"""
anomaly_detector.py - Detector de anomalías en el uso del sistema
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detector de anomalías basado en patrones y reglas"""
    
    MAX_FAILED_ATTEMPTS = 5
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000
    MAX_DATA_EXPORT_SIZE_MB = 100
    
    SUSPICIOUS_ENDPOINTS = [
        '/api/users/all',
        '/api/users/*/password',
        '/api/logs/delete',
        '/api/system/admin',
    ]
    
    ANOMALY_TYPES = {
        'brute_force': 'Múltiples intentos fallidos de acceso',
        'device_jump': 'Cambio sospechoso de dispositivo/ubicación',
        'unusual_endpoint': 'Acceso a endpoint no autorizado',
        'rate_limit': 'Demasiadas solicitudes en corto tiempo',
        'data_exfiltration': 'Intento de extracción masiva de datos',
        'privilege_escalation': 'Intento de escalación de privilegios',
        'abnormal_behavior': 'Patrón de comportamiento anormal',
    }
    
    # ... (resto de métodos igual, pero añadir este método faltante)
    
    @staticmethod
    def get_anomaly_severity(anomaly_type: str) -> int:
        """Obtiene el nivel de severidad de una anomalía (1-5)"""
        severity_levels = {
            'abnormal_behavior': 1,
            'rate_limit': 2,
            'device_jump': 3,
            'unusual_endpoint': 3,
            'brute_force': 4,
            'privilege_escalation': 5,
            'data_exfiltration': 5,
        }
        return severity_levels.get(anomaly_type, 2)
    
    @staticmethod
    def check_device_jump(
        user_id: int,
        current_ip: str,
        current_user_agent: str,
        previous_ip: Optional[str],
        previous_user_agent: Optional[str],
        time_diff_seconds: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Detecta cambios sospechosos de dispositivo/ubicación"""
        reasons = []
        
        if previous_ip and current_ip != previous_ip and time_diff_seconds:
            if time_diff_seconds < 600:
                reasons.append(f"Cambio de IP en {time_diff_seconds}s ({previous_ip} -> {current_ip})")
        
        if previous_user_agent and current_user_agent != previous_user_agent:
            reasons.append("Cambio de navegador/dispositivo")
        
        if reasons:
            reason = f"Cambio sospechoso: {'; '.join(reasons)}"
            logger.warning(f"[DEVICE_JUMP] Usuario {user_id}: {reason}")
            return True, reason
        
        return False, None
    
    @staticmethod
    def check_brute_force(
        user_id: int,
        email: str,
        failed_attempts: int,
        last_attempt_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """Detecta ataques de fuerza bruta"""
        if failed_attempts >= AnomalyDetector.MAX_FAILED_ATTEMPTS:
            reason = f"Demasiados intentos fallidos ({failed_attempts}) para usuario {email}"
            logger.warning(f"[BRUTE_FORCE] {reason}")
            return True, reason
        return False, None