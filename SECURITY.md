# Security — Maintainers Copilot

## Security Goals

The project handles user messages, GitHub issue text, memory, logs, and generated answers. The main security goals are:

- Do not leak secrets into logs.
- Do not silently save long-term memory.
- Make memory writes auditable.
- Refuse to boot if Vault is unreachable.
- Keep local development CPU-only and simple.
- Add request IDs and trace IDs for debugging.

## Vault

The FastAPI app checks Vault during startup.
If Vault is unreachable, the app refuses to boot.

This matches the production expectation that required secrets should come from Vault rather than being hardcoded.

For local Windows development, use:

set VAULT_ADDR=<http://localhost:8200>

Current limitation:

The app currently checks Vault availability.
Full secret resolution from Vault is not fully implemented yet.
Some local development values still come from environment variables.
Local Environment Variables

When running locally from Windows:

set VAULT_ADDR=<http://localhost:8200>
set REDIS_URL=redis://localhost:6379/0
set DATABASE_URL=postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers
python -m uvicorn app.main:app --port 8000

Important:

localhost is used when Python runs directly on Windows.
Docker service names like db, redis, and vault are only valid inside Docker Compose containers.
Redaction Layer

Redaction is implemented in:

app/infra/redaction.py

The redaction layer recursively handles:

strings
dictionaries
lists

It redacts patterns such as:

GitHub tokens
OpenAI-style keys
JWT-like tokens
passwords
authorization headers
bearer tokens
generic API keys
generic secrets
access keys

Example input:

token=ghp_abcdefghijklmnopqrstuvwxyz123456

Example output:

[REDACTED]
Safe Logging

Safe logging is implemented in:

app/infra/logging.py

The logger:

adds default request_id if missing
adds default trace_id if missing
redacts log messages before output
prevents logging crashes when request_id or trace_id are not provided

Log format:

timestamp level trace_id=<trace_id> request_id=<request_id> message
Request ID and Trace ID

Request/trace middleware is implemented in:

app/api/middleware.py

Each HTTP request gets:

x-request-id
x-trace-id

These are also added to response headers.

This helps connect:

client request
    ↓
API response
    ↓
logs
    ↓
future tracing spans

Current limitation:

A full tracing backend is not yet integrated.
The system currently generates trace IDs and logs them, but does not send spans to a tracing UI.
Redaction Tests

Redaction tests are implemented in:

tests/test_redaction.py

Run:

python -m pytest tests/test_redaction.py -q

Expected:

5 passed

The tests prove that fake secrets do not appear unredacted.

Tested secret patterns include:

GitHub token
OpenAI-style key
password
nested authorization payload
redacted log payload
Memory Safety

The chatbot has two memory types.

Short-term memory

Implemented with Redis:

app/infra/redis_memory.py

Properties:

temporary
TTL-based
expires automatically
used for recent conversation state

Current TTL:

1 hour
Long-term memory

Implemented with Postgres:

long_term_memories

Access code:

app/repositories/memory_repository.py

Long-term memory writes are explicit only.

The chatbot writes long-term memory only when the user says something like:

remember that ...
remember this:
save this:
store this:

The chatbot does not automatically save arbitrary conversation content into long-term memory.

Audit Logs

Every long-term memory write creates an audit row in:

audit_logs

Audit rows record:

actor
action
target
metadata
timestamp

Example action:

write_memory

This gives accountability for persistent memory changes.

CORS

Local CORS allows development origins such as:

<http://localhost:5173>
<http://127.0.0.1:5173>
<http://localhost:8080>
<http://127.0.0.1:8080>
<http://localhost:8000>
<http://127.0.0.1:8000>

Current limitation:

The final production version should enforce CORS and frame allowlisting from widget configuration in Postgres.
Current local CORS is intentionally relaxed enough for local Streamlit/widget testing.
Widget Security

Current widget behavior:

React widget calls the shared FastAPI backend.
Widget uses a stable conversation_id.
Widget config endpoint exists from the scaffold.

Current limitation:

Widget configuration is not fully database-backed yet.
Origin allowlisting and CSP frame-ancestor enforcement are not fully production-ready.
Secrets Policy

Do not commit real secrets.

Avoid committing:

OPENAI_API_KEY
GROQ_API_KEY
DATABASE_PASSWORD
MINIO_SECRET_KEY
JWT_SECRET
VAULT_TOKEN

The assignment expects real secrets to resolve from Vault. Current local development uses environment variables and Vault availability checks.

CPU-Only Security/Build Decision

The current project avoids GPU/CUDA dependencies.

This reduces:

build time
install failures
dependency complexity
local hardware requirements

Not used:

torch CUDA
tensorflow-gpu
faiss-gpu
nvidia-* packages
Current Security Limitations

Known remaining gaps:

Full Vault secret resolution is not implemented.
Full tracing backend is not integrated.
Widget config allowlisting from Postgres is not fully enforced.
MinIO storage of eval reports and snapshots is not fully integrated.
Authentication and role enforcement are still scaffold-level.
Security Demo Checklist

For demo/code review:

Start FastAPI with Vault running.
Show app refuses to boot if Vault is unreachable.
Run redaction tests:
python -m pytest tests/test_redaction.py -q
Send a chat request and show response headers:
x-request-id
x-trace-id
Use long-term memory:
remember that dtype bug reports should include pandas version and reproduction steps
Show the memory appears in Streamlit Memory tab.
Show audit log count increases.
File:

```text
app/infra/vault.py


