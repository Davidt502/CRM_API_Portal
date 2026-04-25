"""
user_repository.py - Repositorio para operaciones de usuario
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repositorio para gestión de usuarios"""
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Obtiene usuario por ID"""
        query = """
            SELECT 
                id_usuario, nombre_completo, email, password_hash,
                rol, estado, acepto_terminos, intentos_fallidos,
                ultima_ip, ultimo_user_agent, ultimo_acceso,
                fecha_registro, fecha_actualizacion
            FROM portal_usuarios
            WHERE id_usuario = ?
        """
        return self._execute_single(query, (user_id,))
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene usuario por email"""
        query = """
            SELECT 
                id_usuario, nombre_completo, email, password_hash,
                rol, estado, acepto_terminos, intentos_fallidos,
                ultima_ip, ultimo_user_agent, ultimo_acceso,
                fecha_registro, fecha_actualizacion
            FROM portal_usuarios
            WHERE email = ?
        """
        return self._execute_single(query, (email,))
    
    def create_user(
        self,
        nombre_completo: str,
        email: str,
        password_hash: str,
        acepto_terminos: bool,
        ip_address: str = None,
        user_agent: str = None
    ) -> Optional[int]:
        """Crea un nuevo usuario"""
        try:
            with self._get_cursor() as (conn, cursor):
                query = """
                    INSERT INTO portal_usuarios (
                        nombre_completo, email, password_hash,
                        acepto_terminos, fecha_registro, estado, rol,
                        ultima_ip, ultimo_user_agent
                    ) VALUES (?, ?, ?, ?, GETDATE(), 'Activo', 'usuario', ?, ?)
                """
                cursor.execute(query, (
                    nombre_completo, email, password_hash,
                    1 if acepto_terminos else 0,
                    ip_address[:45] if ip_address else None,
                    user_agent[:500] if user_agent else None
                ))
                conn.commit()
                
                # Obtener ID del nuevo usuario
                cursor.execute("SELECT @@IDENTITY as id")
                row = cursor.fetchone()
                return dict(row).get('id') if row else None
        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            raise
    
    def update_user(self, user_id: int, updates: Dict) -> bool:
        """Actualiza datos de usuario"""
        if not updates:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        params.append(user_id)
        query = f"""
            UPDATE portal_usuarios 
            SET {', '.join(set_clauses)}, fecha_actualizacion = GETDATE()
            WHERE id_usuario = ?
        """
        
        rows_affected = self._execute_non_query(query, tuple(params))
        return rows_affected > 0
    
    def update_last_access(self, user_id: int, ip_address: str, user_agent: str) -> bool:
        """Actualiza el último acceso del usuario"""
        query = """
            UPDATE portal_usuarios 
            SET ultimo_acceso = GETDATE(), 
                ultima_ip = ?,
                ultimo_user_agent = ?
            WHERE id_usuario = ?
        """
        rows_affected = self._execute_non_query(query, (
            ip_address[:45] if ip_address else None,
            user_agent[:500] if user_agent else None,
            user_id
        ))
        return rows_affected > 0
    
    def increment_failed_attempts(self, user_id: int) -> int:
        """Incrementa el contador de intentos fallidos y retorna el nuevo valor"""
        query = """
            UPDATE portal_usuarios 
            SET intentos_fallidos = ISNULL(intentos_fallidos, 0) + 1
            WHERE id_usuario = ?
        """
        self._execute_non_query(query, (user_id,))
        
        # Obtener el nuevo valor
        select_query = "SELECT intentos_fallidos FROM portal_usuarios WHERE id_usuario = ?"
        result = self._execute_single(select_query, (user_id,))
        return result.get('intentos_fallidos', 0) if result else 0
    
    def reset_failed_attempts(self, user_id: int) -> bool:
        """Resetea el contador de intentos fallidos"""
        query = "UPDATE portal_usuarios SET intentos_fallidos = 0 WHERE id_usuario = ?"
        rows_affected = self._execute_non_query(query, (user_id,))
        return rows_affected > 0
    
    def update_user_status(self, user_id: int, status: str) -> bool:
        """Actualiza el estado del usuario (Activo, Bloqueado, Inactivo)"""
        query = "UPDATE portal_usuarios SET estado = ? WHERE id_usuario = ?"
        rows_affected = self._execute_non_query(query, (status, user_id))
        return rows_affected > 0
    
    def get_all_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None
    ) -> Dict[str, Any]:
        """Obtiene lista paginada de usuarios"""
        offset = (page - 1) * per_page
        
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(nombre_completo LIKE ? OR email LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if status:
            where_clauses.append("estado = ?")
            params.append(status)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Query para contar total
        count_query = f"SELECT COUNT(*) as total FROM portal_usuarios {where_sql}"
        total_result = self._execute_single(count_query, tuple(params))
        total = total_result.get('total', 0) if total_result else 0
        
        # Query para obtener datos paginados
        data_query = f"""
            SELECT id_usuario, nombre_completo, email, rol, estado, 
                   ultimo_acceso, fecha_registro
            FROM portal_usuarios {where_sql}
            ORDER BY id_usuario DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        data_params = tuple(params) + (offset, per_page)
        users = self._execute_query(data_query, data_params)
        
        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page else 1,
            'data': users
        }
    
    def email_exists(self, email: str) -> bool:
        """Verifica si un email ya está registrado"""
        query = "SELECT COUNT(*) as count FROM portal_usuarios WHERE email = ?"
        result = self._execute_single(query, (email,))
        return result.get('count', 0) > 0 if result else False
    
    def get_user_count(self, status: str = None) -> int:
        """Obtiene el número total de usuarios"""
        if status:
            query = "SELECT COUNT(*) as count FROM portal_usuarios WHERE estado = ?"
            result = self._execute_single(query, (status,))
        else:
            query = "SELECT COUNT(*) as count FROM portal_usuarios"
            result = self._execute_single(query)
        
        return result.get('count', 0) if result else 0