/**
 * CRM API Portal - Script Base Global
 * Versión: 2.0.0
 * Funcionalidades:
 * - Gestión de sesión y autenticación
 * - Interceptor global de fetch para manejo de 401
 * - Helpers para peticiones API
 * - Utilidades generales
 * - Sistema de notificaciones toast
 * - Manejo de errores centralizado
 */

(function() {
    'use strict';

    // ============================================================
    // CONFIGURACIÓN GLOBAL
    // ============================================================
    const CONFIG = {
        TOKEN_KEY: 'api_token',
        USER_KEY: 'api_user',
        LOGIN_URL: '/portal/login',
        DASHBOARD_URL: '/portal/dashboard',
        SESSION_TIMEOUT_MS: 8 * 60 * 60 * 1000, // 8 horas
        TOAST_DURATION: 3000
    };

    // ============================================================
    // UTILIDADES GENERALES
    // ============================================================
    
    /**
     * Escapa caracteres HTML para prevenir XSS
     */
    window.escapeHtml = function(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    /**
     * Muestra un toast de notificación
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duración en ms (opcional)
     */
    window.showToast = function(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
        // Eliminar toast existente si hay
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) existingToast.remove();

        // Crear elemento toast
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        
        // Iconos según tipo
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || 'ℹ'}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
            <button class="toast-close">&times;</button>
        `;
        
        // Estilos inline para asegurar funcionalidad
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${type === 'success' ? '#00e5a0' : type === 'error' ? '#ff4d6d' : type === 'warning' ? '#f97316' : '#6c63ff'};
            color: ${type === 'success' ? '#000' : '#fff'};
            padding: 12px 16px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: 'Space Mono', monospace;
            font-size: 13px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideInRight 0.3s ease;
            max-width: 350px;
            cursor: default;
        `;
        
        const toastIcon = toast.querySelector('.toast-icon');
        if (toastIcon) {
            toastIcon.style.cssText = `
                font-size: 18px;
                font-weight: bold;
            `;
        }
        
        const toastMessage = toast.querySelector('.toast-message');
        if (toastMessage) {
            toastMessage.style.cssText = `
                flex: 1;
                line-height: 1.4;
            `;
        }
        
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.style.cssText = `
                background: none;
                border: none;
                color: inherit;
                font-size: 18px;
                cursor: pointer;
                padding: 0 4px;
                opacity: 0.7;
            `;
            closeBtn.onclick = () => toast.remove();
        }
        
        document.body.appendChild(toast);
        
        // Auto-remover después de duración
        setTimeout(() => {
            if (toast && toast.parentNode) {
                toast.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, duration);
    };

    /**
     * Formatea una fecha para mostrar
     */
    window.formatDate = function(date, format = 'datetime') {
        if (!date) return '—';
        const d = new Date(date);
        if (isNaN(d.getTime())) return '—';
        
        if (format === 'date') {
            return d.toLocaleDateString('es-GT');
        } else if (format === 'time') {
            return d.toLocaleTimeString('es-GT', { hour12: false });
        } else {
            return d.toLocaleString('es-GT', { hour12: false });
        }
    };

    /**
     * Trunca un texto a una longitud máxima
     */
    window.truncateText = function(str, maxLength = 50) {
        if (!str) return '—';
        if (str.length <= maxLength) return str;
        return str.slice(0, maxLength) + '…';
    };

    /**
     * Copia texto al portapapeles
     */
    window.copyToClipboard = async function(text, successMsg = '¡Copiado al portapapeles!') {
        try {
            await navigator.clipboard.writeText(text);
            showToast(successMsg, 'success');
            return true;
        } catch (err) {
            console.error('Error al copiar:', err);
            showToast('No se pudo copiar', 'error');
            return false;
        }
    };

    /**
     * Debounce para evitar múltiples llamadas
     */
    window.debounce = function(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };

    // ============================================================
    // GESTIÓN DE SESIÓN
    // ============================================================
    
    /**
     * Obtiene el token de autenticación
     */
    window.getToken = function() {
        return localStorage.getItem(CONFIG.TOKEN_KEY);
    };

    /**
     * Obtiene el usuario actual
     */
    window.getCurrentUser = function() {
        const userStr = localStorage.getItem(CONFIG.USER_KEY);
        if (!userStr) return null;
        try {
            return JSON.parse(userStr);
        } catch (e) {
            console.error('Error al parsear usuario:', e);
            return null;
        }
    };

    /**
     * Verifica si el usuario está autenticado
     * @param {boolean} redirectOnFail - Si debe redirigir al login cuando falla
     * @returns {boolean}
     */
    window.checkAuth = function(redirectOnFail = true) {
        const token = getToken();
        const user = getCurrentUser();
        
        if (!token || !user) {
            if (redirectOnFail) {
                window.location.href = CONFIG.LOGIN_URL;
            }
            return false;
        }
        
        // Verificar si el token expiró (opcional, basado en timestamp)
        const tokenTimestamp = localStorage.getItem('token_timestamp');
        if (tokenTimestamp) {
            const elapsed = Date.now() - parseInt(tokenTimestamp);
            if (elapsed > CONFIG.SESSION_TIMEOUT_MS) {
                logout('Tu sesión ha expirado');
                if (redirectOnFail) {
                    window.location.href = CONFIG.LOGIN_URL;
                }
                return false;
            }
        }
        
        return true;
    };

    /**
     * Verifica si el usuario es administrador
     */
    window.isAdmin = function() {
        const user = getCurrentUser();
        return user?.rol === 'admin';
    };

    /**
     * Cierra la sesión del usuario
     * @param {string} message - Mensaje opcional para mostrar
     */
    window.logout = function(message = 'Sesión cerrada') {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_KEY);
        localStorage.removeItem('token_timestamp');
        
        if (message) {
            showToast(message, 'info');
        }
        
        window.location.href = CONFIG.LOGIN_URL;
    };

    /**
     * Guarda la sesión después de login exitoso
     * @param {string} token - Token JWT
     * @param {object} user - Datos del usuario
     */
    window.setSession = function(token, user) {
        localStorage.setItem(CONFIG.TOKEN_KEY, token);
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
        localStorage.setItem('token_timestamp', Date.now().toString());
    };

    // ============================================================
    // API HELPERS
    // ============================================================
    
    /**
     * Obtiene los headers para peticiones autenticadas
     * @param {object} extraHeaders - Headers adicionales
     * @returns {object}
     */
    window.getAuthHeaders = function(extraHeaders = {}) {
        const token = getToken();
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...extraHeaders
        };
    };

    /**
     * Maneja errores de respuesta API
     * @param {Response} response - Respuesta fetch
     * @param {string} fallbackMessage - Mensaje por defecto
     * @returns {Promise<never>}
     */
    window.handleApiError = async function(response, fallbackMessage = 'Error en la petición') {
        let errorMsg = fallbackMessage;
        
        try {
            const data = await response.json();
            errorMsg = data.error || data.message || data.detail || fallbackMessage;
        } catch (e) {
            // Si no se puede parsear JSON, usar texto o mensaje por defecto
            try {
                const text = await response.text();
                if (text) errorMsg = text.slice(0, 200);
            } catch (e2) {
                // Mantener mensaje por defecto
            }
        }
        
        // Manejar específicamente error 401
        if (response.status === 401) {
            // No redirigir en endpoints de auth
            const url = response.url;
            if (!url.includes('/api/auth/')) {
                localStorage.removeItem(CONFIG.TOKEN_KEY);
                localStorage.removeItem(CONFIG.USER_KEY);
                showToast('Sesión expirada. Por favor inicia sesión nuevamente.', 'warning');
                setTimeout(() => {
                    window.location.href = CONFIG.LOGIN_URL;
                }, 1500);
            }
        }
        
        throw new Error(errorMsg);
    };

    /**
     * Petición GET autenticada
     */
    window.apiGet = async function(url, options = {}) {
        const response = await fetch(url, {
            method: 'GET',
            headers: getAuthHeaders(options.headers),
            ...options
        });
        
        if (!response.ok) {
            await handleApiError(response, 'Error al obtener datos');
        }
        
        return response.json();
    };

    /**
     * Petición POST autenticada
     */
    window.apiPost = async function(url, data, options = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: getAuthHeaders(options.headers),
            body: JSON.stringify(data),
            ...options
        });
        
        if (!response.ok) {
            await handleApiError(response, 'Error al enviar datos');
        }
        
        return response.json();
    };

    /**
     * Petición PUT autenticada
     */
    window.apiPut = async function(url, data, options = {}) {
        const response = await fetch(url, {
            method: 'PUT',
            headers: getAuthHeaders(options.headers),
            body: JSON.stringify(data),
            ...options
        });
        
        if (!response.ok) {
            await handleApiError(response, 'Error al actualizar datos');
        }
        
        return response.json();
    };

    /**
     * Petición DELETE autenticada
     */
    window.apiDelete = async function(url, options = {}) {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: getAuthHeaders(options.headers),
            ...options
        });
        
        if (!response.ok) {
            await handleApiError(response, 'Error al eliminar');
        }
        
        return response.json();
    };

    // ============================================================
    // INTERCEPTOR GLOBAL DE FETCH (Manejo automático de 401)
    // ============================================================
    
    const originalFetch = window.fetch;
    let isRedirecting = false;
    
    window.fetch = function(...args) {
        return originalFetch(...args).then(response => {
            // Si es 401 y no estamos en medio de una redirección
            if (response.status === 401 && !isRedirecting) {
                const url = args[0];
                // No redirigir en endpoints de autenticación
                const isAuthEndpoint = typeof url === 'string' && (
                    url.includes('/api/auth/') || 
                    url.includes('/portal/login') ||
                    url.includes('/portal/register')
                );
                
                if (!isAuthEndpoint) {
                    isRedirecting = true;
                    localStorage.removeItem(CONFIG.TOKEN_KEY);
                    localStorage.removeItem(CONFIG.USER_KEY);
                    localStorage.removeItem('token_timestamp');
                    
                    showToast('Tu sesión ha expirado. Por favor inicia sesión nuevamente.', 'warning');
                    
                    setTimeout(() => {
                        window.location.href = CONFIG.LOGIN_URL;
                    }, 500);
                }
            }
            return response;
        });
    };

    // ============================================================
    // NAVBAR Y UI
    // ============================================================
    
    /**
     * Actualiza la navbar según el estado de sesión
     */
    window.updateNavbar = function() {
        const token = getToken();
        const user = getCurrentUser();
        const navLogout = document.getElementById('nav-logout');
        const navLogin = document.getElementById('nav-login');
        const navUser = document.getElementById('nav-user');
        
        if (token && user) {
            if (navLogout) navLogout.style.display = 'inline-flex';
            if (navLogin) navLogin.style.display = 'none';
            
            // Mostrar nombre de usuario en navbar si existe el elemento
            if (navUser) {
                const nombre = user.nombre_completo || user.nombre || user.email;
                const nombreCorto = nombre.split(' ')[0];
                navUser.textContent = `👤 ${nombreCorto}`;
                navUser.style.display = 'inline-flex';
            }
        } else {
            if (navLogout) navLogout.style.display = 'none';
            if (navLogin) navLogin.style.display = 'inline-flex';
            if (navUser) navUser.style.display = 'none';
        }
    };

    /**
     * Carga el avatar del usuario
     */
    window.loadUserAvatar = function(avatarElementId = 'avatar', nameElementId = 'welcome-name', emailElementId = 'welcome-email') {
        const user = getCurrentUser();
        if (!user) return;
        
        const nombre = user.nombre_completo || user.nombre || 'Usuario';
        const avatar = document.getElementById(avatarElementId);
        const welcomeName = document.getElementById(nameElementId);
        const welcomeEmail = document.getElementById(emailElementId);
        
        if (avatar) {
            avatar.textContent = nombre.charAt(0).toUpperCase();
        }
        if (welcomeName) {
            welcomeName.textContent = 'Hola, ' + nombre.split(' ')[0];
        }
        if (welcomeEmail && user.email) {
            welcomeEmail.textContent = user.email;
        }
    };

    // ============================================================
    // ESTILOS DINÁMICOS (Para toasts y animaciones)
    // ============================================================
    
    function addGlobalStyles() {
        if (document.getElementById('base-global-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'base-global-styles';
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
            
            .toast-notification {
                pointer-events: auto;
            }
            
            .toast-notification:hover {
                opacity: 0.95;
            }
        `;
        document.head.appendChild(style);
    }

    // ============================================================
    // INICIALIZACIÓN
    // ============================================================
    
    /**
     * Inicializa el script base
     */
    function init() {
        addGlobalStyles();
        updateNavbar();
        
        // Agregar event listener para clicks en botones de logout dinámicos
        document.addEventListener('click', function(e) {
            if (e.target.closest('#nav-logout') || e.target.closest('.logout-btn')) {
                e.preventDefault();
                logout();
            }
        });
    }
    
    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Exportar CONFIG para uso externo si es necesario
    window.APP_CONFIG = CONFIG;
    
})();