/**
 * CRM API Portal - Reports Script
 * Maneja la página de reportes de actividad
 */

(function() {
    'use strict';

    // Verificar autenticación
    const token = localStorage.getItem('api_token');
    const user = JSON.parse(localStorage.getItem('api_user') || 'null');

    if (!token || !user) {
        window.location.href = '/portal/login';
        return;
    }

    const isAdmin = user?.rol === 'admin';
    let currentPage = 1;
    let totalPages = 1;
    let isLoading = false;
    let currentFilters = {
        fecha_inicio: '',
        fecha_fin: '',
        email: '',
        endpoint: ''
    };

    // Elementos del DOM
    const tableBody = document.getElementById('table-body');
    const tableCount = document.getElementById('table-count');
    const pagination = document.getElementById('pagination');
    const statsGrid = document.getElementById('stats-grid');
    const filterEmailWrap = document.getElementById('filter-email-wrap');

    /**
     * Escapa HTML para prevenir XSS
     */
    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * Formatea fecha para mostrar
     */
    function formatDate(isoString) {
        if (!isoString) return '—';
        try {
            const date = new Date(isoString);
            if (isNaN(date.getTime())) return '—';
            return date.toLocaleString('es-GT', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (e) {
            return '—';
        }
    }

    /**
     * Obtiene la clase CSS para el badge de método HTTP
     */
    function getMethodBadgeClass(method) {
        if (!method) return 'badge';
        const methodLower = method.toLowerCase();
        const classes = {
            get: 'badge-get',
            post: 'badge-post',
            put: 'badge-put',
            patch: 'badge-patch',
            delete: 'badge-delete'
        };
        return `badge ${classes[methodLower] || 'badge'}`;
    }

    /**
     * Obtiene la clase CSS para el badge de código de estado
     */
    function getStatusBadgeClass(statusCode) {
        if (!statusCode) return 'badge';
        if (statusCode < 300) return 'badge badge-2xx';
        if (statusCode < 400) return 'badge badge-2xx'; // Redirecciones
        if (statusCode < 500) return 'badge badge-4xx';
        return 'badge badge-5xx';
    }

    /**
     * Renderiza la tabla con los datos
     */
    function renderTable(rows) {
        if (!tableBody) return;

        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<div class="empty">📭 Sin resultados para los filtros aplicados</div>';
            return;
        }

        let html = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>IP</th>
                        <th>Método</th>
                        <th>Endpoint</th>
                        <th>Status</th>
                        <th>Duración</th>
                        <th>Fecha</th>
                        ${isAdmin ? '<th>User Agent</th>' : ''}
                    </tr>
                </thead>
                <tbody>
        `;

        for (const row of rows) {
            const nombreUsuario = escapeHtml(row.nombre_usuario || 'Anónimo');
            const emailUsuario = escapeHtml(row.email_usuario || '');
            const ipAddress = escapeHtml(row.ip_address || '—');
            const endpoint = escapeHtml(truncateText(row.endpoint || '—', 50));
            const duration = row.duracion_ms != null ? `${row.duracion_ms}ms` : '—';
            const userAgent = escapeHtml(truncateText(row.user_agent || '—', 60));

            html += `
                <tr>
                    <td class="user-cell">
                        <div class="user-name">${nombreUsuario}</div>
                        ${emailUsuario ? `<div class="user-email">${emailUsuario}</div>` : ''}
                    </td>
                    <td class="ip-cell">${ipAddress}</td>
                    <td><span class="${getMethodBadgeClass(row.metodo_http)}">${row.metodo_http || '—'}</span></td>
                    <td class="endpoint-cell">${endpoint}</td>
                    <td><span class="${getStatusBadgeClass(row.status_code)}">${row.status_code || '—'}</span></td>
                    <td class="duration-cell">${duration}</td>
                    <td class="date-cell">${formatDate(row.fecha_acceso)}</td>
                    ${isAdmin ? `<td class="ua-cell" title="${userAgent.replace(/&lt;/g, '<').replace(/&gt;/g, '>')}">${userAgent}</td>` : ''}
                </tr>
            `;
        }

        html += `
                </tbody>
            </table>
        `;

        tableBody.innerHTML = html;
    }

    /**
     * Trunca texto a una longitud máxima
     */
    function truncateText(text, maxLength = 50) {
        if (!text) return '—';
        if (text.length <= maxLength) return text;
        return text.slice(0, maxLength) + '…';
    }

    /**
     * Renderiza la paginación
     */
    function renderPagination(total, perPage, current) {
        if (!pagination) return;

        const totalPages = Math.ceil(total / perPage);
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let html = `
            <button class="page-btn" id="first-page" ${current === 1 ? 'disabled' : ''}>« Primera</button>
            <button class="page-btn" id="prev-page" ${current === 1 ? 'disabled' : ''}>‹ Anterior</button>
        `;

        // Mostrar páginas alrededor de la actual
        let startPage = Math.max(1, current - 2);
        let endPage = Math.min(totalPages, current + 2);

        if (startPage > 1) {
            html += `<button class="page-btn" data-page="1">1</button>`;
            if (startPage > 2) html += `<span class="page-dots">...</span>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="page-btn ${i === current ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += `<span class="page-dots">...</span>`;
            html += `<button class="page-btn" data-page="${totalPages}">${totalPages}</button>`;
        }

        html += `
            <button class="page-btn" id="next-page" ${current === totalPages ? 'disabled' : ''}>Siguiente ›</button>
            <button class="page-btn" id="last-page" ${current === totalPages ? 'disabled' : ''}>Última »</button>
        `;

        pagination.innerHTML = html;

        // Agregar event listeners
        const firstBtn = document.getElementById('first-page');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const lastBtn = document.getElementById('last-page');
        const pageBtns = pagination.querySelectorAll('[data-page]');

        if (firstBtn) firstBtn.onclick = () => loadData(1);
        if (prevBtn) prevBtn.onclick = () => loadData(current - 1);
        if (nextBtn) nextBtn.onclick = () => loadData(current + 1);
        if (lastBtn) lastBtn.onclick = () => loadData(totalPages);
        pageBtns.forEach(btn => {
            btn.onclick = () => loadData(parseInt(btn.dataset.page));
        });
    }

    /**
     * Muestra un estado de carga
     */
    function showLoading() {
        if (tableBody) {
            tableBody.innerHTML = '<div class="loading">⏳ Cargando datos...</div>';
        }
        if (tableCount) {
            tableCount.textContent = 'Cargando...';
        }
    }

    /**
     * Muestra un mensaje de error
     */
    function showError(message) {
        if (tableBody) {
            tableBody.innerHTML = `<div class="empty">❌ ${escapeHtml(message)}</div>`;
        }
        if (typeof showToast === 'function') {
            showToast(message, 'error');
        }
    }

    /**
     * Carga estadísticas (solo admin)
     */
    async function loadStats() {
        if (!isAdmin) return;

        try {
            const response = await fetch('/api/reports/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                if (typeof handleApiError === 'function') {
                    await handleApiError(response);
                }
                return;
            }

            if (!response.ok) {
                throw new Error('Error al cargar estadísticas');
            }

            const data = await response.json();
            
            const statUsuarios = document.getElementById('stat-usuarios');
            const statHoy = document.getElementById('stat-hoy');
            
            if (statUsuarios) statUsuarios.textContent = data.total_usuarios?.toLocaleString() || '0';
            if (statHoy) statHoy.textContent = data.requests_hoy?.toLocaleString() || '0';
        } catch (error) {
            console.error('Error loading stats:', error);
            const statUsuarios = document.getElementById('stat-usuarios');
            const statHoy = document.getElementById('stat-hoy');
            if (statUsuarios) statUsuarios.textContent = '—';
            if (statHoy) statHoy.textContent = '—';
        }
    }

    /**
     * Carga los datos de actividad
     */
    async function loadData(page = 1) {
        if (isLoading) return;
        
        isLoading = true;
        currentPage = page;
        showLoading();

        // Obtener valores de filtros
        const fechaInicio = document.getElementById('f-fecha-inicio')?.value || '';
        const fechaFin = document.getElementById('f-fecha-fin')?.value || '';
        const email = document.getElementById('f-email')?.value.trim() || '';
        const endpoint = document.getElementById('f-endpoint')?.value.trim() || '';

        // Actualizar filtros actuales
        currentFilters = { fecha_inicio: fechaInicio, fecha_fin: fechaFin, email, endpoint };

        // Construir URL con parámetros
        const params = new URLSearchParams({
            page: page,
            per_page: 30
        });
        
        if (fechaInicio) params.append('fecha_inicio', fechaInicio);
        if (fechaFin) params.append('fecha_fin', fechaFin);
        if (email) params.append('email', email);
        if (endpoint) params.append('endpoint', endpoint);

        try {
            const response = await fetch(`/api/reports/activity?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                if (typeof handleApiError === 'function') {
                    await handleApiError(response);
                }
                return;
            }

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Actualizar contador
            if (tableCount) {
                const total = data.total || 0;
                tableCount.textContent = `${total.toLocaleString()} registro${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`;
            }
            
            // Actualizar estadística de total
            const statTotal = document.getElementById('stat-total');
            if (statTotal && isAdmin) {
                statTotal.textContent = (data.total || 0).toLocaleString();
            }
            
            // Renderizar tabla y paginación
            renderTable(data.data || []);
            renderPagination(data.total || 0, data.per_page || 30, page);
            
        } catch (error) {
            console.error('Error loading data:', error);
            showError('Error al cargar los datos. Por favor intenta nuevamente.');
        } finally {
            isLoading = false;
        }
    }

    /**
     * Aplica filtros y recarga datos
     */
    function applyFilters() {
        loadData(1);
    }

    /**
     * Limpia todos los filtros
     */
    function clearFilters() {
        const fechaInicio = document.getElementById('f-fecha-inicio');
        const fechaFin = document.getElementById('f-fecha-fin');
        const email = document.getElementById('f-email');
        const endpoint = document.getElementById('f-endpoint');
        
        if (fechaInicio) fechaInicio.value = '';
        if (fechaFin) fechaFin.value = '';
        if (email) email.value = '';
        if (endpoint) endpoint.value = '';
        
        loadData(1);
    }

    /**
     * Exporta datos a CSV
     */
    async function exportCSV() {
        const fechaInicio = document.getElementById('f-fecha-inicio')?.value || '';
        const fechaFin = document.getElementById('f-fecha-fin')?.value || '';
        const email = document.getElementById('f-email')?.value.trim() || '';
        const endpoint = document.getElementById('f-endpoint')?.value.trim() || '';

        const params = new URLSearchParams();
        if (fechaInicio) params.append('fecha_inicio', fechaInicio);
        if (fechaFin) params.append('fecha_fin', fechaFin);
        if (email) params.append('email', email);
        if (endpoint) params.append('endpoint', endpoint);

        try {
            if (typeof showToast === 'function') {
                showToast('Generando archivo CSV...', 'info');
            }
            
            const response = await fetch(`/api/reports/activity/export?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                if (typeof handleApiError === 'function') {
                    await handleApiError(response);
                }
                return;
            }

            if (!response.ok) {
                throw new Error('Error al exportar');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_actividad_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            if (typeof showToast === 'function') {
                showToast('Exportación completada exitosamente', 'success');
            }
        } catch (error) {
            console.error('Export error:', error);
            if (typeof showToast === 'function') {
                showToast('Error al exportar los datos', 'error');
            } else {
                alert('Error al exportar los datos');
            }
        }
    }

    /**
     * Inicializa la página
     */
    function init() {
        // Configurar UI según rol
        if (statsGrid && !isAdmin) {
            statsGrid.style.display = 'none';
        } else if (statsGrid && isAdmin) {
            statsGrid.style.display = 'grid';
        }
        
        if (filterEmailWrap && !isAdmin) {
            filterEmailWrap.style.display = 'none';
        }
        
        // Cargar datos iniciales
        if (isAdmin) {
            loadStats();
        }
        loadData(1);
        
        // Bindear eventos
        const filterBtn = document.getElementById('filter-btn');
        const clearBtn = document.getElementById('clear-filters-btn');
        const exportBtn = document.getElementById('export-btn');
        const refreshBtn = document.getElementById('refresh-btn');
        
        if (filterBtn) filterBtn.addEventListener('click', applyFilters);
        if (clearBtn) clearBtn.addEventListener('click', clearFilters);
        if (exportBtn) exportBtn.addEventListener('click', exportCSV);
        if (refreshBtn) refreshBtn.addEventListener('click', () => loadData(currentPage));
        
        // Enter key en filtros
        const filterInputs = ['f-fecha-inicio', 'f-fecha-fin', 'f-email', 'f-endpoint'];
        filterInputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyFilters();
                    }
                });
            }
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exportar funciones útiles para uso global
    window.reportHelpers = {
        loadData,
        applyFilters,
        clearFilters,
        exportCSV,
        loadStats
    };
})();