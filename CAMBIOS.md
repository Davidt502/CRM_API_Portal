# 📋 Cambios y Mejoras — CRM API Portal v2

## 🔐 Seguridad

### Variables de entorno
- **ANTES**: `config.py` tenía valores por defecto hardcodeados (`"sa"`, `"localhost"`)
- **AHORA**: Todas las credenciales vienen **exclusivamente** de variables de entorno; si falta `SECRET_KEY` en producción, la app no arranca

### Base de datos
- **ANTES**: SQL Server con `pyodbc` (requiere drivers de Microsoft instalados en el servidor)
- **AHORA**: **Supabase (PostgreSQL)** con `psycopg2-binary` — más fácil de desplegar, sin drivers adicionales, SSL habilitado por defecto

### Token en dashboard
- **ANTES**: El token JWT completo se mostraba en pantalla
- **AHORA**: Solo se muestran los primeros 20 y últimos 10 caracteres; el token completo se copia pero no se ve

### Schema PostgreSQL
- Añadidas constraints `CHECK` en columnas `rol` y `estado`
- **Row Level Security (RLS)** habilitado en todas las tablas de Supabase
- La función `sp_portal_registrar_usuario` ahora es una función PostgreSQL nativa (no stored procedure de SQL Server)

---

## 🗄️ Base de datos migrada a Supabase

| Aspecto | Antes (SQL Server) | Ahora (Supabase/PostgreSQL) |
|---------|-------------------|------------------------------|
| Driver  | `pyodbc` + ODBC Driver 17 | `psycopg2-binary` |
| SSL     | Opcional | Requerido (`sslmode=require`) |
| Sintaxis | `GETDATE()`, `NVARCHAR`, `IDENTITY` | `NOW()`, `VARCHAR`, `SERIAL` |
| Deploy  | Requiere SQL Server | Supabase gratuito |
| RLS     | No | Habilitado |

---

## 🚀 Deploy en Render

### Archivos nuevos
- **`render.yaml`** — configuración declarativa del servicio
- **`DEPLOY_GUIDE.md`** — guía paso a paso completa

### `app.py`
- Puerto leído desde variable de entorno `PORT` (Render lo inyecta automáticamente)
- Health check mejorado: verifica conexión real a la BD y retorna `503` si falla

---

## 📁 Archivos que NO cambiaron

Estos archivos se mantienen igual porque ya funcionaban bien:

- `middleware/auth_middleware.py` — verificación de JWT
- `middleware/audit_middleware.py` — logs de actividad
- `routes/api_routes.py` — endpoints de la API
- `routes/reports_routes.py` — reportes de actividad
- `security/access_manager.py` — bloqueos de seguridad
- `security/anomaly_detector.py` — detección de anomalías
- `frontend/css/styles.css` — estilos
- `frontend/js/*.js` — scripts del frontend

---

## 🗂️ Estructura del proyecto

```
api_portal_v2/
├── .env.example          ← Variables de entorno (copia a .env)
├── .gitignore            ← Incluye .env, __pycache__, venv
├── render.yaml           ← Config de Render (NUEVO)
├── DEPLOY_GUIDE.md       ← Guía de despliegue (NUEVO)
├── CAMBIOS.md            ← Este archivo
├── backend/
│   ├── app.py            ← Mejorado: port dinámico, health check real
│   ├── config.py         ← Mejorado: sin defaults hardcodeados
│   ├── requirements.txt  ← Cambiado: pymssql → psycopg2-binary
│   ├── models/
│   │   └── database.py   ← Reescrito: psycopg2 + SSL para Supabase
│   ├── routes/
│   │   ├── auth_routes.py   ← Adaptado: SQL PostgreSQL (sin stored procs)
│   │   └── portal_routes.py ← Sin cambios
│   └── ... (resto sin cambios)
├── frontend/
│   ├── dashboard.html    ← Mejorado: token truncado en pantalla
│   └── ... (resto sin cambios)
└── database/
    └── schema.sql        ← Reescrito: PostgreSQL + RLS de Supabase
```
