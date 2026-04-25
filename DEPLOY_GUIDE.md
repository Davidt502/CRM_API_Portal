# 🚀 Guía de Despliegue — CRM API Portal v2
## Supabase (Base de datos) + Render (Servidor)

---

## PARTE 1 — Configurar Supabase

### Paso 1: Crear cuenta y proyecto
1. Ve a **https://supabase.com** y crea una cuenta gratuita
2. Haz clic en **"New Project"**
3. Elige un nombre (ej: `crm-api-portal`) y una contraseña segura para la BD
4. Selecciona la región más cercana (ej: `South America - São Paulo`)
5. Espera ~2 minutos a que el proyecto se cree

### Paso 2: Ejecutar el schema
1. En el dashboard de Supabase, ve a **SQL Editor** (ícono de terminal en el menú izquierdo)
2. Haz clic en **"New query"**
3. Abre el archivo `database/schema.sql` de este proyecto
4. Copia y pega **todo** el contenido en el editor
5. Haz clic en **"Run"** — deberías ver: `Success. No rows returned`

### Paso 3: Obtener las credenciales
1. Ve a **Settings** → **Database** (en el menú izquierdo)
2. Baja hasta la sección **"Connection parameters"**
3. Anota estos valores (los necesitarás en Render):
   - **Host**: `db.XXXXXXXX.supabase.co`
   - **Database name**: `postgres`
   - **User**: `postgres`
   - **Password**: la que pusiste al crear el proyecto
   - **Port**: `5432`

### Paso 4: Crear usuario admin (opcional)
1. En **SQL Editor**, ejecuta este comando (cambia los valores):
```sql
INSERT INTO portal_usuarios (nombre_completo, email, password_hash, rol, acepto_terminos)
VALUES (
  'Admin Principal',
  'admin@tuempresa.com',
  '$2b$12$REEMPLAZA_CON_HASH_REAL',
  'admin',
  TRUE
);
```
> Para generar el hash de tu contraseña, ejecuta en tu terminal:
> ```bash
> python -c "import bcrypt; print(bcrypt.hashpw(b'TuPassword123!', bcrypt.gensalt(12)).decode())"
> ```

---

## PARTE 2 — Desplegar en Render

### Paso 1: Subir código a GitHub
1. Crea un repositorio en **https://github.com** (puede ser privado)
2. Sube todo el proyecto:
```bash
git init
git add .
git commit -m "CRM API Portal v2"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```
> ⚠️ Asegúrate de que `.env` esté en `.gitignore` antes de hacer push

### Paso 2: Crear servicio en Render
1. Ve a **https://render.com** y crea una cuenta gratuita
2. Haz clic en **"New +"** → **"Web Service"**
3. Conecta tu cuenta de GitHub y selecciona el repositorio
4. Configura el servicio:
   - **Name**: `crm-api-portal`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120`
   - **Plan**: Free

### Paso 3: Configurar variables de entorno en Render
1. En la página del servicio, ve a **"Environment"**
2. Haz clic en **"Add Environment Variable"** y agrega **UNA POR UNA**:

| Variable               | Valor                                      |
|------------------------|--------------------------------------------|
| `FLASK_ENV`            | `production`                               |
| `FLASK_DEBUG`          | `false`                                    |
| `SECRET_KEY`           | *(genera con el comando de abajo)*         |
| `SUPABASE_DB_HOST`     | `db.XXXXXXXX.supabase.co`                  |
| `SUPABASE_DB_PORT`     | `5432`                                     |
| `SUPABASE_DB_NAME`     | `postgres`                                 |
| `SUPABASE_DB_USER`     | `postgres`                                 |
| `SUPABASE_DB_PASSWORD` | *(tu password de Supabase)*                |
| `CORS_ORIGINS`         | `https://tu-app.onrender.com`              |
| `JWT_EXPIRY_HOURS`     | `8`                                        |
| `LOGIN_MAX_ATTEMPTS`   | `5`                                        |

> Para generar SECRET_KEY:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

3. Haz clic en **"Save Changes"**

### Paso 4: Desplegar
1. Haz clic en **"Manual Deploy"** → **"Deploy latest commit"**
2. Observa los logs en tiempo real
3. Cuando veas `Gunicorn booted successfully`, el servicio está listo
4. Tu URL será: `https://crm-api-portal.onrender.com`

### Paso 5: Verificar
Visita estas URLs para confirmar que todo funciona:
- `https://tu-app.onrender.com/api/health` → debe devolver `{"status": "ok", "database": "connected"}`
- `https://tu-app.onrender.com/portal/login` → debe mostrar la página de login

---

## PARTE 3 — Actualizar el código

Cada vez que hagas cambios y hagas `git push`, Render redesplegará automáticamente.

```bash
# Flujo de trabajo normal
git add .
git commit -m "descripción del cambio"
git push
# Render detecta el push y redespliega automáticamente
```

---

## ⚠️ Notas importantes de seguridad

- **NUNCA** subas el archivo `.env` a GitHub
- **NUNCA** pongas contraseñas directamente en el código
- Todos los secretos van **únicamente** en las variables de entorno de Render
- El archivo `.gitignore` ya está configurado para ignorar `.env`

---

## 🆘 Solución de problemas comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `could not connect to server` | Credenciales de Supabase incorrectas | Verifica las variables de entorno en Render |
| `SECRET_KEY no configurada` | Falta la variable SECRET_KEY | Agrégala en Environment de Render |
| `ModuleNotFoundError: psycopg2` | No se instalaron dependencias | Verifica el Build Command en Render |
| `CORS error` | CORS_ORIGINS no incluye tu dominio | Actualiza CORS_ORIGINS con la URL de Render |
| `502 Bad Gateway` | La app tardó en iniciar (plan free) | Espera 30-60 seg, Render "duerme" en plan free |
