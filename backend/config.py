"""
config.py — Configuración segura del Portal API
Lee TODAS las variables sensibles desde variables de entorno.
Nunca hardcodea credenciales.
"""
import os
import secrets
import sys

# Cargar .env solo en desarrollo local
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except ImportError:
    pass  # En producción (Render) no se necesita python-dotenv

# ─── Base de datos (Supabase / PostgreSQL) ────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Si no hay DATABASE_URL, construir desde variables individuales
if not DATABASE_URL:
    _host = os.getenv("SUPABASE_DB_HOST", "")
    _port = os.getenv("SUPABASE_DB_PORT", "5432")
    _name = os.getenv("SUPABASE_DB_NAME", "postgres")
    _user = os.getenv("SUPABASE_DB_USER", "postgres")
    _pass = os.getenv("SUPABASE_DB_PASSWORD", "")

    if not _host or not _pass:
        print("⚠️  ERROR: Faltan variables de entorno de base de datos.")
        print("   Configura SUPABASE_DB_HOST y SUPABASE_DB_PASSWORD en tu .env")
        # No salir en importación, solo avisar
    else:
        DATABASE_URL = f"postgresql://{_user}:{_pass}@{_host}:{_port}/{_name}"

DB_CONFIG = {
    "host":     os.getenv("SUPABASE_DB_HOST", "localhost"),
    "port":     int(os.getenv("SUPABASE_DB_PORT", "5432")),
    "database": os.getenv("SUPABASE_DB_NAME", "postgres"),
    "user":     os.getenv("SUPABASE_DB_USER", "postgres"),
    "password": os.getenv("SUPABASE_DB_PASSWORD", ""),
}

# ─── Seguridad JWT ────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    if os.getenv("FLASK_ENV") == "production":
        print("❌ CRÍTICO: SECRET_KEY no configurada en producción. Abortando.")
        sys.exit(1)
    SECRET_KEY = secrets.token_hex(32)
    print(f"⚠️  Usando SECRET_KEY generada automáticamente (solo desarrollo)")

# ─── Flask ───────────────────────────────────────────────────
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_ENV = os.getenv("FLASK_ENV", "production")

# ─── CORS ────────────────────────────────────────────────────
_origins_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5000,http://127.0.0.1:5000"
)
CORS_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]

# ─── JWT ─────────────────────────────────────────────────────
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))

# ─── Paginación ──────────────────────────────────────────────
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

# ─── Rate Limiting ───────────────────────────────────────────
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SEC   = int(os.getenv("LOGIN_WINDOW_SEC", "60"))

# ─── Validaciones ────────────────────────────────────────────
PASSWORD_MIN_LENGTH = 8
MAX_FIELD_LEN = 256
BLOCK_DURATION_MINUTES = 15
