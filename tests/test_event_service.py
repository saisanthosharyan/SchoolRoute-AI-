from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import (
    Bus,
    BusCapacityEvent,
    Driver,
    Route,
    RouteDisruptionEvent,
)
from app.services.event_service import (
    EventServiceError,
    change_bus_capacity,
    report_route_disruption,
    resolve_route_disruption,
)


@pytest.fixture
def db():
    """Provide a fresh in-memory SQLite database for each test."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = TestSession()

    bus = Bus(
        bus_id="TEST-BUS-001",
        registration_number="TEST-REG-001",
        capacity=40,
        is_accessible=True,
        operational_status="active",
        capacity_effective_from=date(2026, 1, 1),
        capacity_effective_to=None,
    )

    driver = Driver(
        driver_id="TEST-DRIVER-001",
        driver_name="Test Driver",
        synthetic_license_number="TEST-LICENSE-001",
        license_valid_until=date(2028, 12, 31),
        is_active=True,
    )

    route = Route(
        route_id="TEST-ROUTE-001",
        bus_id="TEST-BUS-001",
        driver_id="TEST-DRIVER-001",
        route_name="Test Route",
        school_year=2026,
        estimated_duration_minutes=45,
        total_distance_km=15.0,
        route_status="active",
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )

    session.add_all([bus, driver, route])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_bus_capacity_change_records_history(db):
    bus = db.get(Bus, "TEST-BUS-001")

    event_record = change_bus_capacity(
        db,
        bus.bus_id,
        35,
        date.today(),
        "Vehicle capacity inspection",
    )

    assert bus.capacity == 35
    assert event_record.previous_capacity == 40
    assert event_record.new_capacity == 35
    assert event_record.reason == "Vehicle capacity inspection"

    saved_event = db.get(
        BusCapacityEvent,
        event_record.capacity_event_id,
    )

    assert saved_event is not None


def test_bus_capacity_rejects_zero(db):
    with pytest.raises(EventServiceError):
        change_bus_capacity(
            db,
            "TEST-BUS-001",
            0,
            date.today(),
            "Invalid capacity test",
        )


def test_bus_capacity_rejects_unchanged_value(db):
    with pytest.raises(EventServiceError):
        change_bus_capacity(
            db,
            "TEST-BUS-001",
            40,
            date.today(),
            "Unchanged capacity test",
        )


def test_route_disruption_changes_route_status(db):
    route = db.get(Route, "TEST-ROUTE-001")

    disruption = report_route_disruption(
        db,
        route.route_id,
        "traffic",
        "Heavy traffic near the school.",
        severity="medium",
    )

    assert route.route_status == "disrupted"
    assert disruption.status == "active"

    resolve_route_disruption(
        db,
        disruption.disruption_event_id,
        "Traffic cleared.",
    )

    assert disruption.status == "resolved"
    assert route.route_status == "active"


def test_multiple_disruptions_require_all_to_be_resolved(db):
    route = db.get(Route, "TEST-ROUTE-001")

    first = report_route_disruption(
        db,
        route.route_id,
        "traffic",
        "Traffic disruption.",
        severity="medium",
    )

    second = report_route_disruption(
        db,
        route.route_id,
        "weather",
        "Heavy rain disruption.",
        severity="high",
    )

    assert route.route_status == "disrupted"

    resolve_route_disruption(
        db,
        first.disruption_event_id,
        "Traffic cleared.",
    )

    assert route.route_status == "disrupted"

    resolve_route_disruption(
        db,
        second.disruption_event_id,
        "Weather cleared.",
    )

    assert route.route_status == "active"


def test_invalid_disruption_type_is_rejected(db):
    with pytest.raises(EventServiceError):
        report_route_disruption(
            db,
            "TEST-ROUTE-001",
            "unknown_type",
            "Invalid disruption test.",
        )


def test_invalid_disruption_severity_is_rejected(db):
    with pytest.raises(EventServiceError):
        report_route_disruption(
            db,
            "TEST-ROUTE-001",
            "traffic",
            "Invalid severity test.",
            severity="extreme",
        )


def test_disruption_cannot_be_resolved_without_notes(db):
    disruption = report_route_disruption(
        db,
        "TEST-ROUTE-001",
        "traffic",
        "Traffic test.",
    )

    with pytest.raises(EventServiceError):
        resolve_route_disruption(
            db,
            disruption.disruption_event_id,
            "",
        )


def test_resolved_disruption_cannot_be_resolved_again(db):
    disruption = report_route_disruption(
        db,
        "TEST-ROUTE-001",
        "traffic",
        "Traffic test.",
    )

    resolve_route_disruption(
        db,
        disruption.disruption_event_id,
        "Traffic cleared.",
    )

    with pytest.raises(EventServiceError):
        resolve_route_disruption(
            db,
            disruption.disruption_event_id,
            "Attempted second resolution.",
        )
