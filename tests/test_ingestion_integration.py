"""End-to-end ingestion + retrieval test against a real Postgres+pgvector DB.

Skips automatically when no reachable database is configured, so `pytest`
still passes locally without Docker running. CI (see .github/workflows/ci.yml)
spins up a real pgvector service container so this test runs there.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.document import Document, DocumentStatus
from app.services.ingestion import ingest_document
from app.services.retrieval import retrieve_relevant_chunks

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _database_available() -> bool:
    if not DATABASE_URL:
        return False
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _database_available(), reason="No reachable TEST_DATABASE_URL/DATABASE_URL"
)


@pytest.fixture
def db_session():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        Base.metadata.drop_all(engine)
        session.close()


def test_ingest_and_retrieve_round_trip(db_session):
    document = Document(
        filename="notes.txt",
        content_type="text/plain",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    content = (
        b"RAGDocs uses PostgreSQL with the pgvector extension to store "
        b"sentence embeddings for semantic search. "
        b"FastAPI exposes the ingestion and question-answering endpoints. "
        b"Docker Compose wires the API and database together for local development."
    )
    ingest_document(db_session, document, content)

    assert document.status == DocumentStatus.READY
    assert document.chunk_count > 0

    results = retrieve_relevant_chunks(db_session, "What database does this project use?")
    assert len(results) > 0
    assert any("pgvector" in r.chunk.content.lower() for r in results)
