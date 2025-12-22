CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY,
    audio_path TEXT NOT NULL,
    duration_seconds FLOAT,
    status TEXT NOT NULL CHECK (
        status IN (
            'TRANSCRIPTION_QUEUE',
            'EVALUATION_QUEUE',
            'EVALUATED',
            'FAILED'
        )
    ),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    model_name TEXT,
    language TEXT,
    transcript_text TEXT,
    segments JSONB,
    timestamped_text TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    evaluator_type TEXT,
    evaluator_version TEXT,
    overall_score INT CHECK (overall_score BETWEEN 1 AND 5),
    category_scores JSONB,
    strengths JSONB,
    improvements JSONB,
    raw_output JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transcripts_call_id
ON transcripts(call_id);

CREATE INDEX IF NOT EXISTS idx_evaluations_call_id
ON evaluations(call_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calls_set_updated_at
BEFORE UPDATE ON calls
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
