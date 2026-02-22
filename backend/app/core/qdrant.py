"""Qdrant vector database client initialization using app.state."""

from fastapi import Request
from qdrant_client.async_qdrant_client import AsyncQdrantClient

from app.core.config import settings


async def init_qdrant(app_state: object) -> AsyncQdrantClient:
    """Initialize the async Qdrant client and store it on app.state."""
    client = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        grpc_port=settings.QDRANT_GRPC_PORT,
        prefer_grpc=True,
    )
    app_state.qdrant = client  # type: ignore[attr-defined]
    return client


async def close_qdrant(app_state: object) -> None:
    """Close the Qdrant client stored on app.state."""
    client: AsyncQdrantClient | None = getattr(app_state, "qdrant", None)
    if client is not None:
        await client.close()
        app_state.qdrant = None  # type: ignore[attr-defined]


def get_qdrant_from_app(request: Request) -> AsyncQdrantClient:
    """FastAPI dependency that returns the Qdrant client from app.state."""
    client: AsyncQdrantClient | None = getattr(request.app.state, "qdrant", None)
    if client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return client
