/**
 * CRM API Portal - Dashboard Script
 * Maneja la página principal del dashboard
 */

(function() {
    'use strict';

    // Verificar autenticación
    if (typeof checkAuth === 'function') {
        if (!checkAuth(true)) return;
    } else {
        // Fallback si base.js no cargó
        const token = localStorage.getItem('api_token');
        const user = JSON.parse(localStorage.getItem('api_user') || 'null');
        if (!token || !user) {
            window.location.href = '/portal/login';
            return;
        }
    }

    // Obtener datos del usuario
    const token = localStorage.getItem('api_token');
    const user = JSON.parse(localStorage.getItem('api_user') || 'null');

    /**
     * Carga los datos del usuario en la UI
     */
    function loadUserData() {
        if (!user) return;
        
        const nombre = user.nombre_completo || user.nombre || 'Usuario';
        const nombreCorto = nombre.split(' ')[0];
        
        // Elementos del DOM
        const welcomeName = document.getElementById('welcome-name');
        const welcomeEmail = document.getElementById('welcome-email');
        const avatar = document.getElementById('avatar');
        
        if (welcomeName) {
            welcomeName.textContent = `Hola, ${nombreCorto}`;
        }
        
        if (welcomeEmail && user.email) {
            welcomeEmail.textContent = user.email;
        }
        
        if (avatar) {
            avatar.textContent = nombre.charAt(0).toUpperCase();
        }
    }

    /**
     * Muestra el token truncado
     */
    function displayToken() {
        const tokenDisplay = document.getElementById('token-display');
        if (tokenDisplay && token) {
            const truncatedToken = token.length > 60 
                ? `${token.slice(0, 40)}...${token.slice(-20)}`
                : token;
            tokenDisplay.textContent = truncatedToken;
        }
    }

    /**
     * Copia el token al portapapeles
     */
    async function copyToken() {
        if (!token) {
            if (typeof showToast === 'function') {
                showToast('No hay token disponible', 'error');
            }
            return;
        }
        
        try {
            await navigator.clipboard.writeText(token);
            
            // Cambiar texto del botón temporalmente
            const copyBtn = document.querySelector('.copy-btn');
            if (copyBtn) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = '✓ ¡Copiado!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
            
            if (typeof showToast === 'function') {
                showToast('Token copiado al portapapeles', 'success');
            }
        } catch (err) {
            console.error('Error al copiar token:', err);
            if (typeof showToast === 'function') {
                showToast('No se pudo copiar el token', 'error');
            }
        }
    }

    /**
     * Carga estadísticas del usuario (si es necesario)
     */
    async function loadUserStats() {
        // Opcional: cargar estadísticas del usuario desde el backend
        // Solo si el usuario es admin o si hay un endpoint específico
        const isAdminUser = user?.rol === 'admin';
        
        if (isAdminUser) {
            try {
                const response = await fetch('/api/reports/stats', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const stats = await response.json();
                    // Actualizar estadísticas en el dashboard si existen elementos
                    const statsContainer = document.getElementById('quick-stats');
                    if (statsContainer) {
                        // Renderizar estadísticas
                        statsContainer.innerHTML = `
                            <div class="stat-item">
                                <span class="stat-label">Usuarios</span>
                                <span class="stat-value">${stats.total_usuarios || 0}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Requests hoy</span>
                                <span class="stat-value">${stats.requests_hoy || 0}</span>
                            </div>
                        `;
                    }
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
    }

    /**
     * Verifica el estado del token
     */
    function checkTokenStatus() {
        const tokenTimestamp = localStorage.getItem('token_timestamp');
        if (tokenTimestamp) {
            const elapsed = Date.now() - parseInt(tokenTimestamp);
            const hoursRemaining = Math.max(0, 8 - Math.floor(elapsed / (1000 * 60 * 60)));
            
            const tokenStatus = document.getElementById('token-status');
            if (tokenStatus) {
                if (hoursRemaining <= 1) {
                    tokenStatus.innerHTML = `⚠️ Token expira en ${hoursRemaining} hora${hoursRemaining !== 1 ? 's' : ''}`;
                    tokenStatus.style.color = '#f97316';
                } else if (hoursRemaining <= 2) {
                    tokenStatus.innerHTML = `⚠️ Token expira en ${hoursRemaining} horas`;
                    tokenStatus.style.color = '#eab308';
                } else {
                    tokenStatus.innerHTML = `✓ Token válido por ${hoursRemaining} horas`;
                    tokenStatus.style.color = '#00e5a0';
                }
            }
        }
    }

    /**
     * Actualiza la hora actual
     */
    function updateCurrentTime() {
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            const now = new Date();
            const formattedTime = now.toLocaleString('es-GT', {
                dateStyle: 'full',
                timeStyle: 'medium'
            });
            timeElement.textContent = formattedTime;
        }
    }

    /**
     * Inicializa el dashboard
     */
    function init() {
        loadUserData();
        displayToken();
        checkTokenStatus();
        updateCurrentTime();
        
        // Actualizar hora cada minuto
        setInterval(updateCurrentTime, 60000);
        
        // Cargar estadísticas (opcional)
        loadUserStats();
        
        // Agregar event listener para logout si existe
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn && typeof logout === 'function') {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                logout();
            });
        }
    }

    // Hacer copyToken global para el onclick del HTML
    window.copyToken = copyToken;

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();