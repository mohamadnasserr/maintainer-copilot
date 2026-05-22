# Architecture — Maintainers Copilot

## Project Goal

Maintainers Copilot is an AI assistant for maintainers of the pandas open-source repository. It helps answer questions about resolved pandas issues, extracts code-shaped entities, summarizes issue text, and stores short-term and long-term conversation memory.

The project focuses on a production-shaped architecture:

- FastAPI backend
- Streamlit internal admin/chat app
- React embeddable widget
- Postgres with pgvector
- Redis short-term memory
- Vault startup check
- RAG evaluation with thresholds
- Redacted logging and request IDs

## Main Runtime Flow

```text
Streamlit app / React widget
        ↓
FastAPI /chat endpoint
        ↓
ChatService
        ↓
Tool routing:
   - RAG over pandas issues
   - NER entity extraction
   - Summarization
   - Explicit write_memory
        ↓
Redis short-term memory
        ↓
Postgres long-term memory / pgvector / audit logs
        ↓
Answer returned to frontend
Backend Layers
app/api/

HTTP boundary only.

Important files:

chat.py — /chat endpoint and /chat/memory/{conversation_id}
nlp.py — /nlp/entities and /nlp/summarize
middleware.py — request ID and trace ID middleware
health.py — health endpoint
widget.py — widget configuration / loader routes

API routes do not directly own business logic. They validate requests and call services.

app/services/

Business logic layer.

Important files:

chat_service.py — chatbot orchestration and tool routing
nlp_tools.py — CPU-only NER and summarization logic

ChatService decides whether the user wants RAG, NER, summarization, or an explicit memory write.

app/infra/

Infrastructure adapters.

Important files:

rag.py — Postgres/pgvector RAG retrieval
redis_memory.py — Redis short-term memory
vault.py — Vault startup check
redaction.py — secret redaction
logging.py — safe logging setup
app/repositories/

Database access layer.

Important files:

memory_repository.py — writes long-term memory and audit logs
schema.sql — base schema from scaffold

Repositories own SQL and do not return HTTP errors.

RAG Architecture

The RAG corpus uses closed issues from the official pandas repository:

https://github.com/pandas-dev/pandas

Pipeline:

scripts/fetch_pandas_corpus.py
        ↓
data/raw/pandas_closed_issues.json
        ↓
scripts/build_pandas_chunks.py
        ↓
data/processed/pandas_chunks.jsonl
        ↓
scripts/ingest_corpus.py
        ↓
Postgres document_chunks table with pgvector embeddings
        ↓
app/infra/rag.py

Retrieval uses hybrid ranking:

pgvector cosine similarity
PostgreSQL full-text keyword score
exact technical-term boost for pandas API names such as groupby, value_counts, numeric_only, and read_csv

This improves retrieval for code-heavy maintainer questions.

Memory Architecture
Short-term memory

Implemented with Redis.

File: app/infra/redis_memory.py
TTL: 1 hour
Stores recent conversation messages
Used by both Streamlit and React widget

Example keys:

conversation:streamlit-local-pandas:messages
conversation:widget-local-pandas:messages
Long-term memory

Implemented with Postgres.

Table: long_term_memories
File: app/repositories/memory_repository.py
Memory type: semantic
Writes only happen explicitly when the user says:
remember that ...
remember this: ...
save this: ...
store this: ...

Every long-term memory write creates an audit row in audit_logs.

Frontends
Streamlit

File:

frontend/streamlit_app/Home.py

Purpose:

Internal maintainer/admin app
Chat tab
Widget config placeholder
Memory inspector
React widget

Files:

frontend/widget/src/main.tsx
frontend/widget/src/styles.css

Purpose:

Embeddable production-style chat widget
Calls /chat
Maintains widget conversation ID
Supports enter-to-send, multiple messages, loading state, and chat history
Evaluation

RAG evaluation files:

evals/rag_golden.jsonl
evals/run_rag_eval.py
evals/eval_thresholds.yaml
eval_report.json

Current metrics from the initial 5-example golden set:

hit@1  = 0.60
hit@3  = 0.80
hit@5  = 0.80
mrr@10 = 0.72

The eval script fails if metrics go below committed thresholds.

Security and Observability

Implemented:

Vault startup check
Redaction layer
Redacted logging
Redaction tests
Request ID and trace ID middleware

Current limitation:

Full tracing backend is not yet integrated.
