from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import require_api_key
from app.schemas.chat import AskRequest, AskResponse, SourceChunk
from app.services.generation import generate_answer
from app.services.retrieval import retrieve_relevant_chunks

router = APIRouter(tags=["chat"], dependencies=[Depends(require_api_key)])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    retrieved = retrieve_relevant_chunks(
        db, payload.question, document_id=payload.document_id, top_k=payload.top_k
    )
    answer, mode = generate_answer(payload.question, retrieved)

    return AskResponse(
        answer=answer,
        generation_mode=mode,
        sources=[
            SourceChunk(
                document_id=r.chunk.document_id,
                filename=r.filename,
                chunk_index=r.chunk.chunk_index,
                content=r.chunk.content,
                similarity=r.similarity,
            )
            for r in retrieved
        ],
    )
