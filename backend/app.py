"""
app.py — Portal de APIs Seguro v2 (Supabase + Render)
"""
import sys
import os
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS

from config import SECRET_KEY, DEBUG, CORS_ORIGINS
from middleware.audit_middleware import register_audit_hooks
from routes.auth_routes import auth_bp
from routes.portal_routes import portal_bp
from routes.reports_routes import reports_bp
from routes.api_routes import api_bp

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Directorios de templates y estáticos ─────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR  = os.path.join(BASE_DIR, "..", "frontend")
FRONTEND_DIR  = os.path.normpath(FRONTEND_DIR)

template_folder = FRONTEND_DIR if os.path.exists(FRONTEND_DIR) else os.path.join(BASE_DIR, "templates")
static_folder   = os.path.join(FRONTEND_DIR) if os.path.exists(FRONTEND_DIR) else os.path.join(BASE_DIR, "static")

# ─── Flask App ────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=template_folder,
    static_folder=static_folder,
    static_url_path="/static",
)
app.secret_key = SECRET_KEY

# ─── CORS ────────────────────────────────────────────────────
CORS(app, origins=CORS_ORIGINS, supports_credentials=True)

# ─── Blueprints ───────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(portal_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(api_bp)

# ─── Middleware de auditoría ──────────────────────────────────
register_audit_hooks(app)

# ─── Cabeceras de seguridad HTTP ──────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]          = "DENY"
    response.headers["X-XSS-Protection"]         = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"

    csp_scripts = "'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net" if DEBUG else \
                  "'self' https://unpkg.com https://cdn.jsdelivr.net"

    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src {csp_scripts}; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        f"font-src 'self' https://fonts.gstatic.com; "
        f"img-src 'self' data: https:; "
        f"connect-src 'self';"
    )

    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    return response

# ─── Manejo global de errores ─────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Solicitud inválida"}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "No autorizado"}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Acceso denegado"}), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404

@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({"error": "Demasiadas solicitudes. Espera un momento."}), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error("Error interno: %s", e, exc_info=True)
    return jsonify({"error": "Error interno del servidor"}), 500

# ─── Health Check ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health_check():
    from models.database import test_connection
    db_ok = test_connection()
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200 if db_ok else 503

# ─── Redirección raíz ─────────────────────────────────────────
@app.route("/")
def root():
    from flask import redirect
    return redirect("/portal/login")

# ─── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("=" * 55)
    print("  CRM API Portal v2 — Supabase + Render")
    print(f"  http://localhost:{port}")
    print(f"  Debug: {DEBUG}")
    print("=" * 55)
    app.run(debug=DEBUG, host="0.0.0.0", port=port)
