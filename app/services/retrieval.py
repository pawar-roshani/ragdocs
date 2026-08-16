"""Vector similarity retrieval over stored chunks using pgvector."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embeddings import embed_query

settings = get_settings()


class RetrievedChunk:
    def __init__(self, chunk: DocumentChunk, filename: str, similarity: float) -> None:
        self.chunk = chunk
        self.filename = filename
        self.similarity = similarity


def retrieve_relevant_chunks(
    db: Session,
    question: str,
    document_id: uuid.UUID | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    query_vector = embed_query(question)
    k = top_k or settings.top_k

    # cosine_distance ranges [0, 2]; similarity = 1 - distance for unit vectors.
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .order_by(distance)
        .limit(k)
    )
    if document_id is not None:
        stmt = stmt.where(DocumentChunk.document_id == document_id)

    results = db.execute(stmt).all()
    return [
        RetrievedChunk(chunk=row[0], filename=row[1], similarity=1 - float(row[2]))
        for row in results
    ]
