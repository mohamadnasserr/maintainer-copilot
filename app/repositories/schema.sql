CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS widget_configs (
  widget_id TEXT PRIMARY KEY,
  allowed_origins JSONB NOT NULL,
  theme JSONB NOT NULL,
  greeting TEXT NOT NULL,
  enabled_tools JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  source_url TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  metadata JSONB NOT NULL,
  embedding vector(1536)
);

