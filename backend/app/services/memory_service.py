"""Memory service for CRUD on decision records, vector storage/retrieval, and lifecycle management.

Provides:
- Episodic memory: CRUD for DecisionLog records
- Semantic memory: vector storage and retrieval via Qdrant
- Importance scoring based on access patterns and content
- Lifecycle management: hot → warm → cold transitions
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import DecisionLog, MemoryEntry
from app.schemas.memory import DecisionLogResponse, MemoryEntryResponse
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Qdrant collection name for semantic memories
MEMORIES_COLLECTION = "memories"

# Lifecycle thresholds (days since last access)
HOT_THRESHOLD_DAYS = 7
WARM_THRESHOLD_DAYS = 90

# Default embedding dimensions (must match EmbeddingService)
EMBEDDING_DIMENSIONS = 1536


class MemoryService:
    """Manages the three-tier memory system: structured, episodic, and semantic."""

    def __init__(
        self,
        db: AsyncSession,
        qdrant: AsyncQdrantClient,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.qdrant = qdrant
        self._embedding = embedding_service or EmbeddingService()

    # -------------------------------------------------------------------
    # Collection Setup
    # -------------------------------------------------------------------

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist."""
        collections = await self.qdrant.get_collections()
        existing = {c.name for c in collections.collections}
        if MEMORIES_COLLECTION not in existing:
            await self.qdrant.create_collection(
                collection_name=MEMORIES_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", MEMORIES_COLLECTION)

    # -------------------------------------------------------------------
    # Decision Log CRUD (Episodic Memory)
    # -------------------------------------------------------------------

    async def create_decision(
        self,
        decision_type: str,
        situation: str,
        context: dict[str, Any] | None = None,
        options_considered: dict[str, Any] | None = None,
        chosen_option: str | None = None,
        outcome: dict[str, Any] | None = None,
        lessons_learned: str | None = None,
        confidence: float = 0.0,
    ) -> DecisionLog:
        """Create a new decision log record and store its embedding in Qdrant."""
        decision = DecisionLog(
            decision_type=decision_type,
            situation=situation,
            context=context,
            options_considered=options_considered,
            chosen_option=chosen_option,
            outcome=outcome,
            lessons_learned=lessons_learned,
            confidence=confidence,
        )
        self.db.add(decision)
        await self.db.flush()

        # Also create a corresponding MemoryEntry for unified search
        memory = MemoryEntry(
            memory_type="episodic",
            category=decision_type,
            content=situation,
            metadata={"decision_log_id": str(decision.id)},
            importance=self._score_importance(situation, decision_type),
            lifecycle="hot",
        )
        self.db.add(memory)
        await self.db.flush()

        # Store embedding in Qdrant for semantic search
        await self._store_embedding(
            point_id=str(memory.id),
            text=situation,
            metadata={
                "memory_id": str(memory.id),
                "decision_log_id": str(decision.id),
                "memory_type": "episodic",
                "category": decision_type,
                "lifecycle": "hot",
            },
        )

        logger.info("Created decision log %s (type=%s)", decision.id, decision_type)
        return decision

    async def get_decision(self, decision_id: uuid.UUID) -> DecisionLog | None:
        """Retrieve a decision log by ID."""
        stmt = select(DecisionLog).where(DecisionLog.id == decision_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_decisions(
        self,
        decision_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DecisionLog]:
        """List decision logs with optional type filter."""
        stmt = select(DecisionLog).order_by(DecisionLog.created_at.desc())
        if decision_type:
            stmt = stmt.where(DecisionLog.decision_type == decision_type)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_decision_outcome(
        self,
        decision_id: uuid.UUID,
        outcome: dict[str, Any],
        lessons_learned: str | None = None,
    ) -> DecisionLog | None:
        """Update a decision's outcome and lessons learned after it was applied."""
        decision = await self.get_decision(decision_id)
        if not decision:
            return None

        decision.outcome = outcome
        if lessons_learned is not None:
            decision.lessons_learned = lessons_learned
        await self.db.flush()

        logger.info("Updated decision outcome for %s", decision_id)
        return decision

    # -------------------------------------------------------------------
    # Memory Entry CRUD
    # -------------------------------------------------------------------

    async def create_memory(
        self,
        memory_type: str,
        category: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
    ) -> MemoryEntry:
        """Create a memory entry and optionally store its embedding."""
        if importance is None:
            importance = self._score_importance(content, category)

        memory = MemoryEntry(
            memory_type=memory_type,
            category=category,
            content=content,
            metadata=metadata,
            importance=importance,
            lifecycle="hot",
        )
        self.db.add(memory)
        await self.db.flush()

        # Store embedding for semantic search if type is episodic or semantic
        if memory_type in ("episodic", "semantic"):
            await self._store_embedding(
                point_id=str(memory.id),
                text=content,
                metadata={
                    "memory_id": str(memory.id),
                    "memory_type": memory_type,
                    "category": category,
                    "lifecycle": "hot",
                },
            )

        return memory

    async def get_memory(self, memory_id: uuid.UUID) -> MemoryEntry | None:
        """Retrieve a memory entry by ID and update access tracking."""
        stmt = select(MemoryEntry).where(MemoryEntry.id == memory_id)
        result = await self.db.execute(stmt)
        memory = result.scalar_one_or_none()

        if memory:
            memory.access_count += 1
            memory.last_accessed_at = datetime.now(timezone.utc)
            await self.db.flush()

        return memory

    async def list_memories(
        self,
        memory_type: str | None = None,
        category: str | None = None,
        lifecycle: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List memory entries with optional filters."""
        stmt = select(MemoryEntry).order_by(MemoryEntry.created_at.desc())
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        if category:
            stmt = stmt.where(MemoryEntry.category == category)
        if lifecycle:
            stmt = stmt.where(MemoryEntry.lifecycle == lifecycle)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Semantic Search (Vector)
    # -------------------------------------------------------------------

    async def search_memories(
        self,
        query: str,
        memory_type: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories using semantic similarity via Qdrant.

        Returns a list of dicts with memory_id, score, and payload.
        Falls back to SQL text search if embedding fails.
        """
        try:
            vector = await self._embedding.embed_text(query)
        except Exception as exc:
            logger.warning("Embedding failed, falling back to SQL search: %s", exc)
            return await self._sql_text_search(query, memory_type, category, limit)

        # Build Qdrant filter conditions
        conditions = []
        if memory_type:
            conditions.append(
                FieldCondition(key="memory_type", match=MatchValue(value=memory_type))
            )
        if category:
            conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = await self.qdrant.query_points(
            collection_name=MEMORIES_COLLECTION,
            query=vector,
            query_filter=query_filter,
            limit=limit,
        )

        hits: list[dict[str, Any]] = []
        for point in results.points:
            payload = point.payload or {}
            memory_id = payload.get("memory_id")
            hits.append({
                "memory_id": memory_id,
                "score": point.score,
                "payload": payload,
            })

            # Update access tracking in DB
            if memory_id:
                try:
                    mid = uuid.UUID(memory_id)
                    await self.db.execute(
                        update(MemoryEntry)
                        .where(MemoryEntry.id == mid)
                        .values(
                            access_count=MemoryEntry.access_count + 1,
                            last_accessed_at=datetime.now(timezone.utc),
                        )
                    )
                except Exception:
                    pass  # Non-critical: access tracking failure shouldn't break search

        return hits

    @staticmethod
    def _escape_ilike(value: str) -> str:
        """Escape special ILIKE characters (%, _, \\) to prevent pattern injection."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async def _sql_text_search(
        self,
        query: str,
        memory_type: str | None,
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback text search using SQL ILIKE when embedding is unavailable."""
        escaped_query = self._escape_ilike(query)
        stmt = select(MemoryEntry).where(
            MemoryEntry.content.ilike(f"%{escaped_query}%")
        )
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        if category:
            stmt = stmt.where(MemoryEntry.category == category)
        stmt = stmt.order_by(MemoryEntry.importance.desc()).limit(limit)

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        return [
            {
                "memory_id": str(m.id),
                "score": m.importance,
                "payload": {
                    "memory_type": m.memory_type,
                    "category": m.category,
                    "content": m.content,
                },
            }
            for m in memories
        ]

    # -------------------------------------------------------------------
    # Importance Scoring
    # -------------------------------------------------------------------

    @staticmethod
    def _score_importance(content: str, category: str) -> float:
        """Score the importance of a memory entry (0.0 - 1.0).

        Factors:
        - Content length (longer = more detailed = higher importance)
        - Category weight (scheduling decisions > general facts)
        - Keyword presence (rush, urgent, failure, exception)
        """
        score = 0.5  # Base score

        # Content length factor
        if len(content) > 500:
            score += 0.1
        elif len(content) > 200:
            score += 0.05

        # Category weights
        category_weights: dict[str, float] = {
            "scheduling": 0.15,
            "rush_order": 0.2,
            "exception": 0.2,
            "simulation": 0.1,
            "delivery_query": 0.05,
            "chat": 0.0,
        }
        score += category_weights.get(category, 0.0)

        # Keyword boosting
        high_importance_keywords = ["urgent", "rush", "failure", "exception", "delay",
                                     "緊急", "趕工", "故障", "異常", "延遲"]
        content_lower = content.lower()
        for keyword in high_importance_keywords:
            if keyword in content_lower:
                score += 0.05

        return min(round(score, 3), 1.0)

    # -------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------

    async def run_lifecycle_transitions(self) -> dict[str, int]:
        """Transition memories between lifecycle stages based on age.

        hot (<7 days) → warm (7-90 days) → cold (>90 days)
        Returns counts of transitioned records.
        """
        now = datetime.now(timezone.utc)
        warm_cutoff = now - timedelta(days=HOT_THRESHOLD_DAYS)
        cold_cutoff = now - timedelta(days=WARM_THRESHOLD_DAYS)

        # hot → warm
        hot_to_warm = await self.db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.lifecycle == "hot")
            .where(MemoryEntry.created_at < warm_cutoff)
            .values(lifecycle="warm")
            .returning(func.count())
        )
        warm_count = hot_to_warm.scalar() or 0

        # warm → cold
        warm_to_cold = await self.db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.lifecycle == "warm")
            .where(MemoryEntry.created_at < cold_cutoff)
            .values(lifecycle="cold")
            .returning(func.count())
        )
        cold_count = warm_to_cold.scalar() or 0

        if warm_count or cold_count:
            logger.info(
                "Lifecycle transitions: hot→warm=%d, warm→cold=%d",
                warm_count, cold_count,
            )

        return {"hot_to_warm": warm_count, "warm_to_cold": cold_count}

    # -------------------------------------------------------------------
    # Vector Storage Helpers
    # -------------------------------------------------------------------

    async def _store_embedding(
        self,
        point_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        """Generate an embedding for text and store it in Qdrant."""
        try:
            vector = await self._embedding.embed_text(text)
            await self.qdrant.upsert(
                collection_name=MEMORIES_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=metadata,
                    )
                ],
            )
        except Exception as exc:
            logger.warning("Failed to store embedding for %s: %s", point_id, exc)
            # Non-critical: SQL data is still persisted even if vector storage fails
