"""
report_validator.py - Validador para reportes y filtros
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from validators.base_validator import BaseValidator, ValidationResult


class ReportValidator(BaseValidator):
    """Validador para reportes y filtros de actividad"""
    
    # Métodos HTTP permitidos
    ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    
    # Rangos de estado HTTP
    STATUS_RANGES = [
        (100, 199, 'Informacional'),
        (200, 299, 'Éxito'),
        (300, 399, 'Redirección'),
        (400, 499, 'Error cliente'),
        (500, 599, 'Error servidor')
    ]
    
    @classmethod
    def validate_filters(cls, filters: Dict[str, Any]) -> ValidationResult:
        """
        Valida filtros para reportes
        
        Campos soportados:
            fecha_inicio, fecha_fin, email_usuario, endpoint,
            metodo_http, status_code, page, per_page
        """
        result = ValidationResult()
        
        # Validar fechas
        if 'fecha_inicio' in filters and filters['fecha_inicio']:
            date_error = cls.validate_date(filters['fecha_inicio'], "fecha inicio")
            if date_error:
                result.add_error('fecha_inicio', date_error)
        
        if 'fecha_fin' in filters and filters['fecha_fin']:
            date_error = cls.validate_date(filters['fecha_fin'], "fecha fin")
            if date_error:
                result.add_error('fecha_fin', date_error)
        
        # Validar rango de fechas
        if (filters.get('fecha_inicio') and filters.get('fecha_fin') and
            not result.errors.get('fecha_inicio') and not result.errors.get('fecha_fin')):
            try:
                inicio = datetime.fromisoformat(filters['fecha_inicio'])
                fin = datetime.fromisoformat(filters['fecha_fin'])
                if inicio > fin:
                    result.add_error('fecha_fin', 'La fecha fin debe ser posterior a la fecha inicio')
            except ValueError:
                pass
        
        # Validar email
        if 'email_usuario' in filters and filters['email_usuario']:
            email_error = cls.validate_email(filters['email_usuario'])
            if email_error:
                result.add_error('email_usuario', email_error)
        
        # Validar endpoint (sanitizar)
        if 'endpoint' in filters and filters['endpoint']:
            endpoint = filters['endpoint']
            if len(endpoint) > 500:
                result.add_warning('endpoint', 'Endpoint truncado a 500 caracteres')
        
        # Validar método HTTP
        if 'metodo_http' in filters and filters['metodo_http']:
            method = filters['metodo_http'].upper()
            if method not in cls.ALLOWED_METHODS:
                result.add_error('metodo_http', f"Método HTTP inválido. Permitidos: {', '.join(cls.ALLOWED_METHODS)}")
        
        # Validar status code
        if 'status_code' in filters and filters['status_code']:
            try:
                status = int(filters['status_code'])
                error = cls.validate_range(status, 100, 599, "código de estado")
                if error:
                    result.add_error('status_code', error)
            except (ValueError, TypeError):
                result.add_error('status_code', 'Código de estado debe ser un número')
        
        # Validar paginación
        page = filters.get('page', 1)
        per_page = filters.get('per_page', 50)
        
        pagination_result = cls.validate_pagination(
            page, per_page, max_per_page=1000
        )
        if not pagination_result.is_valid:
            for field, error in pagination_result.errors.items():
                result.add_error(field, error)
        
        return result
    
    @classmethod
    def validate_stats_request(cls) -> ValidationResult:
        """Valida solicitud de estadísticas (sin parámetros normalmente)"""
        return ValidationResult()
    
    @classmethod
    def validate_export_params(cls, params: Dict[str, str]) -> ValidationResult:
        """Valida parámetros de exportación"""
        result = ValidationResult()
        
        # Formatos soportados
        allowed_formats = ['csv', 'json', 'xlsx']
        export_format = params.get('format', 'csv')
        
        if export_format not in allowed_formats:
            result.add_error('format', f"Formato inválido. Permitidos: {', '.join(allowed_formats)}")
        
        # Validar fecha range (opcional)
        if 'fecha_inicio' in params and params['fecha_inicio']:
            date_error = cls.validate_date(params['fecha_inicio'], "fecha inicio")
            if date_error:
                result.add_error('fecha_inicio', date_error)
        
        if 'fecha_fin' in params and params['fecha_fin']:
            date_error = cls.validate_date(params['fecha_fin'], "fecha fin")
            if date_error:
                result.add_error('fecha_fin', date_error)
        
        # Límite de registros
        if 'limit' in params:
            try:
                limit = int(params['limit'])
                if limit < 1:
                    result.add_error('limit', 'El límite debe ser mayor a 0')
                elif limit > 100000:
                    result.add_error('limit', 'El límite no puede exceder 100,000 registros')
            except (ValueError, TypeError):
                result.add_error('limit', 'Límite debe ser un número')
        
        return result
    
    @classmethod
    def sanitize_filters(cls, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza los filtros antes de usar en consultas
        
        Args:
            filters: Diccionario con filtros
            
        Returns:
            Diccionario sanitizado
        """
        sanitized = {}
        
        # Sanitizar email
        if 'email_usuario' in filters and filters['email_usuario']:
            sanitized['email_usuario'] = cls.sanitize_input(
                filters['email_usuario'], max_length=150
            )
        
        # Sanitizar endpoint
        if 'endpoint' in filters and filters['endpoint']:
            sanitized['endpoint'] = cls.sanitize_input(
                filters['endpoint'], max_length=500
            )
        
        # Método HTTP (solo mayúsculas)
        if 'metodo_http' in filters and filters['metodo_http']:
            sanitized['metodo_http'] = filters['metodo_http'].upper()[:10]
        
        # Fechas (mantener como están)
        if 'fecha_inicio' in filters and filters['fecha_inicio']:
            sanitized['fecha_inicio'] = filters['fecha_inicio']
        
        if 'fecha_fin' in filters and filters['fecha_fin']:
            sanitized['fecha_fin'] = filters['fecha_fin']
        
        # Paginación
        try:
            sanitized['page'] = max(1, int(filters.get('page', 1)))
        except (ValueError, TypeError):
            sanitized['page'] = 1
        
        try:
            sanitized['per_page'] = min(100, max(1, int(filters.get('per_page', 50))))
        except (ValueError, TypeError):
            sanitized['per_page'] = 50
        
        return sanitized
    
    @classmethod
    def validate_date_range(cls, start_date: str, end_date: str, max_days: int = 365) -> ValidationResult:
        """Valida que el rango de fechas sea válido y no exceda el máximo de días"""
        result = ValidationResult()
        
        start_error = cls.validate_date(start_date, "fecha inicio")
        if start_error:
            result.add_error('fecha_inicio', start_error)
        
        end_error = cls.validate_date(end_date, "fecha fin")
        if end_error:
            result.add_error('fecha_fin', end_error)
        
        if not result.errors:
            try:
                inicio = datetime.fromisoformat(start_date)
                fin = datetime.fromisoformat(end_date)
                
                if inicio > fin:
                    result.add_error('fecha_fin', 'La fecha fin debe ser posterior a la fecha inicio')
                
                days_diff = (fin - inicio).days
                if days_diff > max_days:
                    result.add_error(
                        'fecha_range',
                        f'El rango de fechas no puede exceder {max_days} días'
                    )
            except ValueError:
                pass
        
        return result