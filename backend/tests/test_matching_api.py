"""Tests for Line Capabilities CRUD and Product-to-Line matching API."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.matching import (
    create_line_capability,
    delete_line_capability,
    get_line_capability,
    list_line_capabilities,
    match_product_to_lines,
)
from app.schemas.line_capability import LineCapabilityCreate


@pytest.fixture
def cap_payload():
    return LineCapabilityCreate(
        production_line_id=uuid.uuid4(),
        equipment_type="SMT",
    )


@pytest.fixture
def mock_cap(capability_factory):
    return capability_factory.create()


class TestListLineCapabilities:
    @pytest.mark.asyncio
    async def test_list_returns_capabilities(self, mock_db, capability_factory):
        caps = [capability_factory.create(), capability_factory.create()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = caps
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_line_capabilities(
            production_line_id=None, skip=0, limit=50, db=mock_db
        )
        assert len(result) == 2


class TestCreateLineCapability:
    @pytest.mark.asyncio
    async def test_create_success(self, mock_db, cap_payload):
        mock_db.refresh = AsyncMock()
        await create_line_capability(payload=cap_payload, db=mock_db)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestGetLineCapability:
    @pytest.mark.asyncio
    async def test_get_found(self, mock_db, mock_cap):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cap
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_line_capability(capability_id=mock_cap.id, db=mock_db)
        assert result == mock_cap

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await get_line_capability(capability_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404


class TestDeleteLineCapability:
    @pytest.mark.asyncio
    async def test_delete_success(self, mock_db, mock_cap):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cap
        mock_db.execute = AsyncMock(return_value=mock_result)

        await delete_line_capability(capability_id=mock_cap.id, db=mock_db)
        mock_db.delete.assert_awaited_once_with(mock_cap)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await delete_line_capability(capability_id=uuid.uuid4(), db=mock_db)
        assert exc_info.value.status_code == 404


class TestMatchProductToLines:
    @pytest.mark.asyncio
    async def test_match_returns_lines_with_all_types(self, mock_db, line_factory):
        line1 = line_factory.create(name="Line-A")
        line2 = line_factory.create(name="Line-B")

        # First call: fetch active lines
        lines_result = MagicMock()
        lines_result.scalars.return_value.all.return_value = [line1, line2]

        # Capability queries: line1 has SMT+reflow, line2 has only SMT
        caps_line1 = MagicMock()
        caps_line1.all.return_value = [("SMT",), ("reflow",)]

        caps_line2 = MagicMock()
        caps_line2.all.return_value = [("SMT",)]

        mock_db.execute = AsyncMock(side_effect=[lines_result, caps_line1, caps_line2])

        result = await match_product_to_lines(
            product_id=uuid.uuid4(),
            equipment_types=["SMT", "reflow"],
            db=mock_db,
        )
        assert len(result) == 1
        assert result[0]["name"] == "Line-A"

    @pytest.mark.asyncio
    async def test_match_no_lines_match(self, mock_db, line_factory):
        line = line_factory.create()
        lines_result = MagicMock()
        lines_result.scalars.return_value.all.return_value = [line]

        caps = MagicMock()
        caps.all.return_value = [("assembly",)]

        mock_db.execute = AsyncMock(side_effect=[lines_result, caps])

        result = await match_product_to_lines(
            product_id=uuid.uuid4(),
            equipment_types=["SMT", "reflow"],
            db=mock_db,
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_match_empty_active_lines(self, mock_db):
        lines_result = MagicMock()
        lines_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=lines_result)

        result = await match_product_to_lines(
            product_id=uuid.uuid4(),
            equipment_types=["SMT"],
            db=mock_db,
        )
        assert len(result) == 0
