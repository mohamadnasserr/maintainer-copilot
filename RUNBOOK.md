# Runbook — Maintainers Copilot

This runbook explains how to run the project locally on Windows.

## 1. Prerequisites

Required:

- Docker Desktop
- Python 3.13+ / 3.14
- Node.js + npm
- VS Code
- Git

Python packages used during local development:

```bash
python -m pip install fastapi uvicorn httpx psycopg[binary] numpy redis pyyaml pytest streamlit

The project is intentionally CPU-only for the current implementation. No CUDA/GPU dependencies are required.

2. Start infrastructure services

From the project root:

docker compose up -d db vault redis

Check services:

docker compose ps

Expected:

db      healthy/running
vault   running
redis   healthy/running

Vault UI should be available at:

http://localhost:8200
3. Local environment variables

When running FastAPI locally from Windows, use localhost-based URLs.

In CMD:

set VAULT_ADDR=http://localhost:8200
set REDIS_URL=redis://localhost:6379/0
set DATABASE_URL=postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers

Then start FastAPI:

python -m uvicorn app.main:app --port 8000

Important:

Do not use Docker service hostnames like db, redis, or vault when running Python directly from Windows. Use localhost.

4. FastAPI docs

Open:

http://127.0.0.1:8000/docs

Important endpoints:

POST /chat
GET  /chat/memory/{conversation_id}
POST /nlp/entities
POST /nlp/summarize
GET  /healthz
5. Fetch pandas issues

The selected repo is:

pandas-dev/pandas

Fetch closed issues:

python scripts/fetch_pandas_corpus.py --limit 100

Output:

data/raw/pandas_closed_issues.json
6. Build RAG chunks
python scripts/build_pandas_chunks.py

Output:

data/processed/pandas_chunks.jsonl

Expected example:

Read 100 issues from data/raw/pandas_closed_issues.json
Wrote 53 chunks to data/processed/pandas_chunks.jsonl
7. Ingest chunks into Postgres/pgvector

Run with CPU-only dev embeddings:

python scripts/ingest_corpus.py --dev-embeddings --database-url postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers

Expected:

Loaded 53 chunks from data/processed/pandas_chunks.jsonl
Ingested 25/53 chunks
Ingested 50/53 chunks
Done. Ingested 53 chunks into document_chunks.

Verify:

docker exec -it maintainerscopilot-db-1 psql -U maintainers -d maintainers -c "SELECT COUNT(*) FROM document_chunks;"
8. Setup memory tables
python scripts/setup_memory_tables.py

Expected:

Memory and audit tables are ready.

Verify tables:

docker exec -it maintainerscopilot-db-1 psql -U maintainers -d maintainers -c "\dt"

Expected tables include:

document_chunks
long_term_memories
audit_logs
9. Test RAG directly
python -c "from app.infra.rag import RagPipeline; rag=RagPipeline(); answer,chunks=rag.answer('groupby value_counts performance'); print(answer); print('chunks:', len(chunks)); print(chunks[0].title if chunks else 'no chunks')"

Expected top result:

PERF: groupby.value_counts
10. Test FastAPI chat endpoint

With FastAPI running:

python -c "import httpx, json; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':'groupby value_counts performance','conversation_id':'runbook-test'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"

Expected:

200

The response should mention:

PERF: groupby.value_counts
11. Test explicit long-term memory
python -c "import httpx, json; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':'remember that dtype bug reports should include pandas version and reproduction steps','conversation_id':'runbook-memory'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"

Expected:

long_term_memory_written: true

Check memory:

python -c "import httpx, json; r=httpx.get('http://127.0.0.1:8000/chat/memory/runbook-memory', timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
12. Test NER tool
python -c "import httpx, json; text='pd.DataFrame.groupby raises FutureWarning in pandas 2.1. See issue #50538. numeric_only fails with np.mean.'; r=httpx.post('http://127.0.0.1:8000/nlp/entities', json={'text': text}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2))"

Expected entities include:

pd.DataFrame
np.mean
FutureWarning
2.1
#50538
13. Test summarization tool
python -c "import httpx, json; text='The issue reports that groupby.value_counts uses public APIs internally. This may create unnecessary overhead. The maintainer wants to investigate whether pandas internals can improve performance. Benchmark context should be included before making a decision.'; r=httpx.post('http://127.0.0.1:8000/nlp/summarize', json={'text': text, 'max_sentences': 2}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2))"

Expected:

200

with a summary.

14. Run Streamlit internal app

In a new terminal:

streamlit run frontend/streamlit_app/Home.py

The Streamlit app includes:

Chat tab
Widget Config tab
Memory tab

Test message:

groupby value_counts performance

Memory test:

remember that dtype bug reports should include pandas version and reproduction steps

Then open the Memory tab and load:

streamlit-local-pandas
15. Run React widget

In a new terminal:

cd frontend\widget
npm install
npm run dev

Open the Vite URL, usually:

http://localhost:5173/

Test message:

groupby value_counts performance

The widget should return a RAG answer and maintain chat history.

16. Run RAG evaluation
python evals/run_rag_eval.py

Expected current metrics:

hit@1  = 0.60
hit@3  = 0.80
hit@5  = 0.80
mrr@10 = 0.72

Expected final line:

RAG evaluation passed thresholds

This writes:

eval_report.json
17. Run redaction tests
python -m pytest tests/test_redaction.py -q

Expected:

5 passed
18. Stop services safely

Stop FastAPI:

CTRL + C

Stop Streamlit:

CTRL + C

Stop React/Vite:

CTRL + C

Stop Docker services:

docker compose down

Do not use:

docker compose down -v

because -v deletes volumes and may remove Postgres data.

19. Resume later

Start infrastructure:

docker compose up -d db vault redis

Start FastAPI:

set VAULT_ADDR=http://localhost:8200
set REDIS_URL=redis://localhost:6379/0
set DATABASE_URL=postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers
python -m uvicorn app.main:app --port 8000

Start Streamlit:

streamlit run frontend/streamlit_app/Home.py

Start widget:

cd frontend\widget
npm run dev
