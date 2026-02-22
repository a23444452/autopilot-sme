"""Embedding service for text-to-vector conversion using OpenAI embedding API.

Used by the semantic memory layer to convert text into vector embeddings
for storage in Qdrant and similarity search.
"""

import logging
from typing import Any

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Converts text to vector embeddings via OpenAI embedding API."""

    def __init__(self) -> None:
        self._client: openai.AsyncOpenAI | None = None
        self._model = DEFAULT_EMBEDDING_MODEL
        self._dimensions = DEFAULT_EMBEDDING_DIMENSIONS

        if settings.OPENAI_API_KEY:
            self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        return self._dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Convert a single text string into a vector embedding.

        Returns a list of floats representing the embedding vector.
        Raises RuntimeError if the OpenAI client is not configured.
        """
        if not self._client:
            raise RuntimeError(
                "EmbeddingService requires OPENAI_API_KEY to be configured."
            )

        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
            dimensions=self._dimensions,
        )

        embedding = response.data[0].embedding
        logger.info(
            "Generated embedding: model=%s dims=%d tokens=%d",
            self._model,
            len(embedding),
            response.usage.total_tokens if response.usage else 0,
        )
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convert multiple texts into vector embeddings in a single API call.

        Returns a list of embedding vectors in the same order as the input texts.
        """
        if not self._client:
            raise RuntimeError(
                "EmbeddingService requires OPENAI_API_KEY to be configured."
            )

        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )

        # Sort by index to preserve input order
        sorted_data = sorted(response.data, key=lambda d: d.index)
        embeddings = [item.embedding for item in sorted_data]

        logger.info(
            "Generated %d embeddings: model=%s tokens=%d",
            len(embeddings),
            self._model,
            response.usage.total_tokens if response.usage else 0,
        )
        return embeddings

    def get_metadata(self) -> dict[str, Any]:
        """Return service metadata for compliance/audit logging."""
        return {
            "model": self._model,
            "dimensions": self._dimensions,
            "provider": "openai",
            "configured": self._client is not None,
        }
