"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.memory import router as memory_router
from app.api.v1.orders import router as orders_router
from app.api.v1.production_lines import router as production_lines_router
from app.api.v1.products import router as products_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.simulate import router as simulate_router

api_v1_router = APIRouter()
api_v1_router.include_router(orders_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(production_lines_router)
api_v1_router.include_router(schedule_router)
api_v1_router.include_router(simulate_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(compliance_router)


@api_v1_router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning 200 OK."""
    return {"status": "ok"}
