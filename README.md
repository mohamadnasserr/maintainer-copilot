# Maintainers Copilot — AIE Week 7

## Project Summary

Maintainers Copilot is an AI assistant for maintainers of the pandas open-source repository.

It helps a maintainer:

- ask questions about resolved pandas issues
- retrieve relevant maintainer context using RAG
- inspect original GitHub issue sources
- extract code-shaped entities from issue text
- summarize issue text
- keep short-term conversation memory
- explicitly save long-term semantic memory
- use the assistant from both an internal Streamlit app and an embeddable React widget

The selected repository is:

```text
pandas-dev/pandas


The project is built around a production-shaped architecture with FastAPI, Streamlit, React, Postgres + pgvector, Redis, Vault, RAG evaluation, redacted logging, and memory audit logs.

Assignment Alignment

This implementation focuses on the main non-classical-ML parts of the Week 7 Maintainers Copilot assignment:

advanced RAG
chatbot with tools
Redis short-term memory
Postgres long-term memory
NER and summarization tools
Streamlit internal app
React embeddable widget
RAG evaluation with thresholds
safe logging and redaction tests
Vault startup check

Classical ML classification is intentionally not the focus of this implementation.

### Architecture Overview :


Streamlit app / React widget
        ↓
FastAPI backend
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
Postgres:
   - document_chunks with pgvector embeddings
   - long_term_memories
   - audit_logs
        ↓
Answer returned to frontend

Main Components

FastAPI Backend

Main app:
app/main.py

Important routes:


POST /chat
GET  /chat/memory/{conversation_id}
POST /nlp/entities
POST /nlp/summarize
GET  /docs

RAG Pipeline

Main file:

app/infra/rag.py

RAG data flow:

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
Postgres document_chunks table
        ↓
app/infra/rag.py retrieval

The retriever uses:

pgvector cosine similarity
PostgreSQL full-text keyword score
exact technical-term boost

This is useful for pandas API terms such as:

groupby
value_counts
numeric_only
read_csv
DataFrame
Chat Service

Main file:

app/services/chat_service.py

The chat service routes messages by intent:

User message pattern Tool used
remember that ... long-term memory write
remember this: ... long-term memory write
save this: ... long-term memory write
store this: ... long-term memory write
extract entities from: NER
summarize this: summarizer
normal question RAG
Short-Term Memory

Main file:

app/infra/redis_memory.py

Storage:

Redis

TTL:

1 hour

Example keys:

conversation:streamlit-local-pandas:messages
conversation:widget-local-pandas:messages
Long-Term Memory

Main file:

app/repositories/memory_repository.py

Tables:

long_term_memories
audit_logs

Memory type used:

semantic

Long-term memory writes are explicit only. The chatbot does not automatically save arbitrary conversation content.

Every long-term memory write creates an audit row.

NER and Summarization

Main service file:

app/services/nlp_tools.py

API file:

app/api/nlp.py

Endpoints:

POST /nlp/entities
POST /nlp/summarize

The current implementation is CPU-only:

no CUDA
no GPU packages
no heavy deep learning build

NER extracts code-shaped entities such as:

pd.DataFrame
np.mean
FutureWarning
2.1
#50538

Summarization uses lightweight extractive sentence scoring.

Streamlit App

Main file:

frontend/streamlit_app/Home.py

Tabs:

Chat
Widget Config
Memory

The Streamlit chat calls:

POST /chat

The Memory tab calls:

GET /chat/memory/{conversation_id}
React Widget

Main files:

frontend/widget/src/main.tsx
frontend/widget/src/styles.css

The widget supports:

chat panel
input box
enter-to-send
multiple messages
loading state
chat history
backend /chat calls
stable widget conversation ID
RAG Evaluation

Evaluation files:

evals/rag_golden.jsonl
evals/run_rag_eval.py
evals/eval_thresholds.yaml
eval_report.json

Current metrics from the 25-example golden set:

hit@1  = 0.92
hit@3  = 0.96
hit@5  = 0.96
mrr@10 = 0.944

Current thresholds:

rag:
  min_hit_at_1: 0.50
  min_hit_at_3: 0.70
  min_hit_at_5: 0.70
  min_mrr_at_10: 0.60

Run eval:

python evals/run_rag_eval.py

Expected result:

RAG evaluation passed thresholds
Security and Logging

Implemented:

Vault startup check
recursive redaction
safe logging filter
request ID middleware
trace ID middleware
redaction tests

Important files:

app/infra/vault.py
app/infra/redaction.py
app/infra/logging.py
app/api/middleware.py
tests/test_redaction.py

Run redaction tests:

python -m pytest tests/test_redaction.py -q

Expected:

5 passed
CPU-Only Build Decision

This project intentionally avoids GPU/CUDA dependencies.

Not used:

torch CUDA
tensorflow-gpu
faiss-gpu
nvidia-* packages

Reason:

faster setup
lower build risk
runs on normal laptop hardware
suitable for the deadline

The current RAG, NER, summarization, memory, and evaluation features are CPU-only.

Local Setup
1. Install Python dependencies
python -m pip install fastapi uvicorn httpx psycopg[binary] numpy redis pyyaml pytest streamlit
2. Start infrastructure
docker compose up -d db vault redis

Check:

docker compose ps

Expected:

db      healthy/running
vault   running
redis   healthy/running
3. Start FastAPI locally on Windows

Use localhost URLs when running Python directly from Windows:

set VAULT_ADDR=http://localhost:8200
set REDIS_URL=redis://localhost:6379/0
set DATABASE_URL=postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers
python -m uvicorn app.main:app --port 8000

Open docs:

http://127.0.0.1:8000/docs
Data Preparation
1. Fetch closed pandas issues
python scripts/fetch_pandas_corpus.py --limit 100

Output:

data/raw/pandas_closed_issues.json
2. Build chunks
python scripts/build_pandas_chunks.py

Output:

data/processed/pandas_chunks.jsonl
3. Ingest into Postgres/pgvector
python scripts/ingest_corpus.py --dev-embeddings --database-url postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers

Expected:

Done. Ingested 53 chunks into document_chunks.
4. Setup memory tables
python scripts/setup_memory_tables.py

Expected:

Memory and audit tables are ready.
Running the Frontends
Streamlit
streamlit run frontend/streamlit_app/Home.py

Test prompt:

groupby value_counts performance

Memory prompt:

remember that dtype bug reports should include pandas version and reproduction steps

Then open the Memory tab and load:

streamlit-local-pandas
React Widget
cd frontend\widget
npm install
npm run dev

Open:

http://localhost:5173/

Test prompt:

groupby value_counts performance
Useful Test Commands
Test RAG directly
python -c "from app.infra.rag import RagPipeline; rag=RagPipeline(); answer,chunks=rag.answer('groupby value_counts performance'); print(answer); print('chunks:', len(chunks)); print(chunks[0].title if chunks else 'no chunks')"

Expected top result:

PERF: groupby.value_counts
Test /chat
python -c "import httpx, json; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':'groupby value_counts performance','conversation_id':'readme-test'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
Test explicit memory
python -c "import httpx, json; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':'remember that performance issues should include benchmark context','conversation_id':'readme-memory'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
Test memory read
python -c "import httpx, json; r=httpx.get('http://127.0.0.1:8000/chat/memory/readme-memory', timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
Test NER routing through chat
python -c "import httpx, json; msg='extract entities from: pd.DataFrame.groupby raises FutureWarning in pandas 2.1. See issue #50538. numeric_only fails with np.mean.'; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':msg,'conversation_id':'readme-tools'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
Test summarizer routing through chat
python -c "import httpx, json; msg='summarize this: The issue reports that groupby.value_counts uses public APIs internally. This may create unnecessary overhead. The maintainer wants to investigate whether pandas internals can improve performance. Benchmark context should be included before making a decision.'; r=httpx.post('http://127.0.0.1:8000/chat', json={'message':msg,'conversation_id':'readme-tools'}, timeout=30); print(r.status_code); print(json.dumps(r.json(), indent=2)[:2000])"
