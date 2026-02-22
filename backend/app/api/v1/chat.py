"""Chat API endpoint for natural language conversation."""

from fastapi import APIRouter, Depends
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.qdrant import get_qdrant_from_app
from app.core.rate_limit import rate_limit_strict
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.llm_router import LLMRouter
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_chat_service(
    db: AsyncSession = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant_from_app),
) -> ChatService:
    """Dependency to construct a ChatService with its collaborators."""
    memory_service = MemoryService(db=db, qdrant=qdrant)
    llm_router = LLMRouter(db=db)
    return ChatService(db=db, llm_router=llm_router, memory_service=memory_service)


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_strict)])
async def send_message(
    payload: ChatRequest,
    svc: ChatService = Depends(_get_chat_service),
) -> ChatResponse:
    """Process a natural language chat message with scheduling context."""
    return await svc.handle_message(payload)
