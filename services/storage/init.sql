-- Inicialización de la base de datos para Yahoo Answers

-- Crear extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla principal de preguntas y respuestas originales de Yahoo
CREATE TABLE IF NOT EXISTS yahoo_questions (
    id SERIAL PRIMARY KEY,
    yahoo_id VARCHAR(50) UNIQUE,
    class_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    best_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para almacenar respuestas del LLM y métricas
CREATE TABLE IF NOT EXISTS llm_responses (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES yahoo_questions(id),
    llm_response TEXT NOT NULL,
    quality_score DECIMAL(5,4), -- Score de 0.0000 a 1.0000
    response_time_ms INTEGER,
    llm_model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para contabilizar accesos y cache hits
CREATE TABLE IF NOT EXISTS question_stats (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES yahoo_questions(id) UNIQUE,
    access_count INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para métricas del sistema
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4),
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_yahoo_questions_class ON yahoo_questions(class_id);
CREATE INDEX IF NOT EXISTS idx_yahoo_questions_created ON yahoo_questions(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_responses_question ON llm_responses(question_id);
CREATE INDEX IF NOT EXISTS idx_llm_responses_created ON llm_responses(created_at);
CREATE INDEX IF NOT EXISTS idx_question_stats_question ON question_stats(question_id);
CREATE INDEX IF NOT EXISTS idx_question_stats_accessed ON question_stats(last_accessed);

-- Función para actualizar timestamp de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at automáticamente
CREATE TRIGGER update_yahoo_questions_updated_at BEFORE UPDATE ON yahoo_questions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar datos de ejemplo si la tabla está vacía
INSERT INTO yahoo_questions (yahoo_id, class_id, title, question, best_answer) 
SELECT 'sample_' || seq, 
       (seq % 10) + 1,
       'Sample Question ' || seq,
       'This is sample question number ' || seq || ' for testing purposes.',
       'This is the sample answer for question ' || seq || '.'
FROM generate_series(1, 100) seq
WHERE NOT EXISTS (SELECT 1 FROM yahoo_questions);

-- Inicializar stats para preguntas de ejemplo
INSERT INTO question_stats (question_id, access_count, cache_hits)
SELECT id, 0, 0 FROM yahoo_questions
WHERE NOT EXISTS (
    SELECT 1 FROM question_stats WHERE question_id = yahoo_questions.id
);

-- Vista para consultas optimizadas
CREATE OR REPLACE VIEW question_with_stats AS
SELECT 
    yq.id,
    yq.yahoo_id,
    yq.class_id,
    yq.title,
    yq.question,
    yq.best_answer,
    yq.created_at,
    COALESCE(qs.access_count, 0) as access_count,
    COALESCE(qs.cache_hits, 0) as cache_hits,
    qs.last_accessed
FROM yahoo_questions yq
LEFT JOIN question_stats qs ON yq.id = qs.question_id;
