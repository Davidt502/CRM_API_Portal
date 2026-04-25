"""
routes/auth_routes.py — Endpoints de autenticación (PostgreSQL/Supabase)
"""
import re
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import Blueprint, request, jsonify

from config import SECRET_KEY, JWT_EXPIRY_HOURS, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SEC
from models.database import db_connection

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ─── Rate limiting en memoria ─────────────────────────────────
_login_attempts: dict = {}
_login_lock = threading.Lock()

_MAX_FIELD_LEN = 256
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _login_lock:
        attempts = _login_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SEC]
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            _login_attempts[ip] = attempts
            return True
        attempts.append(now)
        _login_attempts[ip] = attempts
    return False


def _generate_token(user_data: dict) -> str:
    payload = {
        "id_usuario": user_data["id_usuario"],
        "nombre":     user_data["nombre_completo"],
        "email":      user_data["email"],
        "rol":        user_data["rol"],
        "exp":        datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat":        datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ─── Registro ─────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    if not request.is_json:
        return jsonify({"error": "Content-Type debe ser application/json"}), 400

    data = request.get_json(silent=True) or {}

    nombre   = str(data.get("nombre_completo", "")).strip()[:150]
    email    = str(data.get("email", "")).strip().lower()[:150]
    password = str(data.get("password", ""))
    terminos = bool(data.get("acepto_terminos", False))

    errors = {}
    if not nombre or len(nombre) < 3:
        errors["nombre_completo"] = "El nombre debe tener al menos 3 caracteres."
    if not email or not _EMAIL_REGEX.match(email):
        errors["email"] = "Correo electrónico inválido."
    if not password or len(password) < 8:
        errors["password"] = "La contraseña debe tener al menos 8 caracteres."
    if len(password) > _MAX_FIELD_LEN:
        errors["password"] = "Contraseña demasiado larga."
    if not terminos:
        errors["acepto_terminos"] = "Debes aceptar los términos y condiciones."

    if errors:
        return jsonify({"error": "Datos inválidos", "fields": errors}), 400

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    try:
        with db_connection() as (conn, cursor):
            # Verificar email único
            cursor.execute(
                "SELECT id_usuario FROM portal_usuarios WHERE email = %s",
                (email,)
            )
            if cursor.fetchone():
                return jsonify({"error": "El correo electrónico ya está registrado."}), 409

            cursor.execute(
                """
                INSERT INTO portal_usuarios (nombre_completo, email, password_hash, acepto_terminos)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre, email, pw_hash, terminos)
            )

        logger.info("Nuevo usuario registrado: %s", email)
        return jsonify({"success": True, "message": "Registro exitoso. Ya puedes iniciar sesión."}), 201

    except Exception as exc:
        logger.error("Error en registro: %s", exc, exc_info=True)
        return jsonify({"error": "Error interno al registrar usuario."}), 500


# ─── Login ────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr or "unknown"

    if _is_rate_limited(ip):
        logger.warning("Rate limit excedido para IP: %s", ip)
        return jsonify({"error": "Demasiados intentos. Espera un momento."}), 429

    if not request.is_json:
        return jsonify({"error": "Content-Type debe ser application/json"}), 400

    data     = request.get_json(silent=True) or {}
    email    = str(data.get("email", "")).strip().lower()[:150]
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Correo y contraseña son requeridos."}), 400

    if len(password) > _MAX_FIELD_LEN:
        return jsonify({"error": "Credenciales incorrectas."}), 401

    try:
        with db_connection() as (conn, cursor):
            cursor.execute(
                """
                SELECT id_usuario, nombre_completo, email, password_hash, rol, estado
                FROM portal_usuarios
                WHERE email = %s
                """,
                (email,),
            )
            row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Credenciales incorrectas."}), 401

        if row["estado"] != "Activo":
            return jsonify({"error": "Credenciales incorrectas."}), 401

        pw_hash = row["password_hash"]
        if isinstance(pw_hash, str):
            pw_hash = pw_hash.encode("utf-8")

        try:
            pw_ok = bcrypt.checkpw(password.encode("utf-8"), pw_hash)
        except Exception:
            return jsonify({"error": "Error al verificar credenciales."}), 500

        if not pw_ok:
            return jsonify({"error": "Credenciales incorrectas."}), 401

        # Actualizar último acceso
        with db_connection() as (conn, cursor):
            cursor.execute(
                "UPDATE portal_usuarios SET ultimo_acceso = NOW(), ultima_ip = %s WHERE id_usuario = %s",
                (ip, row["id_usuario"])
            )

        token = _generate_token(dict(row))
        logger.info("Login exitoso: %s desde %s", email, ip)

        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id_usuario":      row["id_usuario"],
                "nombre_completo": row["nombre_completo"],
                "email":           row["email"],
                "rol":             row["rol"],
            },
        })

    except Exception as exc:
        logger.error("Error en login: %s", exc, exc_info=True)
        return jsonify({"error": "Error interno al autenticar."}), 500


# ─── Verify ───────────────────────────────────────────────────
@auth_bp.route("/verify", methods=["GET"])
def verify():
    """Verifica la validez del token JWT."""
    from middleware.auth_middleware import token_required

    @token_required
    def _inner():
        return jsonify({"valid": True, "user": request.current_user})

    return _inner()
