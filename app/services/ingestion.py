"""Document ingestion pipeline: extract text -> chunk -> embed -> persist."""
import io

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

logger = get_logger(__name__)
settings = get_settings()

SUPPORTED_CONTENT_TYPES = {"application/pdf", "text/plain", "text/markdown"}


class UnsupportedFileType(Exception):
    pass


def extract_text(content: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if content_type in {"text/plain", "text/markdown"}:
        return content.decode("utf-8", errors="ignore")
    raise UnsupportedFileType(content_type)


def ingest_document(db: Session, document: Document, content: bytes) -> None:
    """Process a previously-created ``Document`` row synchronously.

    Kept synchronous (rather than pushed to a task queue) to keep the
    reference implementation simple; see README "Future Improvements" for
    how this would be offloaded to Celery/RQ for larger corpora.
    """
    document.status = DocumentStatus.PROCESSING
    db.add(document)
    db.commit()

    try:
        text = extract_text(content, document.content_type)
        pieces = chunk_text(text, settings.chunk_size, settings.chunk_overlap)

        if not pieces:
            raise ValueError("No extractable text found in document")

        vectors = embed_texts(pieces)

        for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=piece,
                    embedding=vector,
                )
            )

        document.status = DocumentStatus.READY
        document.chunk_count = len(pieces)
        db.add(document)
        db.commit()
        logger.info("document_ingested", document_id=str(document.id), chunks=len(pieces))
    except Exception as exc:  # noqa: BLE001 - persisted for API visibility, then re-raised
        db.rollback()
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)[:1024]
        db.add(document)
        db.commit()
        logger.error("document_ingestion_failed", document_id=str(document.id), error=str(exc))
        raise
