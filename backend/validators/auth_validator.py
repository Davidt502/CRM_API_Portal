"""
auth_validator.py - Validador de autenticación y tokens
"""
from typing import Dict, Any, Optional
import re

from validators.base_validator import BaseValidator, ValidationResult


class AuthValidator(BaseValidator):
    """Validador para autenticación y tokens"""
    
    # Formatos de token JWT
    JWT_PATTERN = re.compile(
        r'^[A-Za-z0-9\-_]+?\.[A-Za-z0-9\-_]+?\.[A-Za-z0-9\-_]+$'
    )
    
    @classmethod
    def validate_token(cls, token: str) -> ValidationResult:
        """
        Valida formato de token JWT
        
        Args:
            token: Token JWT a validar
            
        Returns:
            ValidationResult con validación
        """
        result = ValidationResult()
        
        if not token:
            result.add_error('token', 'Token requerido')
            return result
        
        if not isinstance(token, str):
            result.add_error('token', 'Token debe ser texto')
            return result
        
        if len(token) > 2048:
            result.add_error('token', 'Token demasiado largo')
            return result
        
        if not cls.JWT_PATTERN.match(token):
            result.add_error('token', 'Formato de token inválido')
        
        return result
    
    @classmethod
    def validate_refresh_token(cls, refresh_token: str) -> ValidationResult:
        """Valida token de refresh"""
        return cls.validate_token(refresh_token)
    
    @classmethod
    def validate_auth_header(cls, auth_header: Optional[str]) -> ValidationResult:
        """
        Valida header de autorización
        Espera formato: "Bearer <token>"
        """
        result = ValidationResult()
        
        if not auth_header:
            result.add_error('authorization', 'Header de autorización requerido')
            return result
        
        parts = auth_header.split(' ')
        
        if len(parts) != 2:
            result.add_error('authorization', 'Formato inválido. Use: Bearer <token>')
            return result
        
        scheme, token = parts
        
        if scheme.lower() != 'bearer':
            result.add_error('authorization', 'Esquema de autenticación debe ser Bearer')
        
        token_result = cls.validate_token(token)
        if not token_result.is_valid:
            for field, error in token_result.errors.items():
                result.add_error(field, error)
        
        return result
    
    @classmethod
    def validate_api_key(cls, api_key: str) -> ValidationResult:
        """Valida API key"""
        result = ValidationResult()
        
        if not api_key:
            result.add_error('api_key', 'API key requerida')
            return result
        
        if len(api_key) < 16:
            result.add_error('api_key', 'API key demasiado corta')
        
        if len(api_key) > 256:
            result.add_error('api_key', 'API key demasiado larga')
        
        # Validar que solo contenga caracteres permitidos
        if not re.match(r'^[A-Za-z0-9\-_]+$', api_key):
            result.add_error('api_key', 'API key contiene caracteres inválidos')
        
        return result