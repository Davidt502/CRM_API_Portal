"""
middleware/audit_middleware.py
Captura automáticamente cada request a /api/* y registra:
  - Usuario (nombre, email) extraído del JWT
  - IP real (soporta proxies con X-Forwarded-For)
  - User-Agent (navegador / dispositivo)
  - Método HTTP + endpoint + query params
  - Status code de la respuesta
  - Duración en milisegundos
"""
import time
import logging
import threading
from datetime import datetime, timezone

from flask import request, g
import jwt

logger = logging.getLogger(__name__)

# Cola en memoria para escribir logs en background (no bloquear el request)
_log_queue: list = []
_log_lock = threading.Lock()


def _get_real_ip() -> str:
    """
    Obtiene la IP real del cliente.
    Considera encabezados de proxy inverso (Nginx, AWS ALB, Cloudflare).
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip().split(",")[0].strip()

    # Proxy estándar
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # El primer IP en la lista es el cliente real
        return forwarded.strip().split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.remote_addr or "unknown"


def _decode_user_from_token() -> dict:
    """
    Intenta decodificar el JWT del header Authorization.
    Retorna dict con id_usuario, nombre, email o valores vacíos.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"id_usuario": None, "nombre": None, "email": None}

    token = auth_header[7:].strip()
    if not token:
        return {"id_usuario": None, "nombre": None, "email": None}

    try:
        from config import SECRET_KEY
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "id_usuario": payload.get("id_usuario"),
            "nombre":     payload.get("nombre"),
            "email":      payload.get("email"),
        }
    except Exception:
        return {"id_usuario": None, "nombre": None, "email": None}


def _should_log(path: str) -> bool:
    """
    Define qué rutas se auditan.
    Solo registra endpoints /api/* y excluye health check y swagger assets.
    """
    EXCLUDED = {"/api/health", "/favicon.ico"}
    EXCLUDED_PREFIXES = ("/static/", "/docs/swagger-ui")

    if path in EXCLUDED:
        return False
    for prefix in EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False
    return path.startswith("/api/")


def _write_log_async(log_data: dict):
    """
    Escribe el log en SQL Server en un hilo separado.
    No bloquea el response del request.
    """
    def _write():
        try:
            from models.database import db_connection
            with db_connection() as (conn, cursor):
                cursor.execute(
                    """
                    EXEC sp_insertar_activity_log
                        @id_usuario     = %s,
                        @nombre_usuario = %s,
                        @email_usuario  = %s,
                        @ip_address     = %s,
                        @user_agent     = %s,
                        @metodo_http    = %s,
                        @endpoint       = %s,
                        @query_params   = %s,
                        @status_code    = %s,
                        @duracion_ms    = %s
                    """,
                    (
                        log_data.get("id_usuario"),
                        log_data.get("nombre"),
                        log_data.get("email"),
                        log_data.get("ip")[:45],
                        (log_data.get("user_agent") or "")[:500],
                        log_data.get("method"),
                        log_data.get("endpoint")[:500],
                        (log_data.get("query") or "")[:1000],
                        log_data.get("status_code"),
                        log_data.get("duration_ms"),
                    ),
                )
        except Exception as exc:
            logger.warning("Error al guardar log de auditoría: %s", exc)

    thread = threading.Thread(target=_write, daemon=True)
    thread.start()


def register_audit_hooks(app):
    """
    Registra los hooks before_request y after_request en la app Flask.
    Llamar una sola vez en app.py:
        register_audit_hooks(app)
    """

    @app.before_request
    def before_request_hook():
        """Marca el tiempo de inicio y captura datos del request."""
        g.start_time = time.monotonic()
        g.user_info  = _decode_user_from_token()
        g.real_ip    = _get_real_ip()

    @app.after_request
    def after_request_hook(response):
        """Captura el status code y calcula duración; lanza escritura async."""
        try:
            path = request.path

            if not _should_log(path):
                return response

            duration_ms = int((time.monotonic() - getattr(g, "start_time", time.monotonic())) * 1000)
            user_info   = getattr(g, "user_info", {})
            real_ip     = getattr(g, "real_ip", _get_real_ip())

            log_data = {
                "id_usuario":  user_info.get("id_usuario"),
                "nombre":      user_info.get("nombre"),
                "email":       user_info.get("email"),
                "ip":          real_ip,
                "user_agent":  request.headers.get("User-Agent", ""),
                "method":      request.method,
                "endpoint":    path,
                "query":       request.query_string.decode("utf-8", errors="replace"),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

            logger.info(
                "[AUDIT] %s %s → %d | ip=%s | user=%s | %dms",
                log_data["method"],
                log_data["endpoint"],
                log_data["status_code"],
                log_data["ip"],
                log_data["email"] or "anónimo",
                duration_ms,
            )

            _write_log_async(log_data)

        except Exception as exc:
            logger.warning("Error en audit after_request: %s", exc)

        return response
