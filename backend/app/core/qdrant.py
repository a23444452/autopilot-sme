"""Qdrant vector database client initialization."""

from qdrant_client import QdrantClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient

from app.core.config import settings

qdrant_client: AsyncQdrantClient | None = None


async def init_qdrant() -> AsyncQdrantClient:
    """Initialize the async Qdrant client. Called during app startup."""
    global qdrant_client
    qdrant_client = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        grpc_port=settings.QDRANT_GRPC_PORT,
        prefer_grpc=True,
    )
    return qdrant_client


async def close_qdrant() -> None:
    """Close the Qdrant client. Called during app shutdown."""
    global qdrant_client
    if qdrant_client is not None:
        await qdrant_client.close()
        qdrant_client = None


def get_qdrant() -> AsyncQdrantClient:
    """FastAPI dependency that returns the Qdrant client."""
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return qdrant_client
