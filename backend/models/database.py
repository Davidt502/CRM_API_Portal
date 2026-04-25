"""
models/database.py — Conexión a Supabase (PostgreSQL) con psycopg2
"""
import logging
from contextlib import contextmanager
from decimal import Decimal

import psycopg2
import psycopg2.extras  # para RealDictCursor (devuelve dicts)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_CONFIG, DATABASE_URL

logger = logging.getLogger(__name__)


def get_connection():
    """Obtiene una conexión a Supabase/PostgreSQL."""
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        else:
            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                dbname=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=10,
                sslmode="require",   # Supabase requiere SSL
            )
        return conn
    except psycopg2.Error as e:
        logger.error("Error de conexión a Supabase: %s", e)
        raise


@contextmanager
def db_connection():
    """Context manager para conexiones con commit/rollback automático."""
    conn = None
    try:
        conn = get_connection()
        # RealDictCursor devuelve filas como dicts, igual que el código original
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield conn, cursor
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en operación de BD: %s", e)
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def to_int(value):
    """Convierte Decimal a int de forma segura."""
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, int):
        return value
    return None


def test_connection() -> bool:
    """Prueba la conexión a la base de datos. Retorna True si OK."""
    try:
        with db_connection() as (conn, cursor):
            cursor.execute("SELECT 1 AS test")
            row = cursor.fetchone()
            return row is not None and row.get("test") == 1
    except Exception as e:
        logger.error("Error en test de conexión: %s", e)
        return False
