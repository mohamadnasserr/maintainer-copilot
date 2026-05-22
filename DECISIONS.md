# Decisions — Maintainers Copilot

## 1. Repository Choice

We chose the official pandas repository:

```text
pandas-dev/pandas

Reason:

pandas is a large real-world open-source project.
It has many closed issues, labels, bug reports, documentation questions, and maintainer discussions.
It is a good fit for a maintainer assistant because questions often involve APIs, dtype behavior, groupby behavior, performance, and documentation.
2. Scope Decision

The project focuses on the non-classical-ML parts of the Week 7 assignment:

Advanced RAG
Chatbot
Memory
Streamlit admin surface
React embeddable widget
NER and summarization tools
RAG evaluation
Safe logging and redaction

Classical ML classification is intentionally not the focus for the current implementation.

3. Corpus and Preprocessing

We fetch closed pandas issues using GitHub’s API.

Raw issues are stored in:

data/raw/pandas_closed_issues.json

Processed chunks are stored in:

data/processed/pandas_chunks.jsonl

Preprocessing decisions:

Skip pull requests because the RAG corpus focuses on issue triage and maintainer issue context.
Clean repeated whitespace and newlines.
Keep issue title and body together.
Preserve metadata such as:
issue number
source URL
labels
created/updated/closed timestamps
author
comment count
4. Chunking Strategy

We use markdown-aware paragraph chunking instead of naive fixed-size slicing.

Default values:

max_chars = 2200
overlap_chars = 250

Reason:

GitHub issues are usually structured in paragraphs, code blocks, and sections.
Paragraph-aware chunking keeps related context together.
Overlap prevents losing important information at chunk boundaries.
5. Embedding Choice

Current implementation uses deterministic CPU-only development embeddings.

Reason:

Fast local development.
No GPU/CUDA dependency.
Avoids heavy builds.
Keeps the system fully runnable on a normal laptop.

Limitation:

These embeddings are not as semantically strong as OpenAI, sentence-transformers, or other production embedding models.

Future production choice:

Replace dev embeddings with a real embedding provider or CPU-friendly embedding model.
Re-run ingestion and RAG evaluation.
Compare retrieval metrics before and after the change.
6. Vector Store

We use Postgres with pgvector.

Reason:

The assignment allows pgvector or Qdrant.
Postgres is already part of the project stack.
pgvector allows us to store document chunks and embeddings in the same database.
Metadata and vector search can live together.

Main table:

document_chunks
7. Retrieval Strategy

The RAG retriever uses hybrid ranking:

pgvector cosine similarity
PostgreSQL full-text keyword score
exact technical-term boost

Reason:

Maintainer questions often contain exact API names such as:
groupby
value_counts
numeric_only
read_csv
DataFrame
Pure vector search can miss exact code/API terms.
Keyword and exact-match scoring improve retrieval for technical issue text.

Current scoring strategy:

0.55 * vector_similarity
+ 0.25 * keyword_score
+ 0.20 * exact_match_score

This improved the query:

groupby value_counts performance

so that issue #51750 PERF: groupby.value_counts ranked first.

8. RAG Evaluation

We created a small RAG golden set in:

evals/rag_golden.jsonl

The eval script:

evals/run_rag_eval.py

measures:

hit@1
hit@3
hit@5
mrr@10

Current initial results:

hit@1  = 0.60
hit@3  = 0.80
hit@5  = 0.80
mrr@10 = 0.72

Thresholds are stored in:

evals/eval_thresholds.yaml

The eval fails if retrieval drops below the committed thresholds.

9. Chatbot Tool Routing

The chatbot currently uses deterministic tool routing.

Routing rules:

remember that ... → write long-term memory
remember this: ... → write long-term memory
save this: ... → write long-term memory
store this: ... → write long-term memory
extract entities from: → NER tool
summarize this: → summarization tool
otherwise → RAG

Reason:

This is lightweight and easy to explain.
It avoids introducing a heavy tool-calling LLM before the rest of the system is stable.
The service boundary is still correct: the chat service chooses a tool, then calls the relevant service/infra component.

Future improvement:

Replace deterministic routing with a single tool-calling LLM.
10. NER Tool

The NER tool is CPU-only and regex-based.

It extracts code-shaped entities such as:

pandas APIs
method calls
exceptions/warnings
versions
GitHub issue references
file paths

Reason:

Maintainer issue text often contains technical entities, not person/location entities.
Regex is fast, deterministic, and CPU-only.
Avoids GPU/CUDA build time.

Endpoint:

POST /nlp/entities
11. Summarization Tool

The summarizer is CPU-only and extractive.

It scores sentences using word frequency and gives a small bonus to sentences containing pandas/API terms.

Reason:

Fast to run locally.
No GPU dependency.
Good enough for issue-thread summarization baseline.

Endpoint:

POST /nlp/summarize

Future improvement:

Replace or supplement with LLM-driven summarization.
12. Short-Term Memory

Short-term memory uses Redis.

File:

app/infra/redis_memory.py

TTL:

1 hour

Reason:

Recent chat state should be fast and temporary.
Redis is already part of the required stack.
TTL prevents old conversations from staying forever.
13. Long-Term Memory

Long-term memory uses Postgres.

Table:

long_term_memories

Memory type:

semantic

Reason:

The current useful memory is durable maintainer preference/fact memory.
Example: “dtype bug reports should include pandas version and reproduction steps.”

Writes are explicit only. The chatbot does not automatically save memories.

14. Audit Logs

Every long-term memory write creates an audit row.

Table:

audit_logs

Reason:

Memory writes are sensitive.
We need to know actor, action, target, timestamp, and metadata.
This supports accountability and debugging.
15. Frontend Decision

We use two frontends:

Streamlit

Purpose:

Internal admin/chat app
Fast iteration
Chat tab
Memory inspector
Widget config placeholder
React widget

Purpose:

Production-shaped embeddable widget
Smaller and more appropriate than embedding Streamlit
Supports chat panel, input, enter-to-send, loading state, and chat history

Both call the same FastAPI backend.

16. Secret Handling

The app checks Vault at startup.

Reason:

The assignment requires the app to refuse boot if Vault is unreachable.
In local Windows development, the app uses:
VAULT_ADDR=http://localhost:8200

Current limitation:

Secrets are not fully resolved from Vault yet.
This is a next hardening step.
17. Safe Logging and Redaction

We implemented:

recursive redaction
safe logging filter
request IDs
trace IDs
redaction tests

Redacted patterns include:

GitHub tokens
OpenAI-style keys
JWT-like tokens
passwords
authorization headers
generic API keys/secrets

Test file:

tests/test_redaction.py
18. CPU-Only Build Decision

We intentionally avoided GPU/CUDA dependencies.

Not used:

CUDA
tensorflow-gpu
torch CUDA builds
faiss-gpu
nvidia packages

Reason:

Deadline is tight.
Build time must stay short.
Project should run on a normal laptop.
Current RAG, NER, summarization, and memory features do not require GPU.
