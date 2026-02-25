"""Tests for Process Stations CRUD API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.stations import create_station, delete_station, get_station, list_stations, update_station
from app.schemas.process_station import ProcessStationCreate


@pytest.fixture
def station_payload():
    return ProcessStationCreate(
        production_line_id=uuid.uuid4(),
        name="SMT Station 1",
        station_order=1,
        equipment_type="SMT",
        standard_cycle_time=45.0,
    )


@pytest.fixture
def mock_station(station_factory):
    return station_factory.create()


class TestListStations:
    @pytest.mark.asyncio
    async def test_list_returns_stations(self, mock_db, station_factory):
        stations = [station_factory.create(), station_factory.create()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = stations
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_stations(production_line_id=None, skip=0, limit=50, db=mock_db)
        assert len(result) == 2
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_filters_by_line_id(self, mock_db, station_factory):
        line_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [station_factory.create(production_line_id=line_id)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_stations(production_line_id=line_id, skip=0, limit=50, db=mock_db)
        assert len(result) == 1


class TestCreateStation:
    @pytest.mark.asyncio
    async def test_create_success(self, mock_db, station_payload):
        mock_db.refresh = AsyncMock()
        result = await create_station(payload=station_payload, db=mock_db)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


class TestGetStation:
    @pytest.mark.asyncio
    async def test_get_found(self, mock_db, mock_station):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_station
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_station(station_id=mock_station.id, db=mock_db)
        assert result == mock_station

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await get_station(station_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404


class TestUpdateStation:
    @pytest.mark.asyncio
    async def test_update_success(self, mock_db, mock_station, station_payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_station
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.refresh = AsyncMock()

        result = await update_station(station_id=mock_station.id, payload=station_payload, db=mock_db)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, mock_db, station_payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await update_station(station_id=uuid.uuid4(), payload=station_payload, db=mock_db)
        assert exc_info.value.status_code == 404


class TestDeleteStation:
    @pytest.mark.asyncio
    async def test_delete_success(self, mock_db, mock_station):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_station
        mock_db.execute = AsyncMock(return_value=mock_result)

        await delete_station(station_id=mock_station.id, db=mock_db)
        mock_db.delete.assert_awaited_once_with(mock_station)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await delete_station(station_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404
