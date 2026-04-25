"""
security_repository.py - Repositorio para gestión de seguridad (bloqueos, reportes)
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SecurityRepository(BaseRepository):
    """Repositorio para gestión de bloqueos y reportes de seguridad"""
    
    def create_block(
        self,
        user_id: int,
        email: str,
        reason: str,
        anomaly_type: str,
        details: str,
        permanent: bool = False,
        duration_hours: int = 24
    ) -> Optional[int]:
        """
        Crea un registro de bloqueo
        
        Returns:
            ID del bloqueo creado
        """
        try:
            with self._get_cursor() as (conn, cursor):
                query = """
                    INSERT INTO security_blocks (
                        id_usuario, email, razon, tipo_anomalia, detalles,
                        es_permanente, duracion_horas, fecha_bloqueo, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), 'ACTIVO')
                """
                cursor.execute(query, (
                    user_id, email, reason, anomaly_type, details,
                    1 if permanent else 0, duration_hours if not permanent else None
                ))
                conn.commit()
                
                cursor.execute("SELECT @@IDENTITY as id")
                row = cursor.fetchone()
                block_id = dict(row).get('id') if row else None
                
                # Actualizar estado del usuario
                if block_id:
                    self._update_user_status(user_id, 'Bloqueado')
                
                return block_id
        except Exception as e:
            logger.error(f"Error creando bloqueo: {e}")
            raise
    
    def get_active_block(self, user_id: int) -> Optional[Dict]:
        """Obtiene bloqueo activo de un usuario"""
        query = """
            SELECT 
                id_bloqueo, id_usuario, email, razon, tipo_anomalia,
                detalles, es_permanente, duracion_horas, fecha_bloqueo
            FROM security_blocks
            WHERE id_usuario = ? AND estado = 'ACTIVO'
            AND (es_permanente = 1 OR DATEADD(hour, duracion_horas, fecha_bloqueo) > GETDATE())
            ORDER BY fecha_bloqueo DESC
        """
        return self._execute_single(query, (user_id,))
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Verifica si un usuario está bloqueado activamente"""
        block = self.get_active_block(user_id)
        return block is not None
    
    def unblock_user(self, user_id: int, reason: str = None) -> bool:
        """Desbloquea a un usuario"""
        try:
            with self._get_cursor() as (conn, cursor):
                # Actualizar bloqueo
                query = """
                    UPDATE security_blocks
                    SET estado = 'DESBLOQUEADO', fecha_desbloquo = GETDATE()
                    WHERE id_usuario = ? AND estado = 'ACTIVO'
                """
                cursor.execute(query, (user_id,))
                
                # Actualizar estado del usuario
                self._update_user_status(user_id, 'Activo')
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error desbloqueando usuario: {e}")
            return False
    
    def _update_user_status(self, user_id: int, status: str) -> bool:
        """Actualiza el estado del usuario"""
        query = "UPDATE portal_usuarios SET estado = ? WHERE id_usuario = ?"
        rows = self._execute_non_query(query, (status, user_id))
        return rows > 0
    
    def create_security_report(
        self,
        user_id: int,
        email: str,
        block_id: int,
        title: str,
        content: str,
        report_type: str,
        severity: int = 3
    ) -> Optional[int]:
        """
        Crea un reporte de seguridad
        
        Returns:
            ID del reporte creado
        """
        try:
            with self._get_cursor() as (conn, cursor):
                query = """
                    INSERT INTO security_reports (
                        id_usuario, email_usuario, id_bloqueo,
                        titulo, contenido, tipo_reporte,
                        severidad, fecha_creacion, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), 'GENERADO')
                """
                cursor.execute(query, (
                    user_id, email, block_id,
                    title[:200], content, report_type,
                    severity
                ))
                conn.commit()
                
                cursor.execute("SELECT @@IDENTITY as id")
                row = cursor.fetchone()
                return dict(row).get('id') if row else None
        except Exception as e:
            logger.error(f"Error creando reporte de seguridad: {e}")
            return None
    
    def get_user_blocks(self, user_id: int) -> List[Dict]:
        """Obtiene historial de bloqueos de un usuario"""
        query = """
            SELECT 
                id_bloqueo, razon, tipo_anomalia, detalles,
                es_permanente, duracion_horas, fecha_bloqueo,
                fecha_desbloquo, estado
            FROM security_blocks
            WHERE id_usuario = ?
            ORDER BY fecha_bloqueo DESC
        """
        return self._execute_query(query, (user_id,))
    
    def get_recent_blocks(self, limit: int = 50) -> List[Dict]:
        """Obtiene bloqueos recientes"""
        query = """
            SELECT 
                sb.id_bloqueo, sb.id_usuario, sb.email, sb.razon,
                sb.tipo_anomalia, sb.fecha_bloqueo, sb.estado,
                pu.nombre_completo
            FROM security_blocks sb
            LEFT JOIN portal_usuarios pu ON sb.id_usuario = pu.id_usuario
            ORDER BY sb.fecha_bloqueo DESC
            LIMIT ?
        """
        return self._execute_query(query, (limit,))
    
    def get_security_stats(self) -> Dict:
        """Obtiene estadísticas de seguridad"""
        queries = {
            'active_blocks': "SELECT COUNT(*) as count FROM security_blocks WHERE estado = 'ACTIVO'",
            'total_blocks': "SELECT COUNT(*) as count FROM security_blocks",
            'permanent_blocks': "SELECT COUNT(*) as count FROM security_blocks WHERE es_permanente = 1",
            'blocks_by_type': """
                SELECT tipo_anomalia, COUNT(*) as count 
                FROM security_blocks 
                GROUP BY tipo_anomalia
                ORDER BY count DESC
            """,
            'blocks_last_7_days': """
                SELECT CAST(fecha_bloqueo AS DATE) as fecha, COUNT(*) as count
                FROM security_blocks
                WHERE fecha_bloqueo >= DATEADD(day, -7, GETDATE())
                GROUP BY CAST(fecha_bloqueo AS DATE)
                ORDER BY fecha DESC
            """
        }
        
        stats = {}
        for key, query in queries.items():
            if key in ['blocks_by_type', 'blocks_last_7_days']:
                stats[key] = self._execute_query(query)
            else:
                result = self._execute_single(query)
                stats[key] = result.get('count', 0) if result else 0
        
        return stats