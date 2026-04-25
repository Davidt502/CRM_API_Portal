"""
middleware/auth_middleware.py - Middleware de autenticación JWT
"""
import logging
from functools import wraps
from flask import request, jsonify
import jwt
from config import SECRET_KEY

logger = logging.getLogger(__name__)


def _extract_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return token if token else None
    return None


def token_required(f):
    """Decorator para proteger endpoints con JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()

        if not token:
            return jsonify({"error": "Token de autenticación requerido"}), 401

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado. Inicia sesión nuevamente."}), 401
        except jwt.InvalidTokenError as exc:
            logger.warning("Token inválido: %s", exc)
            return jsonify({"error": "Token inválido"}), 401

        request.current_user = payload
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator para endpoints solo accesibles por administradores."""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        user = getattr(request, "current_user", {})
        if user.get("rol") != "admin":
            return jsonify({"error": "Requiere permisos de administrador"}), 403
        return f(*args, **kwargs)
    return decorated


def get_usuario_from_token() -> str:
    user = getattr(request, "current_user", {})
    return str(user.get("email", "sistema"))[:150]
