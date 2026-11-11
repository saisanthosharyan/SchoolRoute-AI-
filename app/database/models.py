
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


# ============================================================
# 1. ADDRESS ZONE
# ============================================================

class AddressZone(Base):
    __tablename__ = "address_zones"

    zone_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    students: Mapped[list["Student"]] = relationship(back_populates="address_zone")
    stops: Mapped[list["Stop"]] = relationship(back_populates="address_zone")


# ============================================================
# 2. STUDENT
# ============================================================

class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)

    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    address_zone_id: Mapped[str] = mapped_column(
        ForeignKey("address_zones.zone_id", ondelete="RESTRICT"),
        nullable=False,
    )

    synthetic_address: Mapped[str] = mapped_column(String(250), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    requires_accessible_vehicle: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    address_is_approved: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    enrollment_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    address_zone: Mapped["AddressZone"] = relationship(back_populates="students")
    guardian_contacts: Mapped[list["GuardianContact"]] = relationship(
        back_populates="student"
    )
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="student")
    attendance_events: Mapped[list["AttendanceEvent"]] = relationship(
        back_populates="student"
    )

    __table_args__ = (
        CheckConstraint("grade BETWEEN 1 AND 12", name="ck_student_grade"),
        CheckConstraint(
            "enrollment_status IN ('active', 'inactive', 'graduated', 'suspended')",
            name="ck_student_enrollment_status",
        ),
        Index("ix_student_zone", "address_zone_id"),
    )


# ============================================================
# 3. GUARDIAN CONTACT
# ============================================================

class GuardianContact(Base):
    __tablename__ = "guardian_contacts"

    guardian_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="RESTRICT"),
        nullable=False,
    )

    guardian_name: Mapped[str] = mapped_column(String(120), nullable=False)
    synthetic_phone: Mapped[str] = mapped_column(String(25), nullable=False)
    synthetic_email: Mapped[str] = mapped_column(String(150), nullable=False)

    relationship_type: Mapped[str] = mapped_column(String(30), nullable=False)
    preferred_channel: Mapped[str] = mapped_column(
        String(20), default="sms", nullable=False
    )

    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student"] = relationship(back_populates="guardian_contacts")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="guardian"
    )

    __table_args__ = (
        CheckConstraint(
            "preferred_channel IN ('sms', 'email', 'push')",
            name="ck_guardian_channel",
        ),
        Index("ix_guardian_student", "student_id"),
    )


# ============================================================
# 4. STOP
# ============================================================

class Stop(Base):
    __tablename__ = "stops"

    stop_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    stop_name: Mapped[str] = mapped_column(String(120), nullable=False)

    address_zone_id: Mapped[str] = mapped_column(
        ForeignKey("address_zones.zone_id", ondelete="RESTRICT"),
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    pickup_window_start: Mapped[str] = mapped_column(String(5), nullable=False)
    pickup_window_end: Mapped[str] = mapped_column(String(5), nullable=False)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    address_zone: Mapped["AddressZone"] = relationship(back_populates="stops")
    route_stops: Mapped[list["RouteStop"]] = relationship(back_populates="stop")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="stop")

    __table_args__ = (
        Index("ix_stop_zone", "address_zone_id"),
    )


# ============================================================
# 5. BUS
# ============================================================

class Bus(Base):
    __tablename__ = "buses"

    bus_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    registration_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    operational_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    capacity_effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    capacity_effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    routes: Mapped[list["Route"]] = relationship(back_populates="bus")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_bus_capacity"),
        CheckConstraint(
            "operational_status IN ('active', 'maintenance', 'retired')",
            name="ck_bus_status",
        ),
    )


# ============================================================
# 6. DRIVER
# ============================================================

class Driver(Base):
    __tablename__ = "drivers"

    driver_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    driver_name: Mapped[str] = mapped_column(String(120), nullable=False)

    synthetic_license_number: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True
    )

    license_valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    routes: Mapped[list["Route"]] = relationship(back_populates="driver")


# ============================================================
# 7. ROUTE
# ============================================================

class Route(Base):
    __tablename__ = "routes"

    route_id: Mapped[str] = mapped_column(String(30), primary_key=True)

    bus_id: Mapped[str] = mapped_column(
        ForeignKey("buses.bus_id", ondelete="RESTRICT"),
        nullable=False,
    )

    driver_id: Mapped[str] = mapped_column(
        ForeignKey("drivers.driver_id", ondelete="RESTRICT"),
        nullable=False,
    )

    route_name: Mapped[str] = mapped_column(String(120), nullable=False)
    school_year: Mapped[int] = mapped_column(Integer, nullable=False)

    estimated_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    route_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    bus: Mapped["Bus"] = relationship(back_populates="routes")
    driver: Mapped["Driver"] = relationship(back_populates="routes")

    route_stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route",
        order_by="RouteStop.sequence_number",
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="route"
    )

    __table_args__ = (
        CheckConstraint(
            "route_status IN ('draft', 'active', 'disrupted', 'retired')",
            name="ck_route_status",
        ),
        CheckConstraint(
            "estimated_duration_minutes > 0",
            name="ck_route_duration",
        ),
        CheckConstraint("total_distance_km >= 0", name="ck_route_distance"),
        Index("ix_route_bus", "bus_id"),
    )


# ============================================================
# 8. ROUTE STOP (BRIDGE ENTITY)
# ============================================================

class RouteStop(Base):
    __tablename__ = "route_stops"

    route_stop_id: Mapped[str] = mapped_column(String(40), primary_key=True)

    route_id: Mapped[str] = mapped_column(
        ForeignKey("routes.route_id", ondelete="RESTRICT"),
        nullable=False,
    )

    stop_id: Mapped[str] = mapped_column(
        ForeignKey("stops.stop_id", ondelete="RESTRICT"),
        nullable=False,
    )

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    estimated_arrival: Mapped[str] = mapped_column(String(5), nullable=False)
    travel_time_from_previous_minutes: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    route: Mapped["Route"] = relationship(back_populates="route_stops")
    stop: Mapped["Stop"] = relationship(back_populates="route_stops")

    __table_args__ = (
        UniqueConstraint(
            "route_id", "sequence_number",
            name="uq_route_stop_sequence",
        ),
        UniqueConstraint(
            "route_id", "stop_id",
            name="uq_route_stop_pair",
        ),
        CheckConstraint("sequence_number > 0", name="ck_stop_sequence"),
        CheckConstraint(
            "travel_time_from_previous_minutes >= 0",
            name="ck_stop_travel_time",
        ),
    )


# ============================================================
# 9. ASSIGNMENT
# ============================================================

class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="RESTRICT"),
        nullable=False,
    )

    route_id: Mapped[str] = mapped_column(
        ForeignKey("routes.route_id", ondelete="RESTRICT"),
        nullable=False,
    )

    stop_id: Mapped[str] = mapped_column(
        ForeignKey("stops.stop_id", ondelete="RESTRICT"),
        nullable=False,
    )

    school_year: Mapped[int] = mapped_column(Integer, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    assignment_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="assignments")
    route: Mapped["Route"] = relationship(back_populates="assignments")
    stop: Mapped["Stop"] = relationship(back_populates="assignments")

    attendance_events: Mapped[list["AttendanceEvent"]] = relationship(
        back_populates="assignment"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id", "school_year",
            name="uq_student_school_year_assignment",
        ),
        CheckConstraint(
            "assignment_status IN ('active', 'suspended', 'cancelled', 'completed')",
            name="ck_assignment_status",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_assignment_dates",
        ),
        Index("ix_assignment_route", "route_id"),
    )


# ============================================================
# 10. ATTENDANCE EVENT
# ============================================================

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    attendance_event_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )

    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="RESTRICT"),
        nullable=False,
    )

    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_id", ondelete="RESTRICT"),
        nullable=True,
    )

    service_date: Mapped[date] = mapped_column(Date, nullable=False)

    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event_status: Mapped[str] = mapped_column(String(20), nullable=False)

    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="attendance_events")
    assignment: Mapped["Assignment | None"] = relationship(
        back_populates="attendance_events"
    )

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="attendance_event"
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('pickup', 'dropoff')",
            name="ck_attendance_event_type",
        ),
        CheckConstraint(
            "event_status IN ('present', 'absent', 'missed_pickup', "
            "'completed', 'not_applicable')",
            name="ck_attendance_event_status",
        ),
        Index("ix_attendance_date", "service_date"),
        Index("ix_attendance_student_date", "student_id", "service_date"),
    )


# ============================================================
# 11. NOTIFICATION
# ============================================================

class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(String(30), primary_key=True)

    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="RESTRICT"),
        nullable=False,
    )

    guardian_id: Mapped[str] = mapped_column(
        ForeignKey("guardian_contacts.guardian_id", ondelete="RESTRICT"),
        nullable=False,
    )

    attendance_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("attendance_events.attendance_event_id", ondelete="RESTRICT"),
        nullable=True,
    )

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(40), nullable=False)

    notification_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    synthetic_recipient: Mapped[str] = mapped_column(String(150), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    guardian: Mapped["GuardianContact"] = relationship(
        back_populates="notifications"
    )

    attendance_event: Mapped["AttendanceEvent | None"] = relationship(
        back_populates="notifications"
    )

    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'email', 'push')",
            name="ck_notification_channel",
        ),
        CheckConstraint(
            "notification_status IN ('pending', 'sent', 'failed')",
            name="ck_notification_status",
        ),
        Index("ix_notification_student", "student_id"),
    )
