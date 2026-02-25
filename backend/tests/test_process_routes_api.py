"""Tests for Process Routes CRUD API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.process_routes import (
    create_process_route,
    delete_process_route,
    get_process_route,
    list_process_routes,
    update_process_route,
)
from app.schemas.process_route import ProcessRouteCreate

VALID_STEPS = [
    {"station_order": 1, "equipment_type": "SMT", "cycle_time_sec": 45.0},
    {"station_order": 2, "equipment_type": "reflow", "cycle_time_sec": 120.0},
]


@pytest.fixture
def route_payload():
    return ProcessRouteCreate(
        product_id=uuid.uuid4(),
        steps=VALID_STEPS,
    )


@pytest.fixture
def mock_route(route_factory):
    return route_factory.create()


class TestListProcessRoutes:
    @pytest.mark.asyncio
    async def test_list_returns_routes(self, mock_db, route_factory):
        routes = [route_factory.create(), route_factory.create()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = routes
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_process_routes(
            product_id=None, active_only=False, skip=0, limit=50, db=mock_db
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_filters_by_product_id(self, mock_db, route_factory):
        pid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [route_factory.create(product_id=pid)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_process_routes(
            product_id=pid, active_only=False, skip=0, limit=50, db=mock_db
        )
        assert len(result) == 1


class TestCreateProcessRoute:
    @pytest.mark.asyncio
    async def test_create_deactivates_existing(self, mock_db, route_payload):
        mock_db.execute = AsyncMock(return_value=MagicMock())
        mock_db.refresh = AsyncMock()

        await create_process_route(payload=route_payload, db=mock_db)
        # execute called twice: once for deactivation update, once for... actually
        # the deactivation is one execute, then add+flush+refresh
        assert mock_db.execute.await_count == 1  # deactivation UPDATE
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestGetProcessRoute:
    @pytest.mark.asyncio
    async def test_get_found(self, mock_db, mock_route):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_route
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_process_route(route_id=mock_route.id, db=mock_db)
        assert result == mock_route

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await get_process_route(route_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404


class TestUpdateProcessRoute:
    @pytest.mark.asyncio
    async def test_update_success(self, mock_db, mock_route, route_payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_route
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.refresh = AsyncMock()

        result = await update_process_route(
            route_id=mock_route.id, payload=route_payload, db=mock_db
        )
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, mock_db, route_payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await update_process_route(
                route_id=uuid.uuid4(), payload=route_payload, db=mock_db
            )
        assert exc_info.value.status_code == 404


class TestDeleteProcessRoute:
    @pytest.mark.asyncio
    async def test_delete_success(self, mock_db, mock_route):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_route
        mock_db.execute = AsyncMock(return_value=mock_result)

        await delete_process_route(route_id=mock_route.id, db=mock_db)
        mock_db.delete.assert_awaited_once_with(mock_route)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await delete_process_route(route_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404
