"""
user_validator.py - Validador de datos de usuario
"""
from typing import Dict, Any
import re

from validators.base_validator import BaseValidator, ValidationResult


class UserValidator(BaseValidator):
    """Validador para datos de usuario"""
    
    # Roles permitidos
    ALLOWED_ROLES = ['usuario', 'admin', 'auditor']
    
    # Estados permitidos
    ALLOWED_STATUSES = ['Activo', 'Inactivo', 'Bloqueado']
    
    @classmethod
    def validate_register(cls, data: Dict[str, Any]) -> ValidationResult:
        """
        Valida datos de registro de usuario
        
        Campos esperados:
            nombre_completo, email, password, acepto_terminos
        """
        result = ValidationResult()
        
        # Validar nombre
        nombre = data.get('nombre_completo', '')
        nombre_error = cls.validate_name(nombre, "nombre completo")
        if nombre_error:
            result.add_error('nombre_completo', nombre_error)
        
        # Validar email
        email = data.get('email', '')
        email_error = cls.validate_email(email)
        if email_error:
            result.add_error('email', email_error)
        
        # Validar password
        password = data.get('password', '')
        password_error = cls.validate_password(password, require_strong=True)
        if password_error:
            result.add_error('password', password_error)
        
        # Validar términos
        acepto_terminos = data.get('acepto_terminos', False)
        if not acepto_terminos:
            result.add_error('acepto_terminos', 'Debes aceptar los términos y condiciones')
        
        return result
    
    @classmethod
    def validate_login(cls, data: Dict[str, str]) -> ValidationResult:
        """
        Valida datos de login
        
        Campos esperados: email, password
        """
        result = ValidationResult()
        
        email = data.get('email', '')
        email_error = cls.validate_email(email)
        if email_error:
            result.add_error('email', email_error)
        
        password = data.get('password', '')
        if not password:
            result.add_error('password', 'La contraseña es requerida')
        elif len(password) > cls.PASSWORD_MAX_LENGTH:
            result.add_error('password', f'Contraseña demasiado larga (máx {cls.PASSWORD_MAX_LENGTH})')
        
        return result
    
    @classmethod
    def validate_update(cls, data: Dict[str, Any], allow_partial: bool = True) -> ValidationResult:
        """
        Valida datos de actualización de usuario
        
        Args:
            data: Datos a validar
            allow_partial: Si es True, solo valida campos presentes
        """
        result = ValidationResult()
        
        # Validar nombre si está presente
        if 'nombre_completo' in data:
            nombre_error = cls.validate_name(data['nombre_completo'], "nombre completo")
            if nombre_error:
                result.add_error('nombre_completo', nombre_error)
        
        # Validar email si está presente
        if 'email' in data:
            email_error = cls.validate_email(data['email'])
            if email_error:
                result.add_error('email', email_error)
        
        # Validar rol si está presente
        if 'rol' in data:
            if data['rol'] not in cls.ALLOWED_ROLES:
                result.add_error('rol', f"Rol inválido. Permitidos: {', '.join(cls.ALLOWED_ROLES)}")
        
        # Validar estado si está presente
        if 'estado' in data:
            if data['estado'] not in cls.ALLOWED_STATUSES:
                result.add_error('estado', f"Estado inválido. Permitidos: {', '.join(cls.ALLOWED_STATUSES)}")
        
        # Si no hay campos para validar y no se permite parcial, error
        if not allow_partial and not result.errors and not any(k in data for k in ['nombre_completo', 'email', 'rol', 'estado']):
            result.add_error('_general', 'No se proporcionaron campos para actualizar')
        
        return result
    
    @classmethod
    def validate_password_change(
        cls,
        current_password: str,
        new_password: str,
        confirm_password: str
    ) -> ValidationResult:
        """Valida cambio de contraseña"""
        result = ValidationResult()
        
        if not current_password:
            result.add_error('current_password', 'La contraseña actual es requerida')
        
        new_password_error = cls.validate_password(new_password, require_strong=True)
        if new_password_error:
            result.add_error('new_password', new_password_error)
        
        if new_password != confirm_password:
            result.add_error('confirm_password', 'Las contraseñas no coinciden')
        
        if new_password and current_password and new_password == current_password:
            result.add_error('new_password', 'La nueva contraseña debe ser diferente a la actual')
        
        return result
    
    @classmethod
    def validate_user_id(cls, user_id: Any) -> ValidationResult:
        """Valida ID de usuario"""
        result = ValidationResult()
        
        try:
            user_id_int = int(user_id)
            if user_id_int <= 0:
                result.add_error('user_id', 'ID de usuario inválido')
        except (ValueError, TypeError):
            result.add_error('user_id', 'ID de usuario debe ser un número entero')
        
        return result
    
    @classmethod
    def validate_pagination(cls, page: int, per_page: int, max_per_page: int = 100) -> ValidationResult:
        """Valida parámetros de paginación"""
        result = ValidationResult()
        
        if page is not None:
            try:
                page_int = int(page)
                if page_int < 1:
                    result.add_error('page', 'La página debe ser mayor o igual a 1')
            except (ValueError, TypeError):
                result.add_error('page', 'Página inválida')
        
        if per_page is not None:
            try:
                per_page_int = int(per_page)
                if per_page_int < 1:
                    result.add_error('per_page', 'Items por página debe ser mayor a 0')
                elif per_page_int > max_per_page:
                    result.add_error('per_page', f'Items por página no puede exceder {max_per_page}')
            except (ValueError, TypeError):
                result.add_error('per_page', 'Items por página inválido')
        
        return result