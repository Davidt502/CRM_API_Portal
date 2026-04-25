/**
 * CRM API Portal - Login Script
 * Maneja el inicio de sesión de usuarios
 */

(function() {
    'use strict';

    // Si ya tiene token válido, redirigir al dashboard
    const existingToken = localStorage.getItem('api_token');
    const existingUser = localStorage.getItem('api_user');
    
    if (existingToken && existingUser) {
        window.location.href = '/portal/dashboard';
        return;
    }

    // Elementos del DOM
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('btn-login');
    const alertError = document.getElementById('alert-error');
    const loginForm = document.getElementById('login-form');

    /**
     * Muestra un mensaje de error
     * @param {string} message - Mensaje de error
     */
    function showError(message) {
        if (alertError) {
            alertError.textContent = message;
            alertError.classList.add('show');
            
            // Auto-ocultar después de 5 segundos
            setTimeout(() => {
                alertError.classList.remove('show');
            }, 5000);
        }
    }

    /**
     * Oculta el mensaje de error
     */
    function hideError() {
        if (alertError) {
            alertError.classList.remove('show');
        }
    }

    /**
     * Valida el formulario antes de enviar
     * @returns {boolean}
     */
    function validateForm() {
        const email = emailInput?.value.trim() || '';
        const password = passwordInput?.value || '';

        if (!email) {
            showError('Por favor ingresa tu correo electrónico');
            emailInput?.focus();
            return false;
        }

        if (!isValidEmail(email)) {
            showError('Por favor ingresa un correo electrónico válido');
            emailInput?.focus();
            return false;
        }

        if (!password) {
            showError('Por favor ingresa tu contraseña');
            passwordInput?.focus();
            return false;
        }

        if (password.length < 6) {
            showError('La contraseña debe tener al menos 6 caracteres');
            passwordInput?.focus();
            return false;
        }

        return true;
    }

    /**
     * Valida formato de email
     * @param {string} email
     * @returns {boolean}
     */
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@([^\s@]+\.)+[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Realiza la petición de login
     */
    async function doLogin() {
        // Validar formulario
        if (!validateForm()) return;

        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        // Deshabilitar botón y mostrar estado de carga
        if (loginBtn) {
            loginBtn.textContent = 'Verificando...';
            loginBtn.disabled = true;
        }
        
        hideError();

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            let data;
            try {
                data = await response.json();
            } catch (e) {
                throw new Error('Respuesta inválida del servidor');
            }

            if (response.ok && data.success) {
                // Guardar sesión usando el helper global si existe
                if (typeof setSession === 'function') {
                    setSession(data.token, data.user);
                } else {
                    // Fallback si base.js no cargó
                    localStorage.setItem('api_token', data.token);
                    localStorage.setItem('api_user', JSON.stringify(data.user));
                    localStorage.setItem('token_timestamp', Date.now().toString());
                }
                
                // Mostrar mensaje de éxito
                if (typeof showToast === 'function') {
                    showToast('¡Bienvenido ' + (data.user?.nombre_completo?.split(' ')[0] || 'Usuario') + '!', 'success');
                }
                
                // Redirigir al dashboard
                window.location.href = '/portal/dashboard';
            } else {
                // Mostrar error específico
                let errorMsg = data.error || data.message || 'Credenciales incorrectas';
                
                // Mensajes específicos según código de error
                if (response.status === 401) {
                    errorMsg = 'Correo o contraseña incorrectos';
                } else if (response.status === 403) {
                    errorMsg = 'Cuenta bloqueada. Contacta al administrador';
                } else if (response.status === 429) {
                    errorMsg = 'Demasiados intentos. Espera unos minutos';
                }
                
                showError(errorMsg);
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('Error de conexión. Verifica tu conexión a internet e intenta nuevamente.');
        } finally {
            // Restaurar botón
            if (loginBtn) {
                loginBtn.textContent = 'Iniciar Sesión';
                loginBtn.disabled = false;
            }
        }
    }

    /**
     * Limpia el formulario
     */
    function clearForm() {
        if (emailInput) emailInput.value = '';
        if (passwordInput) passwordInput.value = '';
        hideError();
        emailInput?.focus();
    }

    /**
     * Muestra un mensaje de carga
     */
    function showLoading() {
        if (loginBtn) {
            loginBtn.textContent = 'Cargando...';
            loginBtn.disabled = true;
        }
    }

    /**
     * Restaura el botón
     */
    function restoreButton() {
        if (loginBtn) {
            loginBtn.textContent = 'Iniciar Sesión';
            loginBtn.disabled = false;
        }
    }

    // Event Listeners
    if (loginBtn) {
        loginBtn.addEventListener('click', doLogin);
    }

    // Enter key support
    if (passwordInput) {
        passwordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                doLogin();
            }
        });
    }

    if (emailInput) {
        emailInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                passwordInput?.focus();
            }
        });
    }

    // Limpiar error al escribir
    if (emailInput) {
        emailInput.addEventListener('input', hideError);
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', hideError);
    }

    // Mostrar demo credentials en desarrollo (opcional)
    const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isDev) {
        console.log('🔐 Modo desarrollo - Credenciales de prueba:');
        console.log('   Admin: admin@crm.com / admin123');
        console.log('   User:  usuario@crm.com / user123');
    }

    // Auto-focus en email
    emailInput?.focus();

    // Exportar funciones útiles globalmente (por si se necesitan)
    window.loginHelpers = {
        doLogin,
        clearForm,
        showLoading,
        restoreButton,
        showError,
        hideError
    };
})();