"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter, Depends

from app.api.v1.chat import router as chat_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.matching import router as matching_router
from app.api.v1.memory import router as memory_router
from app.api.v1.orders import router as orders_router
from app.api.v1.process_routes import router as process_routes_router
from app.api.v1.production_lines import router as production_lines_router
from app.api.v1.products import router as products_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.simulate import router as simulate_router
from app.api.v1.stations import router as stations_router
from app.core.auth import verify_api_key
from app.core.rate_limit import rate_limit_default

# Public router (no authentication required)
api_v1_router = APIRouter()


@api_v1_router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning 200 OK."""
    return {"status": "ok"}


# Authenticated router with default rate limiting (60 req/min).
# Chat and simulate endpoints additionally enforce strict limits (10 req/min).
_authenticated = APIRouter(dependencies=[Depends(verify_api_key), Depends(rate_limit_default)])
_authenticated.include_router(orders_router)
_authenticated.include_router(products_router)
_authenticated.include_router(production_lines_router)
_authenticated.include_router(schedule_router)
_authenticated.include_router(simulate_router)
_authenticated.include_router(memory_router)
_authenticated.include_router(chat_router)
_authenticated.include_router(compliance_router)
_authenticated.include_router(stations_router)
_authenticated.include_router(process_routes_router)
_authenticated.include_router(matching_router)

api_v1_router.include_router(_authenticated)
