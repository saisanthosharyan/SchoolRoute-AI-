from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import (
    Assignment,
    Bus,
    BusCapacityEvent,
    Route,
    RouteDisruptionEvent,
)


class EventServiceError(Exception):
    """Raised when an operational event violates business rules."""


def change_bus_capacity(
    db: Session,
    bus_id: str,
    new_capacity: int,
    effective_from: date,
    reason: str,
) -> BusCapacityEvent:
    """
    Record a bus capacity change and update its current capacity.

    The caller owns the transaction and must commit or roll it back.
    Historical capacity changes are never deleted.
    """

    if not isinstance(new_capacity, int) or isinstance(new_capacity, bool):
        raise EventServiceError("Capacity must be an integer.")

    if new_capacity <= 0:
        raise EventServiceError("Capacity must be greater than zero.")

    if not isinstance(effective_from, date) or isinstance(effective_from, datetime):
        raise EventServiceError("A valid effective date is required.")

    reason = reason.strip() if reason else ""

    if not reason:
        raise EventServiceError("A reason for the capacity change is required.")

    bus = db.get(Bus, bus_id)

    if bus is None:
        raise EventServiceError(f"Bus not found: {bus_id}")

    if effective_from <= bus.capacity_effective_from:
        raise EventServiceError(
            "The new effective date must be later than the current "
            "capacity effective date."
        )

    if bus.capacity_effective_to is not None:
        if effective_from <= bus.capacity_effective_to:
            raise EventServiceError(
                "The new effective date overlaps the existing capacity period."
            )

    # Do not reduce capacity below active student assignments.
    assigned_count = db.scalar(
        select(func.count(Assignment.assignment_id))
        .join(Route, Assignment.route_id == Route.route_id)
        .where(
            Route.bus_id == bus_id,
            Assignment.assignment_status == "active",
            Assignment.effective_from <= effective_from,
            (
                Assignment.effective_to.is_(None)
                | (Assignment.effective_to >= effective_from)
            ),
        )
    ) or 0

    if new_capacity < assigned_count:
        raise EventServiceError(
            f"Capacity {new_capacity} is below the "
            f"{assigned_count} active student assignments."
        )

    previous_capacity = bus.capacity

    if new_capacity == previous_capacity:
        raise EventServiceError("New capacity is unchanged.")

    event = BusCapacityEvent(
        capacity_event_id=f"CAP-{uuid4().hex[:24].upper()}",
        bus_id=bus.bus_id,
        previous_capacity=previous_capacity,
        new_capacity=new_capacity,
        effective_from=effective_from,
        reason=reason,
        recorded_at=datetime.now(timezone.utc),
    )

    # Close the previous capacity period and establish the new one.
    bus.capacity_effective_to = effective_from - timedelta(days=1)
    bus.capacity = new_capacity
    bus.capacity_effective_from = effective_from
    bus.capacity_effective_to = None

    db.add(event)
    db.flush()

    return event


def report_route_disruption(
    db: Session,
    route_id: str,
    disruption_type: str,
    description: str,
    started_at: datetime | None = None,
    severity: str = "medium",
) -> RouteDisruptionEvent:
    """Record a route disruption and mark the route as disrupted."""

    allowed_types = {
        "traffic",
        "weather",
        "vehicle_breakdown",
        "road_closure",
        "driver_unavailable",
        "safety_incident",
        "other",
    }

    allowed_severities = {"low", "medium", "high", "critical"}

    severity = severity.strip().lower() if severity else ""

    if severity not in allowed_severities:
        raise EventServiceError("Unsupported disruption severity.")

    if disruption_type not in allowed_types:
        raise EventServiceError("Unsupported disruption type.")

    description = description.strip() if description else ""

    if not description:
        raise EventServiceError("A disruption description is required.")

    route = db.get(Route, route_id)

    if route is None:
        raise EventServiceError(f"Route not found: {route_id}")

    if route.route_status not in {"active", "disrupted"}:
        raise EventServiceError(
            "Only active or already-disrupted routes can receive a new disruption."
        )

    if route.route_status == "disrupted":
        existing_active = db.scalar(
            select(func.count(RouteDisruptionEvent.disruption_event_id)).where(
                RouteDisruptionEvent.route_id == route_id,
                RouteDisruptionEvent.status == "active",
            )
        ) or 0

        if existing_active == 0:
            raise EventServiceError(
                "Route is marked disrupted but has no active disruption event."
            )

    event_time = started_at or datetime.now(timezone.utc)

    if event_time.tzinfo is None or event_time.utcoffset() is None:
        raise EventServiceError("Disruption timestamps must include a timezone.")

    event = RouteDisruptionEvent(
        disruption_event_id=f"DIS-{uuid4().hex[:24].upper()}",
        route_id=route.route_id,
        disruption_type=disruption_type,
        severity=severity,
        description=description,
        started_at=event_time,
        status="active",
    )

    route.route_status = "disrupted"

    db.add(event)
    db.flush()

    return event


def resolve_route_disruption(
    db: Session,
    disruption_event_id: str,
    resolution_notes: str,
) -> RouteDisruptionEvent:
    """Resolve a disruption without deleting its historical event."""

    resolution_notes = resolution_notes.strip() if resolution_notes else ""

    if not resolution_notes:
        raise EventServiceError("Resolution notes are required.")

    event = db.get(RouteDisruptionEvent, disruption_event_id)

    if event is None:
        raise EventServiceError(
            f"Disruption event not found: {disruption_event_id}"
        )

    if event.status != "active":
        raise EventServiceError("Only active disruptions can be resolved.")

    now = datetime.now(timezone.utc)

    event.status = "resolved"
    event.resolved_at = now
    event.resolution_notes = resolution_notes

    db.flush()

    # Restore the route only when no other active disruptions remain.
    remaining_disruptions = db.scalar(
        select(func.count(RouteDisruptionEvent.disruption_event_id)).where(
            RouteDisruptionEvent.route_id == event.route_id,
            RouteDisruptionEvent.status == "active",
        )
    ) or 0

    route = db.get(Route, event.route_id)

    if remaining_disruptions == 0 and route.route_status == "disrupted":
        if route.effective_to is None or route.effective_to >= now.date():
            route.route_status = "active"

    db.flush()

    return event
