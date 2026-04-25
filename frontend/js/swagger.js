/**
 * CRM API Portal - Swagger Script
 * Inicializa y configura Swagger UI con autenticación automática
 */

(function() {
    'use strict';

    // Verificar si existe token
    const token = localStorage.getItem('api_token');
    const authBanner = document.getElementById('auth-banner');
    
    // Mostrar banner si no hay token
    if (!token && authBanner) {
        authBanner.classList.add('show');
    } else if (token && authBanner) {
        authBanner.classList.remove('show');
    }

    /**
     * Inicializa Swagger UI
     */
    function initSwagger() {
        // Esperar a que Swagger UI esté disponible
        if (typeof SwaggerUIBundle === 'undefined') {
            console.warn('Swagger UI Bundle not loaded yet, retrying...');
            setTimeout(initSwagger, 100);
            return;
        }

        const ui = SwaggerUIBundle({
            url: '/api/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            layout: 'StandaloneLayout',
            persistAuthorization: true,
            docExpansion: 'none', // 'none', 'list', 'full'
            filter: true, // Habilitar filtro de endpoints
            showExtensions: true,
            showCommonExtensions: true,
            tryItOutEnabled: true, // Habilitar "Try it out" por defecto
            
            // Interceptor para agregar token automáticamente
            requestInterceptor: (request) => {
                const currentToken = localStorage.getItem('api_token');
                if (currentToken && !request.headers['Authorization']) {
                    request.headers['Authorization'] = `Bearer ${currentToken}`;
                }
                
                // Log de la petición (solo en desarrollo)
                if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                    console.log('📤 Swagger Request:', {
                        url: request.url,
                        method: request.method,
                        headers: request.headers
                    });
                }
                
                return request;
            },
            
            // Interceptor para respuestas
            responseInterceptor: (response) => {
                // Log de la respuesta (solo en desarrollo)
                if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                    console.log('📥 Swagger Response:', {
                        url: response.url,
                        status: response.status,
                        statusText: response.statusText
                    });
                }
                
                // Manejar 401 - token expirado
                if (response.status === 401) {
                    const currentToken = localStorage.getItem('api_token');
                    if (currentToken) {
                        localStorage.removeItem('api_token');
                        localStorage.removeItem('api_user');
                        
                        if (typeof showToast === 'function') {
                            showToast('Tu sesión ha expirado. Por favor inicia sesión nuevamente.', 'warning');
                        }
                        
                        // Recargar para mostrar banner
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }
                }
                
                return response;
            }
        });

        // Auto-autorizar con el token guardado
        if (token) {
            // Esperar a que Swagger UI esté completamente inicializado
            setTimeout(() => {
                try {
                    ui.preauthorizeApiKey('BearerAuth', token);
                    console.log('✅ Token autorizado en Swagger UI');
                } catch (error) {
                    console.warn('Error al autorizar token:', error);
                }
            }, 500);
        }

        window.ui = ui;
    }

    /**
     * Escucha cambios en el token para actualizar Swagger
     */
    function listenTokenChanges() {
        // Observar cambios en localStorage
        const originalSetItem = localStorage.setItem;
        localStorage.setItem = function(key, value) {
            const event = new Event('localStorageChange');
            event.key = key;
            event.oldValue = localStorage.getItem(key);
            event.newValue = value;
            originalSetItem.apply(this, arguments);
            window.dispatchEvent(event);
        };

        window.addEventListener('localStorageChange', (e) => {
            if (e.key === 'api_token' && window.ui) {
                const newToken = e.newValue;
                if (newToken) {
                    try {
                        window.ui.preauthorizeApiKey('BearerAuth', newToken);
                        console.log('🔄 Token actualizado en Swagger UI');
                        
                        // Ocultar banner si existe
                        const banner = document.getElementById('auth-banner');
                        if (banner) banner.classList.remove('show');
                    } catch (error) {
                        console.warn('Error al actualizar token:', error);
                    }
                }
            }
        });
    }

    /**
     * Agrega controles adicionales a Swagger UI
     */
    function addCustomControls() {
        // Esperar a que Swagger UI esté en el DOM
        const checkInterval = setInterval(() => {
            const swaggerContainer = document.getElementById('swagger-ui');
            if (swaggerContainer && swaggerContainer.children.length > 0) {
                clearInterval(checkInterval);
                
                // Agregar botón para limpiar token si existe
                const toolbar = document.querySelector('.swagger-ui .information-container');
                if (toolbar && !document.getElementById('swagger-clear-token')) {
                    const clearBtn = document.createElement('button');
                    clearBtn.id = 'swagger-clear-token';
                    clearBtn.textContent = '🗑️ Limpiar Token';
                    clearBtn.style.cssText = `
                        position: absolute;
                        top: 10px;
                        right: 20px;
                        background: #ff4d6d;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 12px;
                        cursor: pointer;
                        z-index: 100;
                    `;
                    
                    clearBtn.onclick = () => {
                        localStorage.removeItem('api_token');
                        localStorage.removeItem('api_user');
                        if (typeof showToast === 'function') {
                            showToast('Token eliminado. Recarga la página para continuar.', 'info');
                        }
                        setTimeout(() => window.location.reload(), 1500);
                    };
                    
                    // Solo mostrar si hay token
                    if (localStorage.getItem('api_token')) {
                        const wrapper = document.querySelector('.swagger-ui .topbar');
                        if (wrapper) {
                            wrapper.style.position = 'relative';
                            wrapper.appendChild(clearBtn);
                        }
                    }
                }
            }
        }, 1000);
    }

    /**
     * Agrega atajos de teclado
     */
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl + K: enfocar filtro de Swagger
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const filterInput = document.querySelector('.swagger-ui .filter-container input');
                if (filterInput) {
                    filterInput.focus();
                    if (typeof showToast === 'function') {
                        showToast('Filtro activado', 'info');
                    }
                }
            }
            
            // Ctrl + R: recargar documentación
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                if (window.ui) {
                    window.ui.specActions.updateUrl('/api/openapi.json');
                    window.ui.specActions.download();
                    if (typeof showToast === 'function') {
                        showToast('Recargando especificación...', 'info');
                    }
                }
            }
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initSwagger();
            listenTokenChanges();
            addCustomControls();
            addKeyboardShortcuts();
        });
    } else {
        initSwagger();
        listenTokenChanges();
        addCustomControls();
        addKeyboardShortcuts();
    }
})();