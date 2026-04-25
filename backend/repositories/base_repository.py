"""
base_repository.py - Repositorio base con operaciones comunes
"""
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """Repositorio base con métodos comunes para acceso a datos"""
    
    def __init__(self, db_connection_func):
        """
        Inicializa el repositorio
        
        Args:
            db_connection_func: Función context manager para conexión a BD
        """
        self.db_connection = db_connection_func
    
    @contextmanager
    def _get_cursor(self):
        """Context manager para obtener cursor de BD"""
        with self.db_connection() as (conn, cursor):
            yield conn, cursor
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Ejecuta una consulta SELECT y retorna resultados como lista de diccionarios"""
        try:
            with self._get_cursor() as (conn, cursor):
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error ejecutando query: {e}")
            raise
    
    def _execute_single(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Ejecuta una consulta SELECT y retorna un solo resultado"""
        try:
            with self._get_cursor() as (conn, cursor):
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error ejecutando query single: {e}")
            raise
    
    def _execute_non_query(self, query: str, params: tuple = None) -> int:
        """Ejecuta una consulta INSERT/UPDATE/DELETE y retorna filas afectadas"""
        try:
            with self._get_cursor() as (conn, cursor):
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error ejecutando non-query: {e}")
            raise
    
    def _execute_scalar(self, query: str, params: tuple = None) -> Any:
        """Ejecuta una consulta que retorna un solo valor"""
        try:
            with self._get_cursor() as (conn, cursor):
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                if row:
                    values = list(row.values()) if isinstance(row, dict) else list(row)
                    return values[0] if values else None
                return None
        except Exception as e:
            logger.error(f"Error ejecutando query scalar: {e}")
            raise
    
    def _execute_procedure(self, proc_name: str, params: dict = None) -> List[Dict]:
        """Ejecuta un procedimiento almacenado"""
        try:
            with self._get_cursor() as (conn, cursor):
                # Construir placeholders
                if params:
                    placeholders = ','.join(['?' for _ in params])
                    query = f"EXEC {proc_name} {placeholders}"
                    cursor.execute(query, tuple(params.values()))
                else:
                    cursor.execute(f"EXEC {proc_name}")
                
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error ejecutando procedimiento {proc_name}: {e}")
            raise