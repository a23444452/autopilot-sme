"""Seed script with demo data for all 4 core manufacturing scenarios.

Scenarios covered:
1. Standard multi-product scheduling across production lines
2. Rush order insertion with priority override
3. Line capacity constraints and changeover optimization
4. Delivery date estimation with confidence intervals
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.production_line import ProductionLine

# Fixed UUIDs for deterministic seeding
PRODUCT_IDS = {
    "PCB-A100": uuid.UUID("a0000000-0000-0000-0000-000000000001"),
    "PCB-B200": uuid.UUID("a0000000-0000-0000-0000-000000000002"),
    "SENSOR-T1": uuid.UUID("a0000000-0000-0000-0000-000000000003"),
    "MOTOR-M50": uuid.UUID("a0000000-0000-0000-0000-000000000004"),
    "CABLE-C10": uuid.UUID("a0000000-0000-0000-0000-000000000005"),
    "HOUSING-H3": uuid.UUID("a0000000-0000-0000-0000-000000000006"),
}

LINE_IDS = {
    "SMT-Line-1": uuid.UUID("b0000000-0000-0000-0000-000000000001"),
    "SMT-Line-2": uuid.UUID("b0000000-0000-0000-0000-000000000002"),
    "Assembly-A": uuid.UUID("b0000000-0000-0000-0000-000000000003"),
    "Assembly-B": uuid.UUID("b0000000-0000-0000-0000-000000000004"),
}

ORDER_IDS = {
    "ORD-2026-001": uuid.UUID("c0000000-0000-0000-0000-000000000001"),
    "ORD-2026-002": uuid.UUID("c0000000-0000-0000-0000-000000000002"),
    "ORD-2026-003": uuid.UUID("c0000000-0000-0000-0000-000000000003"),
    "ORD-2026-004": uuid.UUID("c0000000-0000-0000-0000-000000000004"),
    "ORD-2026-005": uuid.UUID("c0000000-0000-0000-0000-000000000005"),
    "ORD-2026-006": uuid.UUID("c0000000-0000-0000-0000-000000000006"),
    "ORD-2026-007": uuid.UUID("c0000000-0000-0000-0000-000000000007"),
    "ORD-2026-008": uuid.UUID("c0000000-0000-0000-0000-000000000008"),
    "ORD-2026-009": uuid.UUID("c0000000-0000-0000-0000-000000000009"),
    "ORD-2026-010": uuid.UUID("c0000000-0000-0000-0000-000000000010"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_from_now(days: int) -> datetime:
    return _now() + timedelta(days=days)


def _create_products() -> list[Product]:
    """Create 6 products covering PCB, sensor, motor, cable, and housing."""
    return [
        Product(
            id=PRODUCT_IDS["PCB-A100"],
            sku="PCB-A100",
            name="主板 A100",
            description="高密度多層PCB主板，適用於工業控制器",
            standard_cycle_time=2.5,
            setup_time=45.0,
            yield_rate=0.93,
        ),
        Product(
            id=PRODUCT_IDS["PCB-B200"],
            sku="PCB-B200",
            name="電源板 B200",
            description="電源管理PCB板，支援多電壓輸出",
            standard_cycle_time=1.8,
            setup_time=30.0,
            yield_rate=0.96,
        ),
        Product(
            id=PRODUCT_IDS["SENSOR-T1"],
            sku="SENSOR-T1",
            name="溫度感測器 T1",
            description="工業級高精度溫度感測器模組",
            standard_cycle_time=3.0,
            setup_time=20.0,
            yield_rate=0.97,
        ),
        Product(
            id=PRODUCT_IDS["MOTOR-M50"],
            sku="MOTOR-M50",
            name="步進馬達 M50",
            description="高扭力步進馬達，適用於CNC設備",
            standard_cycle_time=5.0,
            setup_time=60.0,
            yield_rate=0.91,
        ),
        Product(
            id=PRODUCT_IDS["CABLE-C10"],
            sku="CABLE-C10",
            name="線束組 C10",
            description="客製化線束組件，含端子壓接",
            standard_cycle_time=1.2,
            setup_time=15.0,
            yield_rate=0.98,
        ),
        Product(
            id=PRODUCT_IDS["HOUSING-H3"],
            sku="HOUSING-H3",
            name="鋁合金外殼 H3",
            description="CNC加工鋁合金外殼，IP65防水等級",
            standard_cycle_time=8.0,
            setup_time=90.0,
            yield_rate=0.88,
        ),
    ]


def _create_production_lines() -> list[ProductionLine]:
    """Create 4 production lines with different capabilities."""
    return [
        ProductionLine(
            id=LINE_IDS["SMT-Line-1"],
            name="SMT-Line-1",
            description="高速SMT貼片產線，適用於PCB類產品",
            capacity_per_hour=120,
            efficiency_factor=0.92,
            status="active",
            allowed_products=["PCB-A100", "PCB-B200"],
            changeover_matrix={
                "PCB-A100->PCB-B200": 25,
                "PCB-B200->PCB-A100": 30,
            },
        ),
        ProductionLine(
            id=LINE_IDS["SMT-Line-2"],
            name="SMT-Line-2",
            description="精密SMT產線，支援感測器與PCB產品",
            capacity_per_hour=80,
            efficiency_factor=0.88,
            status="active",
            allowed_products=["PCB-A100", "PCB-B200", "SENSOR-T1"],
            changeover_matrix={
                "PCB-A100->SENSOR-T1": 40,
                "SENSOR-T1->PCB-A100": 35,
                "PCB-B200->SENSOR-T1": 30,
                "SENSOR-T1->PCB-B200": 30,
                "PCB-A100->PCB-B200": 20,
                "PCB-B200->PCB-A100": 25,
            },
        ),
        ProductionLine(
            id=LINE_IDS["Assembly-A"],
            name="Assembly-A",
            description="機電組裝產線，馬達與線束組裝",
            capacity_per_hour=40,
            efficiency_factor=0.85,
            status="active",
            allowed_products=["MOTOR-M50", "CABLE-C10"],
            changeover_matrix={
                "MOTOR-M50->CABLE-C10": 20,
                "CABLE-C10->MOTOR-M50": 25,
            },
        ),
        ProductionLine(
            id=LINE_IDS["Assembly-B"],
            name="Assembly-B",
            description="精密組裝與外殼加工產線",
            capacity_per_hour=25,
            efficiency_factor=0.90,
            status="active",
            allowed_products=["HOUSING-H3", "SENSOR-T1", "CABLE-C10"],
            changeover_matrix={
                "HOUSING-H3->SENSOR-T1": 45,
                "SENSOR-T1->HOUSING-H3": 50,
                "HOUSING-H3->CABLE-C10": 30,
                "CABLE-C10->HOUSING-H3": 35,
                "SENSOR-T1->CABLE-C10": 15,
                "CABLE-C10->SENSOR-T1": 15,
            },
        ),
    ]


def _create_orders_with_items() -> list[Order]:
    """Create 10 orders with items covering all 4 core scenarios."""
    item_id_counter = 0

    def _item_id() -> uuid.UUID:
        nonlocal item_id_counter
        item_id_counter += 1
        return uuid.UUID(f"d0000000-0000-0000-0000-{item_id_counter:012d}")

    orders = [
        # --- Scenario 1: Standard multi-product scheduling ---
        Order(
            id=ORDER_IDS["ORD-2026-001"],
            order_no="ORD-2026-001",
            customer_name="台灣精密工業",
            due_date=_days_from_now(14),
            priority=5,
            status="pending",
            notes="標準訂單，PCB主板批量生產",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-A100"], quantity=500),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-B200"], quantity=300),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-002"],
            order_no="ORD-2026-002",
            customer_name="聯合電子",
            due_date=_days_from_now(10),
            priority=5,
            status="pending",
            notes="感測器模組訂單",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["SENSOR-T1"], quantity=200),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-003"],
            order_no="ORD-2026-003",
            customer_name="大同機械",
            due_date=_days_from_now(21),
            priority=5,
            status="pending",
            notes="馬達與線束組合訂單",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["MOTOR-M50"], quantity=100),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["CABLE-C10"], quantity=400),
            ],
        ),
        # --- Scenario 2: Rush order with priority override ---
        Order(
            id=ORDER_IDS["ORD-2026-004"],
            order_no="ORD-2026-004",
            customer_name="鴻海精密",
            due_date=_days_from_now(3),
            priority=1,
            status="pending",
            notes="🚨 急單！客戶產線停擺，需緊急交貨PCB主板",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-A100"], quantity=200),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-005"],
            order_no="ORD-2026-005",
            customer_name="華碩電腦",
            due_date=_days_from_now(5),
            priority=2,
            status="pending",
            notes="急單 - 電源板緊急補貨",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-B200"], quantity=150),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["CABLE-C10"], quantity=150),
            ],
        ),
        # --- Scenario 3: Line capacity constraints & changeover ---
        Order(
            id=ORDER_IDS["ORD-2026-006"],
            order_no="ORD-2026-006",
            customer_name="工研院",
            due_date=_days_from_now(7),
            priority=3,
            status="in_progress",
            notes="研發樣品，多產品小批量，換線頻繁",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-A100"], quantity=50),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["SENSOR-T1"], quantity=30),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["HOUSING-H3"], quantity=20),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-007"],
            order_no="ORD-2026-007",
            customer_name="台達電子",
            due_date=_days_from_now(12),
            priority=4,
            status="pending",
            notes="外殼加工大單，需考慮產能限制",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["HOUSING-H3"], quantity=80),
            ],
        ),
        # --- Scenario 4: Delivery date estimation ---
        Order(
            id=ORDER_IDS["ORD-2026-008"],
            order_no="ORD-2026-008",
            customer_name="明泰科技",
            due_date=_days_from_now(18),
            priority=5,
            status="pending",
            notes="大量混合訂單，需要精確交期預估",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-A100"], quantity=300),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["MOTOR-M50"], quantity=50),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["CABLE-C10"], quantity=200),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-009"],
            order_no="ORD-2026-009",
            customer_name="研華科技",
            due_date=_days_from_now(25),
            priority=5,
            status="pending",
            notes="長期合約訂單第一批",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["SENSOR-T1"], quantity=500),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-B200"], quantity=250),
            ],
        ),
        Order(
            id=ORDER_IDS["ORD-2026-010"],
            order_no="ORD-2026-010",
            customer_name="光寶科技",
            due_date=_days_from_now(8),
            priority=3,
            status="pending",
            notes="已排程訂單，測試排程衝突處理",
            items=[
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["PCB-B200"], quantity=100),
                OrderItem(id=_item_id(), product_id=PRODUCT_IDS["HOUSING-H3"], quantity=15),
            ],
        ),
    ]

    return orders


async def seed_demo_data(session: AsyncSession) -> dict[str, int]:
    """Seed the database with demo data for all 4 core scenarios.

    Args:
        session: An async SQLAlchemy session.

    Returns:
        Dictionary with counts of created entities.
    """
    products = _create_products()
    lines = _create_production_lines()
    orders = _create_orders_with_items()

    session.add_all(products)
    session.add_all(lines)
    session.add_all(orders)

    await session.flush()

    total_items = sum(len(order.items) for order in orders)

    return {
        "products": len(products),
        "production_lines": len(lines),
        "orders": len(orders),
        "order_items": total_items,
    }


async def seed_if_empty(session: AsyncSession) -> dict[str, int] | None:
    """Seed demo data only if the database is empty.

    Returns:
        Seed counts if data was seeded, None if database already has data.
    """
    from sqlalchemy import text

    result = await session.execute(text("SELECT COUNT(*) FROM products"))
    count = result.scalar() or 0

    if count > 0:
        return None

    return await seed_demo_data(session)
