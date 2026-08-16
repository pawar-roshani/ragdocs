import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import require_api_key
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentList, DocumentRead
from app.services.ingestion import SUPPORTED_CONTENT_TYPES, UnsupportedFileType, ingest_document

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])
settings = get_settings()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> Document:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type '{file.content_type}'. "
            f"Supported: {sorted(SUPPORTED_CONTENT_TYPES)}",
        )

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb}MB limit.",
        )

    document = Document(
        filename=file.filename or "unnamed",
        content_type=file.content_type,
        size_bytes=len(content),
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        ingest_document(db, document, content)
    except UnsupportedFileType:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Could not extract text from this file type.",
        ) from None
    except Exception as exc:  # noqa: BLE001
        # Document row already reflects FAILED status + error_message; surface a 422.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ingestion failed: {exc}",
        ) from exc

    db.refresh(document)
    return document


@router.get("", response_model=DocumentList)
def list_documents(db: Session = Depends(get_db)) -> DocumentList:
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return DocumentList(items=list(documents), total=len(documents))


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(document)
    db.commit()
