"""
access_manager.py - Sistema de bloqueo y reporte de mal uso
Gestiona:
  - Bloqueo automático de usuarios después de detecciones
  - Generación de reportes de seguridad
  - Notificaciones al usuario bloqueado
  - Restricción permanente de compartir datos
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class BlockReason(Enum):
    """Razones de bloqueo de usuario"""
    BRUTE_FORCE = "Múltiples intentos de acceso fallidos"
    PRIVILEGE_ESCALATION = "Intento de acceso no autorizado"
    DATA_EXFILTRATION = "Intento de extracción masiva de datos"
    ANOMALOUS_BEHAVIOR = "Comportamiento anómalo detectado"
    RATE_LIMIT_EXCEEDED = "Exceso de solicitudes"
    SUSPICIOUS_DEVICE_JUMP = "Cambio sospechoso de dispositivo"
    SECURITY_POLICY_VIOLATION = "Violación de política de seguridad"
    MANUAL_BLOCK = "Bloqueado manualmente por administrador"


class AccessManager:
    """Gestor de acceso y bloqueos de usuario"""
    
    # Configuración de bloqueos
    DEFAULT_BLOCK_DURATION_HOURS = 24  # Bloqueo automático por 24h
    PERMANENT_BLOCK_THRESHOLD = 3  # 3+ violaciones = bloqueo permanente
    
    def __init__(self, db_connection):
        """
        Inicializa el gestor de acceso
        
        Args:
            db_connection: Conexión a la base de datos
        """
        self.db = db_connection
    
    def block_user(
        self,
        user_id: int,
        email: str,
        block_reason: BlockReason,
        anomaly_type: str,
        details: str,
        permanent: bool = False,
        block_duration_hours: Optional[int] = None
    ) -> Dict:
        """
        Bloquea a un usuario por comportamiento sospechoso
        
        Args:
            user_id: ID del usuario a bloquear
            email: Email del usuario
            block_reason: Razón del bloqueo (BlockReason enum)
            anomaly_type: Tipo de anomalía detectada
            details: Detalles adicionales de la anomalía
            permanent: Si es bloqueo permanente
            block_duration_hours: Duración del bloqueo en horas
            
        Returns:
            Dict con información del bloqueo
        """
        
        if permanent:
            block_duration_hours = None  # Sin límite de tiempo
        else:
            block_duration_hours = block_duration_hours or self.DEFAULT_BLOCK_DURATION_HOURS
        
        block_id = self._create_block_record(
            user_id=user_id,
            email=email,
            reason=block_reason.value,
            anomaly_type=anomaly_type,
            details=details,
            permanent=permanent,
            duration_hours=block_duration_hours
        )
        
        # Registrar el evento
        logger.critical(
            f"[BLOCK-{anomaly_type.upper()}] Usuario {email} (ID:{user_id}) bloqueado. "
            f"Razón: {block_reason.value}. Detalles: {details}"
        )
        
        # Crear reporte de seguridad
        report_id = self._generate_security_report(
            user_id=user_id,
            email=email,
            block_id=block_id,
            reason=block_reason.value,
            details=details
        )
        
        return {
            'block_id': block_id,
            'user_id': user_id,
            'email': email,
            'reason': block_reason.value,
            'permanent': permanent,
            'duration_hours': block_duration_hours,
            'blocked_at': datetime.utcnow().isoformat(),
            'report_id': report_id,
            'message': self._get_block_message(block_reason, permanent, block_duration_hours)
        }
    
    def _create_block_record(
        self,
        user_id: int,
        email: str,
        reason: str,
        anomaly_type: str,
        details: str,
        permanent: bool,
        duration_hours: Optional[int]
    ) -> int:
        """
        Crea un registro de bloqueo en la base de datos
        
        Returns:
            ID del bloqueo creado
        """
        try:
            with self.db.cursor() as cursor:
                sql = """
                    INSERT INTO security_blocks (
                        id_usuario, email, razon, tipo_anomalia, detalles,
                        es_permanente, duracion_horas, fecha_bloqueo, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), 'ACTIVO')
                """
                cursor.execute(sql, (
                    user_id, email, reason, anomaly_type, details,
                    1 if permanent else 0, duration_hours
                ))
                cursor.commit()
                
                # Obtener el ID del bloqueo creado
                cursor.execute("SELECT SCOPE_IDENTITY()")
                block_id = cursor.fetchone()[0]
                
                # Actualizar estado del usuario
                update_sql = """
                    UPDATE portal_usuarios
                    SET estado = 'Bloqueado'
                    WHERE id_usuario = ?
                """
                cursor.execute(update_sql, (user_id,))
                cursor.commit()
                
                return int(block_id)
        except Exception as e:
            logger.error(f"Error al crear registro de bloqueo: {e}")
            raise
    
    def _generate_security_report(
        self,
        user_id: int,
        email: str,
        block_id: int,
        reason: str,
        details: str
    ) -> int:
        """
        Genera un reporte de seguridad
        
        Returns:
            ID del reporte generado
        """
        try:
            with self.db.cursor() as cursor:
                report_content = f"""
REPORTE DE SEGURIDAD - BLOQUEO DE USUARIO
==========================================

Fecha del Reporte: {datetime.utcnow().isoformat()}
ID de Usuario: {user_id}
Email del Usuario: {email}
ID de Bloqueo: {block_id}

RAZÓN DEL BLOQUEO:
{reason}

DETALLES ADICIONALES:
{details}

ACCIÓN TOMADA:
El usuario ha sido bloqueado automáticamente por el sistema de detección
de anomalías. No podrá acceder a su cuenta ni recibir datos del sistema
mientras el bloqueo esté activo.

POLÍTICA ACCESS/DATA SHARING:
Mientras el usuario esté bloqueado, NO se compartirán de datos de su sistema.
Esto incluye:
- API de acceso bloqueada
- Exportación de datos deshabilitada
- Sincronización parada
- Webshooks pausados

El bloqueo se revisará automáticamente después de 24 horas.
Para desbloqueo permanente, contactar a administración@sistema.com
                """
                
                sql = """
                    INSERT INTO security_reports (
                        id_usuario, email_usuario, id_bloqueo,
                        titulo, contenido, tipo_reporte,
                        severidad, fecha_creacion, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), 'GENERADO')
                """
                
                cursor.execute(sql, (
                    user_id, email, block_id,
                    f"Bloqueo de usuario: {email}",
                    report_content,
                    "SECURITY_BLOCK",
                    5  # Severidad máxima
                ))
                cursor.commit()
                
                cursor.execute("SELECT SCOPE_IDENTITY()")
                report_id = cursor.fetchone()[0]
                
                return int(report_id)
        except Exception as e:
            logger.error(f"Error al generar reporte de seguridad: {e}")
            raise
    
    def is_user_blocked(self, user_id: int) -> bool:
        """
        Verifica si un usuario está bloqueado
        
        Args:
            user_id: ID del usuario a verificar
            
        Returns:
            True si está bloqueado
        """
        try:
            with self.db.cursor() as cursor:
                sql = """
                    SELECT COUNT(*) FROM security_blocks
                    WHERE id_usuario = ?
                    AND estado = 'ACTIVO'
                    AND (es_permanente = 1 OR fecha_bloqueo + CAST(duracion_horas AS INT) HOUR > GETDATE())
                """
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                
                return result[0] > 0
        except Exception as e:
            logger.error(f"Error al verificar bloqueo del usuario: {e}")
            return False  # Por seguridad, permitir acceso si hay error
    
    def get_block_info(self, user_id: int) -> Optional[Dict]:
        """
        Obtiene información del bloqueo de un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con información del bloqueo o None
        """
        try:
            with self.db.cursor() as cursor:
                sql = """
                    SELECT TOP 1
                        id_bloqueo, razon, tipo_anomalia, detalles,
                        es_permanente, duracion_horas, fecha_bloqueo
                    FROM security_blocks
                    WHERE id_usuario = ?
                    AND estado = 'ACTIVO'
                    ORDER BY fecha_bloqueo DESC
                """
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'block_id': result[0],
                        'reason': result[1],
                        'anomaly_type': result[2],
                        'details': result[3],
                        'permanent': bool(result[4]),
                        'duration_hours': result[5],
                        'blocked_at': result[6].isoformat() if result[6] else None
                    }
                
                return None
        except Exception as e:
            logger.error(f"Error al obtener info de bloqueo: {e}")
            return None
    
    def _get_block_message(
        self,
        reason: BlockReason,
        permanent: bool,
        duration_hours: Optional[int]
    ) -> str:
        """
        Genera un mensaje descriptivo sobre el bloqueo
        """
        
        base_msg = f"Cuenta bloqueada: {reason.value}."
        
        if permanent:
            return (
                f"{base_msg} "
                "⚠️ Bloqueo PERMANENTE. "
                "No se compartirán datos de su sistema. "
                "Para apelar, contacte a: admin@sistema.com"
            )
        else:
            return (
                f"{base_msg} "
                f"🔒 Bloqueado durante {duration_hours} horas. "
                "No se accedera a datos ni se compartirán con otros sistemas. "
                "Acceso se restaurará automáticamente después del período de bloqueo."
            )
    
    def unblock_user(self, user_id: int, reason: str) -> bool:
        """
        Desbloquea a un usuario (solo para admins)
        
        Args:
            user_id: ID del usuario
            reason: Razón del desbloqueo
            
        Returns:
            True si fue desbloqueado exitosamente
        """
        try:
            with self.db.cursor() as cursor:
                # Actualizar estado del bloqueo
                sql = """
                    UPDATE security_blocks
                    SET estado = 'DESBLOQUEADO', fecha_desbloqu = GETDATE()
                    WHERE id_usuario = ? AND estado = 'ACTIVO'
                """
                cursor.execute(sql, (user_id,))
                
                # Actualizar estado del usuario
                update_sql = """
                    UPDATE portal_usuarios
                    SET estado = 'Activo'
                    WHERE id_usuario = ?
                """
                cursor.execute(update_sql, (user_id,))
                cursor.commit()
                
                logger.info(f"Usuario {user_id} desbloqueado. Razón: {reason}")
                return True
        except Exception as e:
            logger.error(f"Error al desbloquear usuario: {e}")
            return False
    
    def check_and_escalate_violations(self, user_id: int) -> Optional[BlockReason]:
        """
        Verifica si el usuario tiene múltiples violaciones
        y escala a bloqueo permanente si es necesario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            BlockReason si debe bloquearse permanentemente, None si no
        """
        try:
            with self.db.cursor() as cursor:
                sql = """
                    SELECT COUNT(*) FROM security_blocks
                    WHERE id_usuario = ? AND estado = 'ACTIVO'
                """
                cursor.execute(sql, (user_id,))
                violation_count = cursor.fetchone()[0]
                
                if violation_count >= self.PERMANENT_BLOCK_THRESHOLD:
                    logger.critical(
                        f"Usuario {user_id} escalado a bloqueo permanente "
                        f"({violation_count} violaciones)"
                    )
                    return BlockReason.SECURITY_POLICY_VIOLATION
                
                return None
        except Exception as e:
            logger.error(f"Error al verificar escalación de violaciones: {e}")
            return None
