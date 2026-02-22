"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1.orders import router as orders_router

api_v1_router = APIRouter()
api_v1_router.include_router(orders_router)


@api_v1_router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning 200 OK."""
    return {"status": "ok"}
