"""
base_validator.py - Validador base con estructura común
"""
import re
from typing import Dict, List, Optional, Any
from datetime import datetime


class ValidationResult:
    """Resultado de validación"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: Dict[str, str] = {}
        self.warnings: Dict[str, str] = {}
    
    def add_error(self, field: str, message: str):
        """Agrega un error de validación"""
        self.is_valid = False
        self.errors[field] = message
    
    def add_warning(self, field: str, message: str):
        """Agrega una advertencia"""
        self.warnings[field] = message
    
    def add_errors(self, errors: Dict[str, str]):
        """Agrega múltiples errores"""
        self.is_valid = False
        self.errors.update(errors)
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        result = {'is_valid': self.is_valid}
        if self.errors:
            result['errors'] = self.errors
        if self.warnings:
            result['warnings'] = self.warnings
        return result
    
    def get_error_messages(self) -> List[str]:
        """Obtiene lista de mensajes de error"""
        return list(self.errors.values())
    
    def __repr__(self):
        return f"<ValidationResult valid={self.is_valid} errors={len(self.errors)}>"


class BaseValidator:
    """Validador base con métodos comunes"""
    
    # Constantes
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    NAME_MIN_LENGTH = 2
    NAME_MAX_LENGTH = 150
    IP_REGEX = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    
    @classmethod
    def validate_required(cls, value: Any, field_name: str) -> Optional[str]:
        """Valida que un campo sea requerido"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"El campo {field_name} es requerido"
        return None
    
    @classmethod
    def validate_email(cls, email: str) -> Optional[str]:
        """Valida formato de email"""
        if not email:
            return "El email es requerido"
        if not cls.EMAIL_REGEX.match(email):
            return "Formato de email inválido"
        if len(email) > 150:
            return "El email no puede exceder 150 caracteres"
        return None
    
    @classmethod
    def validate_password(cls, password: str, require_strong: bool = False) -> Optional[str]:
        """Valida fortaleza de contraseña"""
        if not password:
            return "La contraseña es requerida"
        
        if len(password) < cls.PASSWORD_MIN_LENGTH:
            return f"La contraseña debe tener al menos {cls.PASSWORD_MIN_LENGTH} caracteres"
        
        if len(password) > cls.PASSWORD_MAX_LENGTH:
            return f"La contraseña no puede exceder {cls.PASSWORD_MAX_LENGTH} caracteres"
        
        if require_strong:
            if not any(c.isupper() for c in password):
                return "La contraseña debe contener al menos una mayúscula"
            if not any(c.islower() for c in password):
                return "La contraseña debe contener al menos una minúscula"
            if not any(c.isdigit() for c in password):
                return "La contraseña debe contener al menos un número"
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                return "La contraseña debe contener al menos un carácter especial"
        
        return None
    
    @classmethod
    def validate_name(cls, name: str, field_name: str = "nombre") -> Optional[str]:
        """Valida nombre de persona"""
        if not name or not name.strip():
            return f"El {field_name} es requerido"
        
        name = name.strip()
        if len(name) < cls.NAME_MIN_LENGTH:
            return f"El {field_name} debe tener al menos {cls.NAME_MIN_LENGTH} caracteres"
        
        if len(name) > cls.NAME_MAX_LENGTH:
            return f"El {field_name} no puede exceder {cls.NAME_MAX_LENGTH} caracteres"
        
        if not re.match(r'^[a-zA-ZáéíóúñÑüÜ\s]+$', name):
            return f"El {field_name} solo puede contener letras y espacios"
        
        return None
    
    @classmethod
    def validate_date(cls, date_str: str, field_name: str = "fecha") -> Optional[str]:
        """Valida formato de fecha"""
        if not date_str:
            return None  # Fecha opcional
        
        try:
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return None
        except ValueError:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                return None
            except ValueError:
                return f"Formato de {field_name} inválido. Use ISO format (YYYY-MM-DD)"
    
    @classmethod
    def validate_ip(cls, ip: str) -> Optional[str]:
        """Valida dirección IP"""
        if not ip:
            return None  # IP opcional
        
        if cls.IP_REGEX.match(ip):
            return None
        return "Formato de IP inválido"
    
    @classmethod
    def validate_url(cls, url: str) -> Optional[str]:
        """Valida URL"""
        if not url:
            return None
        
        url_regex = re.compile(
            r'^(https?://)?'  # protocolo opcional
            r'([a-zA-Z0-9]+([\-\.]{1}[a-zA-Z0-9]+)*\.[a-zA-Z]{2,})'  # dominio
            r'(:\d+)?'  # puerto opcional
            r'(/[\w\-\.~]*)*'  # path
            r'(\?[\w\-\.~&=]*)?'  # query string
            r'(#[\w\-]*)?$'  # fragmento
        )
        
        if url_regex.match(url):
            return None
        return "Formato de URL inválido"
    
    @classmethod
    def validate_range(
        cls,
        value: Any,
        min_val: Any = None,
        max_val: Any = None,
        field_name: str = "valor"
    ) -> Optional[str]:
        """Valida que un valor esté en un rango"""
        if value is None:
            return None
        
        if min_val is not None and value < min_val:
            return f"El {field_name} debe ser mayor o igual a {min_val}"
        
        if max_val is not None and value > max_val:
            return f"El {field_name} debe ser menor o igual a {max_val}"
        
        return None
    
    @classmethod
    def validate_length(
        cls,
        value: str,
        min_len: int = None,
        max_len: int = None,
        field_name: str = "texto"
    ) -> Optional[str]:
        """Valida longitud de un string"""
        if value is None:
            return None
        
        if min_len is not None and len(value) < min_len:
            return f"El {field_name} debe tener al menos {min_len} caracteres"
        
        if max_len is not None and len(value) > max_len:
            return f"El {field_name} no puede exceder {max_len} caracteres"
        
        return None
    
    @classmethod
    def sanitize_input(cls, value: str, max_length: int = None) -> str:
        """Sanitiza entrada de usuario"""
        if not value:
            return ""
        
        # Eliminar espacios al inicio y final
        value = value.strip()
        
        # Limitar longitud
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        # Eliminar caracteres peligrosos básicos
        dangerous_chars = ['<', '>', '&', '"', "'", ';', '`', '\\']
        for char in dangerous_chars:
            value = value.replace(char, '')
        
        return value