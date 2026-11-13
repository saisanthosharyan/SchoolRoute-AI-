
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import (
    AddressZone,
    Student,
    GuardianContact,
    Stop,
    Bus,
    Driver,
    Route,
    RouteStop,
    Assignment,
    AttendanceEvent,
    Notification,
    RouteDisruptionEvent,
)
from app.validators.data_validator import DataValidator


@pytest.fixture
def db():
    """Create an isolated in-memory database with valid test records."""

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

    zone = AddressZone(
        zone_id="TEST-ZONE-001",
        zone_name="Test Zone",
        city="Hyderabad",
        postal_code="500001",
        latitude=17.385,
        longitude=78.4867,
        is_active=True,
    )

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

    student = Student(
        student_id="TEST-STUDENT-001",
        first_name="Test",
        last_name="Student",
        grade=5,
        address_zone_id="TEST-ZONE-001",
        synthetic_address="Test Address",
        latitude=17.385,
        longitude=78.4867,
        requires_accessible_vehicle=False,
        address_is_approved=True,
        enrollment_status="active",
    )

    guardian = GuardianContact(
        guardian_id="TEST-GUARDIAN-001",
        student_id="TEST-STUDENT-001",
        guardian_name="Test Guardian",
        synthetic_phone="+910000000001",
        synthetic_email="guardian@example.test",
        relationship_type="parent",
        preferred_channel="sms",
        is_valid=True,
        is_primary=True,
    )

    stop = Stop(
        stop_id="TEST-STOP-001",
        stop_name="Test Pickup Stop",
        address_zone_id="TEST-ZONE-001",
        latitude=17.385,
        longitude=78.4867,
        pickup_window_start="07:00",
        pickup_window_end="08:00",
        is_approved=True,
        is_accessible=True,
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

    route_stop = RouteStop(
        route_stop_id="TEST-ROUTE-STOP-001",
        route_id="TEST-ROUTE-001",
        stop_id="TEST-STOP-001",
        sequence_number=1,
        estimated_arrival="07:30",
        travel_time_from_previous_minutes=10,
    )

    assignment = Assignment(
        assignment_id="TEST-ASSIGNMENT-001",
        student_id="TEST-STUDENT-001",
        route_id="TEST-ROUTE-001",
        stop_id="TEST-STOP-001",
        school_year=2026,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        assignment_status="active",
    )

    attendance = AttendanceEvent(
        attendance_event_id="TEST-ATTENDANCE-001",
        student_id="TEST-STUDENT-001",
        assignment_id="TEST-ASSIGNMENT-001",
        service_date=date(2026, 11, 13),
        event_type="pickup",
        event_status="present",
        event_timestamp=datetime(2026, 11, 13, 7, 30),
        notes="Test attendance",
    )

    notification = Notification(
        notification_id="TEST-NOTIFICATION-001",
        student_id="TEST-STUDENT-001",
        guardian_id="TEST-GUARDIAN-001",
        attendance_event_id="TEST-ATTENDANCE-001",
        channel="sms",
        message_type="pickup_confirmation",
        notification_status="sent",
        synthetic_recipient="+910000000001",
        created_at=datetime(2026, 11, 13, 7, 31),
        sent_at=datetime(2026, 11, 13, 7, 31),
        failure_reason=None,
    )

    session.add_all([
        zone,
        bus,
        driver,
        student,
        guardian,
        stop,
        route,
        route_stop,
        assignment,
        attendance,
        notification,
    ])

    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_valid_dataset_passes_all_validation_groups(db):
    """A valid relational and operational dataset should pass."""

    validator = DataValidator(db)
    report = validator.run()

    assert report["status"] == "PASSED"
    assert report["error_count"] == 0
    assert report["warning_count"] == 0
    assert report["checks_passed"] > 0


def test_assignment_rejects_stop_not_belonging_to_route(db):
    """An assignment cannot use a stop outside its route."""

    assignment = db.get(
        Assignment,
        "TEST-ASSIGNMENT-001",
    )

    assignment.stop_id = "TEST-STOP-002"

    db.add(
        Stop(
            stop_id="TEST-STOP-002",
            stop_name="Another Stop",
            address_zone_id="TEST-ZONE-001",
            latitude=17.39,
            longitude=78.49,
            pickup_window_start="07:00",
            pickup_window_end="08:00",
            is_approved=True,
            is_accessible=True,
        )
    )

    db.commit()

    validator = DataValidator(db)
    validator.validate_assignments()

    assert any(
        "assigned stop is not part of its route" in error
        for error in validator.errors
    )


def test_capacity_validation_detects_exceeded_capacity(db):
    """Active assignments cannot exceed bus capacity."""

    bus = db.get(Bus, "TEST-BUS-001")
    bus.capacity = 1

    db.add(
        Student(
            student_id="TEST-STUDENT-002",
            first_name="Second",
            last_name="Student",
            grade=6,
            address_zone_id="TEST-ZONE-001",
            synthetic_address="Second Test Address",
            latitude=17.386,
            longitude=78.487,
            requires_accessible_vehicle=False,
            address_is_approved=True,
            enrollment_status="active",
        )
    )

    db.add(
        Assignment(
            assignment_id="TEST-ASSIGNMENT-002",
            student_id="TEST-STUDENT-002",
            route_id="TEST-ROUTE-001",
            stop_id="TEST-STOP-001",
            school_year=2026,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            assignment_status="active",
        )
    )

    db.commit()

    validator = DataValidator(db)
    validator.validate_capacity()

    assert any(
        "capacity exceeded" in error
        for error in validator.errors
    )


def test_accessibility_validation_detects_incompatible_bus(db):
    """Students requiring accessible vehicles need accessible buses."""

    student = db.get(Student, "TEST-STUDENT-001")
    bus = db.get(Bus, "TEST-BUS-001")

    student.requires_accessible_vehicle = True
    bus.is_accessible = False

    db.commit()

    validator = DataValidator(db)
    validator.validate_accessibility()

    assert any(
        "student requires an accessible bus" in error
        for error in validator.errors
    )


def test_accessibility_validation_detects_incompatible_stop(db):
    """Students requiring accessibility need accessible pickup stops."""

    student = db.get(Student, "TEST-STUDENT-001")
    stop = db.get(Stop, "TEST-STOP-001")

    student.requires_accessible_vehicle = True
    stop.is_accessible = False

    db.commit()

    validator = DataValidator(db)
    validator.validate_accessibility()

    assert any(
        "student requires an accessible stop" in error
        for error in validator.errors
    )


def test_route_validation_detects_active_route_without_stops(db):
    """An active route must have at least one stop."""

    db.delete(
        db.get(RouteStop, "TEST-ROUTE-STOP-001")
    )
    db.commit()

    validator = DataValidator(db)
    validator.validate_routes()

    assert any(
        "active route has no stops" in error
        for error in validator.errors
    )


def test_attendance_validation_detects_student_assignment_mismatch(db):
    """Attendance student must match the referenced assignment."""

    db.add(
        Student(
            student_id="TEST-STUDENT-002",
            first_name="Second",
            last_name="Student",
            grade=6,
            address_zone_id="TEST-ZONE-001",
            synthetic_address="Second Test Address",
            latitude=17.386,
            longitude=78.487,
            requires_accessible_vehicle=False,
            address_is_approved=True,
            enrollment_status="active",
        )
    )

    attendance = db.get(
        AttendanceEvent,
        "TEST-ATTENDANCE-001",
    )

    attendance.student_id = "TEST-STUDENT-002"
    db.commit()

    validator = DataValidator(db)
    validator.validate_attendance()

    assert any(
        "student does not match assignment" in error
        for error in validator.errors
    )



def test_notification_validation_detects_guardian_student_mismatch(db):
    """A guardian cannot receive another student's notification."""

    db.add(
        Student(
            student_id="TEST-STUDENT-002",
            first_name="Second",
            last_name="Student",
            grade=6,
            address_zone_id="TEST-ZONE-001",
            synthetic_address="Second Test Address",
            latitude=17.386,
            longitude=78.487,
            requires_accessible_vehicle=False,
            address_is_approved=True,
            enrollment_status="active",
        )
    )

    # Commit the referenced student before changing the notification.
    db.commit()

    notification = db.get(
        Notification,
        "TEST-NOTIFICATION-001",
    )

    notification.student_id = "TEST-STUDENT-002"
    db.commit()

    validator = DataValidator(db)
    validator.validate_notifications()

    assert any(
        "guardian belongs to another student" in error
        for error in validator.errors
    )



def test_notification_validation_detects_attendance_student_mismatch(db):
    """A notification event must belong to its notification student."""

    db.add(
        Student(
            student_id="TEST-STUDENT-002",
            first_name="Second",
            last_name="Student",
            grade=6,
            address_zone_id="TEST-ZONE-001",
            synthetic_address="Second Test Address",
            latitude=17.386,
            longitude=78.487,
            requires_accessible_vehicle=False,
            address_is_approved=True,
            enrollment_status="active",
        )
    )

    notification = db.get(
        Notification,
        "TEST-NOTIFICATION-001",
    )

    notification.attendance_event_id = None
    notification.student_id = "TEST-STUDENT-002"
    notification.guardian_id = "TEST-GUARDIAN-001"

    db.add(
        GuardianContact(
            guardian_id="TEST-GUARDIAN-002",
            student_id="TEST-STUDENT-002",
            guardian_name="Second Guardian",
            synthetic_phone="+910000000002",
            synthetic_email="second@example.test",
            relationship_type="parent",
            preferred_channel="sms",
            is_valid=True,
            is_primary=True,
        )
    )

    notification.guardian_id = "TEST-GUARDIAN-002"
    notification.attendance_event_id = "TEST-ATTENDANCE-001"

    db.commit()

    validator = DataValidator(db)
    validator.validate_notifications()

    assert any(
        "attendance event belongs to another student" in error
        for error in validator.errors
    )


def test_disruption_validation_detects_missing_resolution_details(db):
    """Resolved disruptions require a timestamp and resolution notes."""

    db.add(
        RouteDisruptionEvent(
            disruption_event_id="TEST-DISRUPTION-001",
            route_id="TEST-ROUTE-001",
            affected_stop_id=None,
            disruption_type="traffic",
            severity="medium",
            description="Test disruption",
            started_at=datetime(2026, 11, 13, 8, 0),
            resolved_at=None,
            status="resolved",
            resolution_notes=None,
        )
    )

    db.commit()

    validator = DataValidator(db)
    validator.validate_event_history()

    assert any(
        "resolved event is missing resolution details" in error
        for error in validator.errors
    )
