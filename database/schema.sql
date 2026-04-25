-- ============================================================
--  schema.sql — CRM API Portal v2 (PostgreSQL / Supabase)
--  Ejecuta este archivo en Supabase:
--    Dashboard → SQL Editor → pega el contenido → Run
-- ============================================================

-- ─── Tabla 1: Usuarios del portal ────────────────────────────
CREATE TABLE IF NOT EXISTS portal_usuarios (
    id_usuario            SERIAL PRIMARY KEY,
    nombre_completo       VARCHAR(150)   NOT NULL,
    email                 VARCHAR(150)   NOT NULL UNIQUE,
    password_hash         VARCHAR(255)   NOT NULL,
    rol                   VARCHAR(20)    NOT NULL DEFAULT 'usuario',
    estado                VARCHAR(20)    NOT NULL DEFAULT 'Activo',
    acepto_terminos       BOOLEAN        NOT NULL DEFAULT FALSE,
    fecha_registro        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    ultimo_acceso         TIMESTAMPTZ,
    intentos_fallidos     INT            NOT NULL DEFAULT 0,
    ultima_ip             VARCHAR(45),
    ultimo_user_agent     VARCHAR(500),
    es_activo_api         BOOLEAN        NOT NULL DEFAULT TRUE,
    fecha_ultima_mod      TIMESTAMPTZ,
    modificado_por        VARCHAR(150),
    CONSTRAINT chk_rol    CHECK (rol IN ('usuario', 'admin')),
    CONSTRAINT chk_estado CHECK (estado IN ('Activo', 'Inactivo', 'Bloqueado'))
);

-- ─── Tabla 2: Logs de actividad ──────────────────────────────
CREATE TABLE IF NOT EXISTS api_activity_log (
    id_log            BIGSERIAL PRIMARY KEY,
    id_usuario        INT            REFERENCES portal_usuarios(id_usuario) ON DELETE SET NULL,
    nombre_usuario    VARCHAR(150),
    email_usuario     VARCHAR(150),
    ip_address        VARCHAR(45)    NOT NULL,
    user_agent        VARCHAR(500),
    metodo_http       VARCHAR(10)    NOT NULL,
    endpoint          VARCHAR(500)   NOT NULL,
    query_params      VARCHAR(1000),
    status_code       INT,
    duracion_ms       INT,
    fecha_acceso      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    es_anomalia       BOOLEAN        NOT NULL DEFAULT FALSE,
    tipo_anomalia     VARCHAR(100),
    detalles_anomalia TEXT
);

-- ─── Tabla 3: Bloqueos de seguridad ──────────────────────────
CREATE TABLE IF NOT EXISTS security_blocks (
    id_bloqueo        SERIAL PRIMARY KEY,
    id_usuario        INT            NOT NULL REFERENCES portal_usuarios(id_usuario) ON DELETE CASCADE,
    email             VARCHAR(150)   NOT NULL,
    razon_bloqueo     VARCHAR(100)   NOT NULL,
    tipo_anomalia     VARCHAR(100),
    detalles          TEXT,
    fecha_bloqueo     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    fecha_expiracion  TIMESTAMPTZ,
    activo            BOOLEAN        NOT NULL DEFAULT TRUE,
    desbloqueado_por  VARCHAR(150),
    fecha_desbloqueo  TIMESTAMPTZ
);

-- ─── Índices para performance ─────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_log_usuario    ON api_activity_log(id_usuario);
CREATE INDEX IF NOT EXISTS idx_log_fecha      ON api_activity_log(fecha_acceso DESC);
CREATE INDEX IF NOT EXISTS idx_log_endpoint   ON api_activity_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_log_ip         ON api_activity_log(ip_address);
CREATE INDEX IF NOT EXISTS idx_blocks_usuario ON security_blocks(id_usuario);
CREATE INDEX IF NOT EXISTS idx_blocks_activo  ON security_blocks(activo);

-- ─── Función: registrar usuario ──────────────────────────────
CREATE OR REPLACE FUNCTION sp_portal_registrar_usuario(
    p_nombre    VARCHAR,
    p_email     VARCHAR,
    p_hash      VARCHAR,
    p_terminos  BOOLEAN
) RETURNS TABLE(codigo INT, mensaje TEXT) AS $$
BEGIN
    -- Verificar si el email ya existe
    IF EXISTS (SELECT 1 FROM portal_usuarios WHERE email = LOWER(p_email)) THEN
        RETURN QUERY SELECT 50001, 'El correo electrónico ya está registrado.'::TEXT;
        RETURN;
    END IF;

    INSERT INTO portal_usuarios (nombre_completo, email, password_hash, acepto_terminos)
    VALUES (p_nombre, LOWER(p_email), p_hash, p_terminos);

    RETURN QUERY SELECT 0, 'Usuario registrado exitosamente.'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- ─── Row Level Security (RLS) — Supabase ─────────────────────
-- Habilitar RLS para que usuarios solo vean sus propios datos
ALTER TABLE portal_usuarios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_activity_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_blocks   ENABLE ROW LEVEL SECURITY;

-- Política: el backend usa el rol 'postgres' (service role) y tiene acceso total
-- Los usuarios directos de Supabase solo verían sus propios datos

-- ─── Usuario admin inicial (cambia el email y password_hash) ─
-- Para generar un hash: python -c "import bcrypt; print(bcrypt.hashpw(b'TuPassword123!', bcrypt.gensalt(12)).decode())"
-- INSERT INTO portal_usuarios (nombre_completo, email, password_hash, rol, acepto_terminos)
-- VALUES ('Admin', 'admin@empresa.com', '$2b$12$HASH_AQUI', 'admin', TRUE);
