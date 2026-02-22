"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import async_session_factory, close_db, init_db
from app.core.qdrant import close_qdrant, init_qdrant
from app.core.redis import close_redis, init_redis
from app.db.seed import seed_if_empty

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Starting %s ...", settings.PROJECT_NAME)

    # Startup
    await init_db()
    logger.info("Database initialized")

    async with async_session_factory() as session:
        result = await seed_if_empty(session)
        if result:
            await session.commit()
            logger.info("Demo data seeded: %s", result)
        else:
            logger.info("Database already has data, skipping seed")

    await init_redis()
    logger.info("Redis connected")

    await init_qdrant()
    logger.info("Qdrant connected")

    # Ensure Qdrant 'memories' collection exists
    from app.core.qdrant import get_qdrant
    from app.services.memory_service import MemoryService

    async with async_session_factory() as session:
        memory_svc = MemoryService(db=session, qdrant=get_qdrant())
        await memory_svc.ensure_collection()
    logger.info("Qdrant memories collection ready")

    yield

    # Shutdown
    await close_qdrant()
    logger.info("Qdrant disconnected")

    await close_redis()
    logger.info("Redis disconnected")

    await close_db()
    logger.info("Database disconnected")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 router
app.include_router(api_v1_router, prefix="/api/v1")
