"""
audit_repository.py - Repositorio para logs de auditoría
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """Repositorio para gestión de logs de auditoría"""
    
    def create_log(
        self,
        id_usuario: Optional[int],
        nombre_usuario: Optional[str],
        email_usuario: Optional[str],
        ip_address: str,
        user_agent: str,
        metodo_http: str,
        endpoint: str,
        query_params: str,
        status_code: int,
        duracion_ms: int
    ) -> Optional[int]:
        """
        Crea un registro de actividad
        
        Returns:
            ID del log creado o None si hay error
        """
        try:
            with self._get_cursor() as (conn, cursor):
                query = """
                    INSERT INTO activity_logs (
                        id_usuario, nombre_usuario, email_usuario,
                        ip_address, user_agent, metodo_http, endpoint,
                        query_params, status_code, duracion_ms, fecha_acceso
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """
                cursor.execute(query, (
                    id_usuario,
                    nombre_usuario[:150] if nombre_usuario else None,
                    email_usuario[:150] if email_usuario else None,
                    ip_address[:45] if ip_address else None,
                    user_agent[:500] if user_agent else None,
                    metodo_http[:10] if metodo_http else None,
                    endpoint[:500] if endpoint else None,
                    query_params[:1000] if query_params else None,
                    status_code,
                    duracion_ms
                ))
                conn.commit()
                
                cursor.execute("SELECT @@IDENTITY as id")
                row = cursor.fetchone()
                return dict(row).get('id') if row else None
        except Exception as e:
            logger.error(f"Error creando log de actividad: {e}")
            return None
    
    def get_activity_logs(
        self,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        email_usuario: Optional[str] = None,
        endpoint: Optional[str] = None,
        metodo: Optional[str] = None,
        status_code: Optional[int] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Obtiene logs de actividad con filtros y paginación
        """
        offset = (page - 1) * per_page
        
        where_clauses = []
        params = []
        
        if fecha_inicio:
            where_clauses.append("fecha_acceso >= ?")
            params.append(fecha_inicio)
        
        if fecha_fin:
            where_clauses.append("fecha_acceso <= DATEADD(day, 1, ?)")
            params.append(fecha_fin)
        
        if email_usuario:
            where_clauses.append("email_usuario = ?")
            params.append(email_usuario)
        
        if endpoint:
            where_clauses.append("endpoint LIKE ?")
            params.append(f'%{endpoint}%')
        
        if metodo:
            where_clauses.append("metodo_http = ?")
            params.append(metodo.upper())
        
        if status_code:
            where_clauses.append("status_code = ?")
            params.append(status_code)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Contar total
        count_query = f"SELECT COUNT(*) as total FROM activity_logs {where_sql}"
        total_result = self._execute_single(count_query, tuple(params))
        total = total_result.get('total', 0) if total_result else 0
        
        # Obtener datos paginados
        data_query = f"""
            SELECT 
                id_log, id_usuario, nombre_usuario, email_usuario,
                ip_address, user_agent, metodo_http, endpoint,
                query_params, status_code, duracion_ms, fecha_acceso
            FROM activity_logs {where_sql}
            ORDER BY fecha_acceso DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        data_params = tuple(params) + (offset, per_page)
        logs = self._execute_query(data_query, data_params)
        
        # Formatear fechas
        for log in logs:
            if isinstance(log.get('fecha_acceso'), datetime):
                log['fecha_acceso'] = log['fecha_acceso'].isoformat()
        
        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page else 1,
            'data': logs
        }
    
    def get_user_activity(
        self,
        email_usuario: str,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Obtiene logs de actividad para un usuario específico
        """
        return self.get_activity_logs(
            email_usuario=email_usuario,
            page=page,
            per_page=per_page
        )
    
    def get_today_requests_count(self) -> int:
        """Obtiene el número de requests de hoy"""
        query = """
            SELECT COUNT(*) as count 
            FROM activity_logs 
            WHERE CAST(fecha_acceso AS DATE) = CAST(GETDATE() AS DATE)
        """
        result = self._execute_single(query)
        return result.get('count', 0) if result else 0
    
    def get_top_endpoints(self, limit: int = 10) -> List[Dict]:
        """Obtiene los endpoints más consultados"""
        query = """
            SELECT 
                endpoint,
                COUNT(*) as total_accesos,
                AVG(duracion_ms) as avg_duracion_ms
            FROM activity_logs
            WHERE endpoint IS NOT NULL
            GROUP BY endpoint
            ORDER BY total_accesos DESC
            LIMIT ?
        """
        return self._execute_query(query, (limit,))
    
    def get_requests_by_hour(self, days: int = 7) -> List[Dict]:
        """Obtiene distribución de requests por hora"""
        query = """
            SELECT 
                DATEPART(hour, fecha_acceso) as hora,
                COUNT(*) as total,
                AVG(duracion_ms) as avg_duracion
            FROM activity_logs
            WHERE fecha_acceso >= DATEADD(day, -?, GETDATE())
            GROUP BY DATEPART(hour, fecha_acceso)
            ORDER BY hora
        """
        return self._execute_query(query, (days,))
    
    def get_requests_by_day(self, days: int = 30) -> List[Dict]:
        """Obtiene requests por día"""
        query = """
            SELECT 
                CAST(fecha_acceso AS DATE) as fecha,
                COUNT(*) as total
            FROM activity_logs
            WHERE fecha_acceso >= DATEADD(day, -?, GETDATE())
            GROUP BY CAST(fecha_acceso AS DATE)
            ORDER BY fecha DESC
        """
        return self._execute_query(query, (days,))
    
    def get_requests_by_user(self, limit: int = 10) -> List[Dict]:
        """Obtiene usuarios más activos"""
        query = """
            SELECT 
                email_usuario,
                nombre_usuario,
                COUNT(*) as total_requests,
                MIN(fecha_acceso) as first_access,
                MAX(fecha_acceso) as last_access
            FROM activity_logs
            WHERE email_usuario IS NOT NULL
            GROUP BY email_usuario, nombre_usuario
            ORDER BY total_requests DESC
            LIMIT ?
        """
        return self._execute_query(query, (limit,))
    
    def get_activity_summary(self) -> Dict:
        """Obtiene resumen de actividad"""
        query = """
            SELECT 
                COUNT(*) as total_requests,
                COUNT(DISTINCT email_usuario) as unique_users,
                COUNT(DISTINCT ip_address) as unique_ips,
                AVG(duracion_ms) as avg_response_time,
                MIN(fecha_acceso) as oldest_log,
                MAX(fecha_acceso) as newest_log
            FROM activity_logs
        """
        result = self._execute_single(query)
        return result or {}