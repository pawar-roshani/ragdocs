# RAGDocs API

A production-shaped Retrieval-Augmented Generation (RAG) service: upload PDF or
text documents, they're chunked and embedded into **PostgreSQL + pgvector**,
and you can ask natural-language questions that get answered from their
content — with cited sources.

Built to demonstrate a practical, end-to-end backend engineering stack:
**FastAPI**, **PostgreSQL/pgvector**, **Docker Compose**, **Alembic
migrations**, and a real (if intentionally scoped-down) **RAG pipeline**.

> **Runs with zero API keys.** Embeddings are generated locally with
> `sentence-transformers`, and if no `OPENAI_API_KEY` is set, answers are
> generated with a deterministic extractive fallback instead of an LLM call.
> Set `OPENAI_API_KEY` to upgrade to fluent, synthesized answers — no code
> changes required.

## Why this project

Most "RAG demo" repos either hardcode an OpenAI key requirement (so they
don't actually run for a reviewer) or skip the parts that make a service
production-shaped: migrations, health checks, structured errors, auth,
tests, and CI. This one tries to get those basics right at a scope
appropriate for a focused portfolio project rather than a sprawling one.

## Architecture

```mermaid
flowchart LR
    subgraph Client
        U[HTTP client / curl / Swagger UI]
    end

    subgraph API["FastAPI app"]
        UP["/documents POST\n(upload)"]
        ASK["/ask POST\n(question)"]
        DOCS["/documents GET\n(list/status)"]
    end

    subgraph Pipeline["RAG pipeline"]
        EXT[Extract text\npypdf / plaintext]
        CHK[Chunk\nsliding window + overlap]
        EMB[Embed\nsentence-transformers]
        RET[Retrieve\ncosine similarity]
        GEN[Generate\nOpenAI or extractive fallback]
    end

    subgraph DB["PostgreSQL + pgvector"]
        T1[(documents)]
        T2[(document_chunks\nvector(384))]
    end

    U -->|upload file| UP --> EXT --> CHK --> EMB --> T2
    UP --> T1
    U -->|ask question| ASK --> RET --> T2
    RET --> GEN --> U
    U --> DOCS --> T1
```

**Request flow, upload:** `POST /documents` → extract text → chunk with
overlap → embed each chunk locally → persist document + chunk rows (with
`vector(384)` embeddings) in Postgres.

**Request flow, ask:** `POST /ask` → embed the question → cosine-similarity
search over `document_chunks` via pgvector's `<=>` operator → top-K chunks
passed to the generation step (OpenAI if configured, otherwise an extractive
summary of the passages themselves) → answer + cited sources returned.

## Tech stack

| Concern              | Choice                                                |
|-----------------------|-------------------------------------------------------|
| API framework          | FastAPI + Pydantic v2                                 |
| Database                | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) |
| ORM / migrations        | SQLAlchemy 2.0 + Alembic                              |
| Embeddings               | `sentence-transformers` (`all-MiniLM-L6-v2`, local)    |
| Generation (optional)     | OpenAI chat completions                              |
| Containerization           | Docker multi-stage build + Docker Compose           |
| Auth                         | API key (`X-API-Key` header)                      |
| CI                             | GitHub Actions (lint + tests against a real pgvector service) |
| Testing                          | pytest, FastAPI `TestClient`                    |

## Quickstart

```bash
git clone https://github.com/<your-username>/ragdocs.git
cd ragdocs
cp .env.example .env        # defaults work out of the box for local dev
make up                     # docker compose up --build -d (db, migrate, api)
```

The API is now live at `http://localhost:8000`. Interactive docs:
`http://localhost:8000/docs`.

```bash
# Upload a document
curl -F "file=@README.md" \
     -H "X-API-Key: change-me-local-dev-key" \
     http://localhost:8000/documents

# Ask a question about what you've ingested
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -H "X-API-Key: change-me-local-dev-key" \
     -d '{"question": "What database does this project use for vector search?"}'
```

Tear down: `make down`.

## Running without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# Point DATABASE_URL at any Postgres instance with the pgvector extension available
alembic upgrade head
uvicorn app.main:app --reload
```

## API surface

| Method | Path                | Auth | Description                              |
|--------|----------------------|------|-------------------------------------------|
| GET    | `/health`             | —    | Liveness probe                            |
| GET    | `/health/ready`       | —    | Readiness probe (checks DB connectivity)  |
| POST   | `/documents`          | ✅   | Upload + ingest a PDF/text/markdown file  |
| GET    | `/documents`          | ✅   | List ingested documents + status          |
| GET    | `/documents/{id}`     | ✅   | Get one document's status                 |
| DELETE | `/documents/{id}`     | ✅   | Delete a document and its chunks          |
| POST   | `/ask`                | ✅   | Ask a question, get an answer + sources   |

Full interactive schema at `/docs` (Swagger) or `/redoc`.

## Testing

```bash
make test            # unit tests only, no DB required
```

`tests/test_ingestion_integration.py` runs a full ingest → embed → retrieve
round trip against a real pgvector database; it auto-skips locally if
`DATABASE_URL`/`TEST_DATABASE_URL` isn't reachable, and runs for real in CI
against a Postgres service container (see `.github/workflows/ci.yml`).

## Design notes / trade-offs

- **Synchronous ingestion.** Chunking + embedding happen inline in the
  upload request for simplicity. For large corpora or high upload volume,
  this is the first thing I'd move to a background task queue (Celery/RQ)
  with the `documents.status` field (already `pending → processing → ready`)
  driving a polling or webhook-based client experience.
- **Single shared API key.** Deliberately minimal so every route is
  demonstrably guarded without the overhead of a full user/auth system that
  would be out of scope here; swapping in OAuth2/JWT only touches
  `app/core/security.py`.
- **Local embeddings, optional cloud generation.** Keeps the project
  runnable end-to-end at zero cost, while still showing how a real LLM
  would be wired in for production-quality answers.
- **IVFFlat index on the embedding column**, created in the initial
  migration, for approximate-nearest-neighbor search that scales past a
  toy dataset.

## Project layout

```
app/
  api/routes/     FastAPI routers (documents, chat, health)
  core/           settings, logging, auth
  db/             engine/session setup
  models/         SQLAlchemy ORM models
  schemas/        Pydantic request/response models
  services/       chunking, embeddings, retrieval, generation, ingestion
alembic/          database migrations
tests/            unit + integration tests
.github/workflows/ CI pipeline
```

## License

MIT — see [LICENSE](LICENSE).
