/**
 * CRM API Portal - Register Script
 * Maneja el registro de nuevos usuarios
 */

(function() {
    'use strict';

    // Si ya tiene sesión, redirigir al dashboard
    const existingToken = localStorage.getItem('api_token');
    if (existingToken) {
        window.location.href = '/portal/dashboard';
        return;
    }

    // Elementos del DOM
    const nombreInput = document.getElementById('nombre');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const terminosCheckbox = document.getElementById('terminos');
    const registerBtn = document.getElementById('btn-register');
    const alertError = document.getElementById('alert-error');
    const alertSuccess = document.getElementById('alert-success');
    const passBar = document.getElementById('pass-bar');

    // Variables de estado
    let isSubmitting = false;
    let passwordStrength = 0;

    /**
     * Calcula la fortaleza de la contraseña
     * @param {string} password
     * @returns {number} Score de 0 a 5
     */
    function calculatePasswordStrength(password) {
        if (!password) return 0;
        
        let score = 0;
        
        // Longitud
        if (password.length >= 8) score++;
        if (password.length >= 12) score++;
        
        // Mayúsculas y minúsculas
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
        
        // Números
        if (/[0-9]/.test(password)) score++;
        
        // Caracteres especiales
        if (/[^a-zA-Z0-9]/.test(password)) score++;
        
        return Math.min(score, 5);
    }

    /**
     * Obtiene el color según la fortaleza
     * @param {number} score
     * @returns {string}
     */
    function getStrengthColor(score) {
        const colors = {
            0: '#ff4d6d',  // Muy débil
            1: '#ff4d6d',  // Débil
            2: '#f97316',  // Regular
            3: '#eab308',  // Buena
            4: '#00e5a0',  // Fuerte
            5: '#00e5a0'   // Muy fuerte
        };
        return colors[score] || '#ff4d6d';
    }

    /**
     * Obtiene el ancho según la fortaleza
     * @param {number} score
     * @returns {string}
     */
    function getStrengthWidth(score) {
        const widths = {
            0: '0%',
            1: '20%',
            2: '40%',
            3: '60%',
            4: '80%',
            5: '100%'
        };
        return widths[score] || '0%';
    }

    /**
     * Actualiza el indicador de fortaleza de contraseña
     */
    function updatePasswordStrength() {
        if (!passBar) return;
        
        const password = passwordInput?.value || '';
        passwordStrength = calculatePasswordStrength(password);
        
        passBar.style.background = getStrengthColor(passwordStrength);
        passBar.style.width = getStrengthWidth(passwordStrength);
        
        // Opcional: agregar texto de ayuda
        const strengthText = document.getElementById('strength-text');
        if (strengthText) {
            const texts = {
                0: 'Muy débil',
                1: 'Débil',
                2: 'Regular',
                3: 'Buena',
                4: 'Fuerte',
                5: 'Muy fuerte'
            };
            strengthText.textContent = texts[passwordStrength] || '';
            strengthText.style.color = getStrengthColor(passwordStrength);
        }
    }

    /**
     * Muestra un error en un campo específico
     * @param {string} field
     * @param {string} message
     */
    function showFieldError(field, message) {
        const errorEl = document.getElementById(`err-${field}`);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }

    /**
     * Oculta todos los errores de campo
     */
    function hideAllFieldErrors() {
        const fields = ['nombre', 'email', 'password'];
        fields.forEach(field => {
            const errorEl = document.getElementById(`err-${field}`);
            if (errorEl) {
                errorEl.style.display = 'none';
            }
        });
    }

    /**
     * Muestra un mensaje de error general
     * @param {string} message
     */
    function showError(message) {
        if (alertError) {
            alertError.textContent = message;
            alertError.classList.add('show');
            
            setTimeout(() => {
                alertError.classList.remove('show');
            }, 5000);
        }
    }

    /**
     * Muestra un mensaje de éxito
     * @param {string} message
     */
    function showSuccess(message) {
        if (alertSuccess) {
            alertSuccess.textContent = message;
            alertSuccess.classList.add('show');
        }
    }

    /**
     * Oculta mensajes de alerta
     */
    function hideAlerts() {
        if (alertError) alertError.classList.remove('show');
        if (alertSuccess) alertSuccess.classList.remove('show');
    }

    /**
     * Valida el formulario antes de enviar
     * @returns {boolean}
     */
    function validateForm() {
        let isValid = true;
        hideAllFieldErrors();
        hideAlerts();

        const nombre = nombreInput?.value.trim() || '';
        const email = emailInput?.value.trim() || '';
        const password = passwordInput?.value || '';
        const terminos = terminosCheckbox?.checked || false;

        // Validar nombre
        if (!nombre) {
            showFieldError('nombre', 'El nombre completo es requerido');
            isValid = false;
        } else if (nombre.length < 3) {
            showFieldError('nombre', 'El nombre debe tener al menos 3 caracteres');
            isValid = false;
        } else if (nombre.length > 100) {
            showFieldError('nombre', 'El nombre no puede exceder 100 caracteres');
            isValid = false;
        }

        // Validar email
        if (!email) {
            showFieldError('email', 'El correo electrónico es requerido');
            isValid = false;
        } else if (!isValidEmail(email)) {
            showFieldError('email', 'Ingresa un correo electrónico válido');
            isValid = false;
        }

        // Validar contraseña
        if (!password) {
            showFieldError('password', 'La contraseña es requerida');
            isValid = false;
        } else if (password.length < 8) {
            showFieldError('password', 'La contraseña debe tener al menos 8 caracteres');
            isValid = false;
        } else if (passwordStrength < 3) {
            showFieldError('password', 'La contraseña es muy débil. Usa mayúsculas, números y caracteres especiales');
            isValid = false;
        }

        // Validar términos
        if (!terminos) {
            showError('Debes aceptar los términos y condiciones y el aviso de privacidad');
            isValid = false;
        }

        return isValid;
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
     * Realiza la petición de registro
     */
    async function doRegister() {
        // Prevenir múltiples envíos
        if (isSubmitting) return;
        
        // Validar formulario
        if (!validateForm()) return;

        const nombre = nombreInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const terminos = terminosCheckbox.checked;

        isSubmitting = true;
        
        if (registerBtn) {
            registerBtn.textContent = 'Registrando...';
            registerBtn.disabled = true;
        }

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    nombre_completo: nombre,
                    email: email,
                    password: password,
                    acepto_terminos: terminos
                })
            });

            let data;
            try {
                data = await response.json();
            } catch (e) {
                throw new Error('Respuesta inválida del servidor');
            }

            if (response.ok && data.success) {
                // Mostrar mensaje de éxito
                showSuccess('✓ ¡Cuenta creada exitosamente! Redirigiendo al inicio de sesión...');
                
                // Si hay función de toast, mostrarla también
                if (typeof showToast === 'function') {
                    showToast('¡Registro exitoso! Ya puedes iniciar sesión', 'success');
                }
                
                // Limpiar formulario
                if (nombreInput) nombreInput.value = '';
                if (emailInput) emailInput.value = '';
                if (passwordInput) passwordInput.value = '';
                if (terminosCheckbox) terminosCheckbox.checked = false;
                if (passBar) passBar.style.width = '0%';
                
                // Redirigir después de 2 segundos
                setTimeout(() => {
                    window.location.href = '/portal/login';
                }, 2000);
            } else {
                // Mostrar errores específicos del backend
                if (data.fields && typeof data.fields === 'object') {
                    Object.entries(data.fields).forEach(([field, message]) => {
                        // Mapear nombre_completo a nombre
                        const mappedField = field === 'nombre_completo' ? 'nombre' : field;
                        showFieldError(mappedField, message);
                    });
                }
                
                // Mostrar error general si existe
                if (data.error) {
                    showError(data.error);
                } else if (!data.fields) {
                    showError('Error al registrar. Por favor intenta nuevamente.');
                }
            }
        } catch (error) {
            console.error('Register error:', error);
            showError('Error de conexión. Verifica tu conexión a internet e intenta nuevamente.');
        } finally {
            isSubmitting = false;
            if (registerBtn) {
                registerBtn.textContent = 'Crear cuenta';
                registerBtn.disabled = false;
            }
        }
    }

    /**
     * Limpia todos los campos del formulario
     */
    function clearForm() {
        if (nombreInput) nombreInput.value = '';
        if (emailInput) emailInput.value = '';
        if (passwordInput) passwordInput.value = '';
        if (terminosCheckbox) terminosCheckbox.checked = false;
        if (passBar) passBar.style.width = '0%';
        hideAllFieldErrors();
        hideAlerts();
    }

    // Event Listeners
    if (registerBtn) {
        registerBtn.addEventListener('click', doRegister);
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', updatePasswordStrength);
    }

    // Enter key support
    const formInputs = [nombreInput, emailInput, passwordInput];
    formInputs.forEach((input, index) => {
        if (input) {
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const nextInput = formInputs[index + 1];
                    if (nextInput) {
                        nextInput.focus();
                    } else {
                        doRegister();
                    }
                }
            });
        }
    });

    // Limpiar errores al escribir
    if (nombreInput) {
        nombreInput.addEventListener('input', () => {
            const errorEl = document.getElementById('err-nombre');
            if (errorEl) errorEl.style.display = 'none';
        });
    }
    
    if (emailInput) {
        emailInput.addEventListener('input', () => {
            const errorEl = document.getElementById('err-email');
            if (errorEl) errorEl.style.display = 'none';
        });
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', () => {
            const errorEl = document.getElementById('err-password');
            if (errorEl) errorEl.style.display = 'none';
            hideAlerts();
        });
    }

    if (terminosCheckbox) {
        terminosCheckbox.addEventListener('change', () => {
            if (alertError) alertError.classList.remove('show');
        });
    }

    // Auto-focus en nombre
    nombreInput?.focus();

    // Exportar funciones útiles
    window.registerHelpers = {
        doRegister,
        clearForm,
        validateForm,
        checkStrength: updatePasswordStrength
    };
})();