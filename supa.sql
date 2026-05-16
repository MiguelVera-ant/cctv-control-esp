-- ============================================================
-- Habilitar extensión pgvector para búsqueda por similitud
-- ============================================================

-- Extensión para vectores
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Tabla principal de personas registradas
-- ============================================================
CREATE TABLE IF NOT EXISTS persons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT,                              -- Nombre
    -- metadata        JSONB DEFAULT '{}',               -- Datos extra
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Tabla de embeddings faciales (1 persona puede tener N rostros)
-- ============================================================
CREATE TABLE IF NOT EXISTS face_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID REFERENCES persons(id) ON DELETE CASCADE,
    embedding       vector(512),                      -- Facenet512 = 512 dims
    image_base64    TEXT,                             -- Imagen original
    confidence      FLOAT DEFAULT 1.0,               -- Calidad del embedding
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW
CREATE INDEX IF NOT EXISTS face_embeddings_hnsw_idx
    ON face_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- Tabla de log de accesos / detecciones
-- ============================================================
CREATE TABLE IF NOT EXISTS detection_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID REFERENCES persons(id) ON DELETE SET NULL,
    is_known        BOOLEAN NOT NULL,
    similarity      FLOAT,                            -- Distancia coseno (0=idéntico, 1=diferente)
    mqtt_topic      TEXT,
    device_id       TEXT,
    image_base64    TEXT,
    matched_face_id UUID REFERENCES face_embeddings(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Función para buscar rostro más cercano por similitud coseno
-- Retorna el face_embedding más similar dentro del umbral
-- ============================================================
CREATE OR REPLACE FUNCTION find_closest_face(
    query_embedding vector(512),
    similarity_threshold FLOAT DEFAULT 0.4   -- 0.4 = umbral
)
RETURNS TABLE (
    face_id         UUID,
    person_id       UUID,
    person_name     TEXT,
    distance        FLOAT,
    metadata        JSONB
)
LANGUAGE sql STABLE AS $$
    SELECT
        fe.id           AS face_id,
        fe.person_id,
        p.name          AS person_name,
        (fe.embedding <=> query_embedding) AS distance,
        p.metadata
    FROM face_embeddings fe
    JOIN persons p ON p.id = fe.person_id
    WHERE (fe.embedding <=> query_embedding) < similarity_threshold
    ORDER BY fe.embedding <=> query_embedding
    LIMIT 1;
$$;

-- ============================================================
-- Trigger para actualizar updated_at automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER persons_updated_at
    BEFORE UPDATE ON persons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- Row Level Security (RLS)
-- ============================================================
ALTER TABLE persons         ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE detection_logs  ENABLE ROW LEVEL SECURITY;

-- Política: solo service_role puede escribir (n8n usa service_role key)
CREATE POLICY "Service role full access" ON persons
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access" ON face_embeddings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access" ON detection_logs
    FOR ALL TO service_role USING (true) WITH CHECK (true);