from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness probe: process is up. Does not touch the database."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    """Readiness probe: confirms the database connection is usable."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
