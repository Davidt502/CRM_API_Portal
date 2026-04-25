"""
user_service.py - Servicio de lógica de negocio para usuarios
"""
from datetime import datetime
from typing import Dict, Optional, Tuple
import bcrypt
import re
import logging

# CORREGIDO: Importaciones absolutas
from security.anomaly_detector import AnomalyDetector
from security.access_manager import AccessManager, BlockReason

logger = logging.getLogger(__name__)


class UserService:
    """Servicio de lógica de negocio para usuarios"""
    
    def __init__(self, db_connection_func, access_manager: AccessManager):
        """
        Inicializa el servicio
        
        Args:
            db_connection_func: Función context manager para conexión a BD
            access_manager: Gestor de acceso
        """
        self.db_connection = db_connection_func
        self.access_manager = access_manager
        self.anomaly_detector = AnomalyDetector()
    
    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Autentica a un usuario con validación completa de seguridad
        """
        # Paso 1: Obtener usuario de BD
        user = self._get_user_by_email(email)
        if not user:
            logger.warning(f"Intento de login con email inexistente: {email}")
            return False, None, "Email o contraseña incorrectos"
        
        user_id = user.get('id_usuario')
        
        # Paso 2: Verificar si el usuario está bloqueado
        if self.access_manager and self.access_manager.is_user_blocked(user_id):
            block_info = self.access_manager.get_block_info(user_id)
            logger.warning(f"Usuario bloqueado {email} intentó acceder")
            return False, None, "Cuenta bloqueada. Contacta a administración."
        
        # Paso 3: Verificar contraseña
        if not self._verify_password(password, user.get('password_hash', '')):
            # Registrar intento fallido
            failed_attempts = self._increment_failed_attempts(user_id)
            
            # Detectar brute force
            is_anomaly, reason = self.anomaly_detector.check_brute_force(
                user_id=user_id,
                email=email,
                failed_attempts=failed_attempts
            )
            
            if is_anomaly and self.access_manager:
                self.access_manager.block_user(
                    user_id=user_id,
                    email=email,
                    block_reason=BlockReason.BRUTE_FORCE,
                    anomaly_type='brute_force',
                    details=reason or "Múltiples intentos fallidos"
                )
            
            logger.warning(f"Intento fallido de login para {email}")
            return False, None, "Email o contraseña incorrectos"
        
        # Paso 4: Limpiar intentos fallidos y actualizar acceso
        self._reset_failed_attempts(user_id)
        self._update_last_access(user_id, ip_address, user_agent)
        
        # Paso 5: Retornar datos del usuario
        user_data = {
            'id_usuario': user.get('id_usuario'),
            'nombre_completo': user.get('nombre_completo'),
            'email': user.get('email'),
            'rol': user.get('rol', 'usuario'),
            'estado': user.get('estado', 'Activo')
        }
        
        logger.info(f"Login exitoso para {email} desde {ip_address}")
        return True, user_data, None
    
    def register_user(
        self,
        nombre_completo: str,
        email: str,
        password: str,
        acepto_terminos: bool,
        ip_address: str
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Registra un nuevo usuario
        """
        # Validaciones
        if not self._validate_email(email):
            return False, None, "Email inválido"
        
        if not self._validate_password(password):
            return False, None, "Contraseña debe tener mínimo 8 caracteres, mayúscula, minúscula y número"
        
        if not acepto_terminos:
            return False, None, "Debes aceptar los términos y privacidad"
        
        # Verificar si email ya existe
        existing_user = self._get_user_by_email(email)
        if existing_user:
            return False, None, "El email ya está registrado"
        
        # Hashear contraseña
        password_hash = self._hash_password(password)
        
        # Crear usuario
        try:
            with self.db_connection() as (conn, cursor):
                sql = """
                    INSERT INTO portal_usuarios (
                        nombre_completo, email, password_hash,
                        acepto_terminos, fecha_registro, estado, rol
                    ) VALUES (?, ?, ?, ?, GETDATE(), 'Activo', 'usuario')
                """
                cursor.execute(sql, (nombre_completo, email, password_hash, 1 if acepto_terminos else 0))
                conn.commit()
                
                # Obtener ID del nuevo usuario
                cursor.execute("SELECT @@IDENTITY as id")
                row = cursor.fetchone()
                user_id = row.get('id') if row else None
                
                logger.info(f"Nuevo usuario registrado: {email} (ID: {user_id})")
                return True, int(user_id) if user_id else None, None
        except Exception as e:
            logger.error(f"Error al registrar usuario: {e}")
            return False, None, "Error al registrar usuario"
    
    def _get_user_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene usuario de la BD por email"""
        try:
            with self.db_connection() as (conn, cursor):
                sql = """
                    SELECT id_usuario, nombre_completo, email, password_hash,
                           rol, estado, fecha_registro, ultimo_acceso,
                           ultima_ip, ultimo_user_agent
                    FROM portal_usuarios
                    WHERE email = ?
                """
                cursor.execute(sql, (email,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error al obtener usuario: {e}")
            return None
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica contraseña con bcrypt"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8') if isinstance(password_hash, str) else password_hash
            )
        except Exception as e:
            logger.error(f"Error verificando contraseña: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Hashea contraseña con bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _validate_email(self, email: str) -> bool:
        """Valida formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        """Valida que contraseña cumpla requisitos"""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        return True
    
    def _increment_failed_attempts(self, user_id: int) -> int:
        """Incrementa contador de intentos fallidos"""
        try:
            with self.db_connection() as (conn, cursor):
                cursor.execute("SELECT ISNULL(intentos_fallidos, 0) FROM portal_usuarios WHERE id_usuario = ?", (user_id,))
                row = cursor.fetchone()
                attempts = (row.get('') or list(row.values())[0] if row else 0) + 1
                
                cursor.execute("UPDATE portal_usuarios SET intentos_fallidos = ? WHERE id_usuario = ?", (attempts, user_id))
                conn.commit()
                return attempts
        except Exception as e:
            logger.error(f"Error incrementando intentos: {e}")
            return 0
    
    def _reset_failed_attempts(self, user_id: int) -> None:
        """Resetea intentos fallidos"""
        try:
            with self.db_connection() as (conn, cursor):
                cursor.execute("UPDATE portal_usuarios SET intentos_fallidos = 0 WHERE id_usuario = ?", (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetando intentos: {e}")
    
    def _update_last_access(self, user_id: int, ip_address: str, user_agent: str) -> None:
        """Actualiza último acceso del usuario"""
        try:
            with self.db_connection() as (conn, cursor):
                sql = """
                    UPDATE portal_usuarios
                    SET ultimo_acceso = GETDATE(), ultima_ip = ?, ultimo_user_agent = ?
                    WHERE id_usuario = ?
                """
                cursor.execute(sql, (ip_address[:45], user_agent[:500], user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error actualizando último acceso: {e}")