"""API-contract tests that don't require a live database.

Auth and validation are checked here without touching Postgres; full
ingestion/retrieval flows are exercised via the `db` marker tests, skipped
automatically when DATABASE_URL isn't reachable (see CI workflow, which runs
a real Postgres+pgvector service so those run there).
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_documents_requires_api_key():
    response = client.get("/documents")
    assert response.status_code == 401


def test_list_documents_rejects_wrong_api_key():
    response = client.get("/documents", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_ask_requires_api_key():
    response = client.post("/ask", json={"question": "What is this about?"})
    assert response.status_code == 401


def test_ask_validates_empty_question(api_key):
    response = client.post(
        "/ask", json={"question": ""}, headers={"X-API-Key": api_key}
    )
    assert response.status_code == 422
