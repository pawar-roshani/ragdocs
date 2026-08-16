from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.environment)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.app_name, environment=settings.environment)
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "A Retrieval-Augmented Generation API: upload PDF/text documents, "
        "they're chunked and embedded into PostgreSQL (pgvector), and you "
        "can ask natural-language questions answered from their content."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)
