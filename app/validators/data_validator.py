
import argparse
from collections import defaultdict
from datetime import datetime

from app.database.connection import SessionLocal, FullSessionLocal
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
    BusCapacityEvent,
    RouteDisruptionEvent,
)


BATCH_SIZE = 10_000


class DataValidator:
    """Validate SchoolRoute AI relational and operational data."""

    def __init__(self, db):
        self.db = db
        self.errors = []
        self.warnings = []
        self.checks_passed = 0

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def passed(self):
        self.checks_passed += 1

    def count_invalid(self, query):
        """Count invalid records without loading them into memory."""
        return query.count()

    def validate_foreign_keys(self):
        """Validate all important parent-child relationships."""

        checks = [
            (
                "Student address zones",
                self.db.query(Student)
                .outerjoin(
                    AddressZone,
                    Student.address_zone_id == AddressZone.zone_id,
                )
                .filter(AddressZone.zone_id.is_(None)),
            ),
            (
                "Guardian students",
                self.db.query(GuardianContact)
                .outerjoin(
                    Student,
                    GuardianContact.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None)),
            ),
            (
                "Stop address zones",
                self.db.query(Stop)
                .outerjoin(
                    AddressZone,
                    Stop.address_zone_id == AddressZone.zone_id,
                )
                .filter(AddressZone.zone_id.is_(None)),
            ),
            (
                "Route buses",
                self.db.query(Route)
                .outerjoin(Bus, Route.bus_id == Bus.bus_id)
                .filter(Bus.bus_id.is_(None)),
            ),
            (
                "Route drivers",
                self.db.query(Route)
                .outerjoin(Driver, Route.driver_id == Driver.driver_id)
                .filter(Driver.driver_id.is_(None)),
            ),
            (
                "Route stop routes",
                self.db.query(RouteStop)
                .outerjoin(Route, RouteStop.route_id == Route.route_id)
                .filter(Route.route_id.is_(None)),
            ),
            (
                "Route stop locations",
                self.db.query(RouteStop)
                .outerjoin(Stop, RouteStop.stop_id == Stop.stop_id)
                .filter(Stop.stop_id.is_(None)),
            ),
            (
                "Assignment students",
                self.db.query(Assignment)
                .outerjoin(
                    Student,
                    Assignment.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None)),
            ),
            (
                "Assignment routes",
                self.db.query(Assignment)
                .outerjoin(Route, Assignment.route_id == Route.route_id)
                .filter(Route.route_id.is_(None)),
            ),
            (
                "Assignment stops",
                self.db.query(Assignment)
                .outerjoin(Stop, Assignment.stop_id == Stop.stop_id)
                .filter(Stop.stop_id.is_(None)),
            ),
            (
                "Attendance students",
                self.db.query(AttendanceEvent)
                .outerjoin(
                    Student,
                    AttendanceEvent.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None)),
            ),
            (
                "Attendance assignments",
                self.db.query(AttendanceEvent)
                .outerjoin(
                    Assignment,
                    AttendanceEvent.assignment_id == Assignment.assignment_id,
                )
                .filter(
                    AttendanceEvent.assignment_id.isnot(None),
                    Assignment.assignment_id.is_(None),
                ),
            ),
            (
                "Notification students",
                self.db.query(Notification)
                .outerjoin(
                    Student,
                    Notification.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None)),
            ),
            (
                "Notification guardians",
                self.db.query(Notification)
                .outerjoin(
                    GuardianContact,
                    Notification.guardian_id == GuardianContact.guardian_id,
                )
                .filter(GuardianContact.guardian_id.is_(None)),
            ),
            (
                "Notification attendance events",
                self.db.query(Notification)
                .outerjoin(
                    AttendanceEvent,
                    Notification.attendance_event_id
                    == AttendanceEvent.attendance_event_id,
                )
                .filter(
                    Notification.attendance_event_id.isnot(None),
                    AttendanceEvent.attendance_event_id.is_(None),
                ),
            ),
            (
                "Capacity event buses",
                self.db.query(BusCapacityEvent)
                .outerjoin(
                    Bus,
                    BusCapacityEvent.bus_id == Bus.bus_id,
                )
                .filter(Bus.bus_id.is_(None)),
            ),
            (
                "Disruption event routes",
                self.db.query(RouteDisruptionEvent)
                .outerjoin(
                    Route,
                    RouteDisruptionEvent.route_id == Route.route_id,
                )
                .filter(Route.route_id.is_(None)),
            ),
            (
                "Disruption affected stops",
                self.db.query(RouteDisruptionEvent)
                .outerjoin(
                    Stop,
                    RouteDisruptionEvent.affected_stop_id == Stop.stop_id,
                )
                .filter(
                    RouteDisruptionEvent.affected_stop_id.isnot(None),
                    Stop.stop_id.is_(None),
                ),
            ),
        ]

        for name, query in checks:
            invalid_count = self.count_invalid(query)

            if invalid_count:
                self.error(
                    f"{name}: {invalid_count} invalid references"
                )
            else:
                self.passed()

    def validate_assignments(self):
        """Check assignment dates and route-stop membership."""

        route_stop_pairs = {
            (route_id, stop_id)
            for route_id, stop_id in self.db.query(
                RouteStop.route_id,
                RouteStop.stop_id,
            ).all()
        }

        assignments = self.db.query(Assignment).yield_per(BATCH_SIZE)

        for assignment in assignments:
            if (
                assignment.effective_to is not None
                and assignment.effective_to < assignment.effective_from
            ):
                self.error(
                    f"{assignment.assignment_id}: invalid effective dates"
                )
                continue

            if (
                assignment.route_id,
                assignment.stop_id,
            ) not in route_stop_pairs:
                self.error(
                    f"{assignment.assignment_id}: "
                    "assigned stop is not part of its route"
                )
                continue

            self.passed()

    def validate_capacity(self):
        """Check active assignment counts against current bus capacity."""

        assignments = (
            self.db.query(Assignment)
            .filter(Assignment.assignment_status == "active")
            .all()
        )

        route_by_id = {
            route.route_id: route
            for route in self.db.query(Route).all()
        }

        bus_counts = defaultdict(int)

        for assignment in assignments:
            route = route_by_id.get(assignment.route_id)

            if route is not None:
                bus_counts[route.bus_id] += 1

        buses = {
            bus.bus_id: bus
            for bus in self.db.query(Bus).all()
        }

        for bus_id, assigned_count in bus_counts.items():
            bus = buses.get(bus_id)

            if bus is None:
                continue

            if assigned_count > bus.capacity:
                self.error(
                    f"{bus_id}: capacity exceeded "
                    f"({assigned_count}/{bus.capacity})"
                )
            else:
                self.passed()

    def validate_accessibility(self):
        """Check accessible bus and stop requirements."""

        assignments = (
            self.db.query(Assignment)
            .filter(Assignment.assignment_status == "active")
            .all()
        )

        students = {
            item.student_id: item
            for item in self.db.query(Student).all()
        }

        routes = {
            item.route_id: item
            for item in self.db.query(Route).all()
        }

        stops = {
            item.stop_id: item
            for item in self.db.query(Stop).all()
        }

        buses = {
            item.bus_id: item
            for item in self.db.query(Bus).all()
        }

        for assignment in assignments:
            student = students.get(assignment.student_id)
            route = routes.get(assignment.route_id)
            stop = stops.get(assignment.stop_id)

            if student is None or route is None or stop is None:
                continue

            bus = buses.get(route.bus_id)

            if student.requires_accessible_vehicle:
                if bus is None or not bus.is_accessible:
                    self.error(
                        f"{assignment.assignment_id}: "
                        "student requires an accessible bus"
                    )
                    continue

                if not stop.is_accessible:
                    self.error(
                        f"{assignment.assignment_id}: "
                        "student requires an accessible stop"
                    )
                    continue

            self.passed()

    def validate_approvals(self):
        """Check student address and pickup stop approvals."""

        for student in self.db.query(Student).yield_per(BATCH_SIZE):
            if not student.address_is_approved:
                self.error(
                    f"{student.student_id}: student address is not approved"
                )
            else:
                self.passed()

        for stop in self.db.query(Stop).yield_per(BATCH_SIZE):
            if not stop.is_approved:
                self.error(
                    f"{stop.stop_id}: pickup stop is not approved"
                )
            else:
                self.passed()

    def validate_routes(self):
        """Check route sequences, duration and pickup windows."""

        stops = {
            stop.stop_id: stop
            for stop in self.db.query(Stop).all()
        }

        routes = self.db.query(Route).all()

        for route in routes:
            route_stops = (
                self.db.query(RouteStop)
                .filter(RouteStop.route_id == route.route_id)
                .order_by(RouteStop.sequence_number)
                .all()
            )

            if (
                not route_stops
                and route.route_status in {"active", "disrupted"}
            ):
                self.error(
                    f"{route.route_id}: active route has no stops"
                )
                continue

            sequences = [
                item.sequence_number
                for item in route_stops
            ]

            if sequences != list(range(1, len(sequences) + 1)):
                self.error(
                    f"{route.route_id}: invalid stop sequence"
                )
            else:
                self.passed()

            total_travel_time = sum(
                item.travel_time_from_previous_minutes
                for item in route_stops
            )

            if total_travel_time > route.estimated_duration_minutes:
                self.error(
                    f"{route.route_id}: travel time exceeds "
                    "estimated route duration"
                )
            else:
                self.passed()

            for route_stop in route_stops:
                try:
                    arrival = datetime.strptime(
                        route_stop.estimated_arrival,
                        "%H:%M",
                    ).time()

                    stop = stops.get(route_stop.stop_id)

                    if stop is None:
                        self.error(
                            f"{route.route_id}: missing stop "
                            f"{route_stop.stop_id}"
                        )
                        continue

                    window_start = datetime.strptime(
                        stop.pickup_window_start,
                        "%H:%M",
                    ).time()

                    window_end = datetime.strptime(
                        stop.pickup_window_end,
                        "%H:%M",
                    ).time()

                    if window_start > window_end:
                        self.error(
                            f"{stop.stop_id}: invalid pickup window"
                        )
                    elif not window_start <= arrival <= window_end:
                        self.error(
                            f"{route.route_id}: arrival outside "
                            f"pickup window at {stop.stop_id}"
                        )
                    else:
                        self.passed()

                except (ValueError, TypeError):
                    self.error(
                        f"{route.route_id}: invalid stop time format"
                    )

    def validate_attendance(self):
        """
        Stream attendance records in batches.

        Avoid loading millions of ORM objects into memory.
        """

        valid_statuses = {
            "pickup": {"present", "absent", "missed_pickup"},
            "dropoff": {"completed", "not_applicable"},
        }

        query = (
            self.db.query(
                AttendanceEvent,
                Assignment.student_id.label("assignment_student_id"),
            )
            .outerjoin(
                Assignment,
                AttendanceEvent.assignment_id == Assignment.assignment_id,
            )
            .yield_per(BATCH_SIZE)
        )

        for event, assignment_student_id in query:
            if event.event_timestamp is None:
                self.error(
                    f"{event.attendance_event_id}: missing timestamp"
                )
                continue

            if (
                event.assignment_id
                and assignment_student_id is None
            ):
                self.error(
                    f"{event.attendance_event_id}: "
                    "assignment does not exist"
                )
                continue

            if (
                event.assignment_id
                and assignment_student_id != event.student_id
            ):
                self.error(
                    f"{event.attendance_event_id}: "
                    "student does not match assignment"
                )
                continue

            allowed = valid_statuses.get(event.event_type, set())

            if event.event_status not in allowed:
                self.error(
                    f"{event.attendance_event_id}: "
                    "invalid event type/status combination"
                )
            else:
                self.passed()

    def validate_notifications(self):
        """Validate notification relationships and lifecycle states."""

        valid_statuses = {"pending", "sent", "failed"}

        query = (
            self.db.query(
                Notification,
                GuardianContact.student_id.label("guardian_student_id"),
                GuardianContact.preferred_channel.label(
                    "guardian_preferred_channel"
                ),
                GuardianContact.is_valid.label("guardian_is_valid"),
                AttendanceEvent.student_id.label("event_student_id"),
            )
            .outerjoin(
                GuardianContact,
                Notification.guardian_id == GuardianContact.guardian_id,
            )
            .outerjoin(
                AttendanceEvent,
                Notification.attendance_event_id
                == AttendanceEvent.attendance_event_id,
            )
            .yield_per(BATCH_SIZE)
        )

        for (
            notification,
            guardian_student_id,
            guardian_preferred_channel,
            guardian_is_valid,
            event_student_id,
        ) in query:

            notification_id = notification.notification_id

            if guardian_student_id is None:
                self.error(
                    f"{notification_id}: guardian missing"
                )
                continue

            if guardian_student_id != notification.student_id:
                self.error(
                    f"{notification_id}: "
                    "guardian belongs to another student"
                )
                continue

            if notification.channel != guardian_preferred_channel:
                self.error(
                    f"{notification_id}: "
                    "notification channel differs from preference"
                )
                continue

            if (
                notification.attendance_event_id
                and event_student_id is None
            ):
                self.error(
                    f"{notification_id}: attendance event missing"
                )
                continue

            if (
                notification.attendance_event_id
                and event_student_id != notification.student_id
            ):
                self.error(
                    f"{notification_id}: "
                    "attendance event belongs to another student"
                )
                continue

            if notification.notification_status not in valid_statuses:
                self.error(
                    f"{notification_id}: "
                    f"invalid notification status "
                    f"'{notification.notification_status}'"
                )
                continue

            if notification.notification_status == "sent":
                if not guardian_is_valid:
                    self.error(
                        f"{notification_id}: "
                        "sent to invalid guardian contact"
                    )
                    continue

                if notification.sent_at is None:
                    self.error(
                        f"{notification_id}: "
                        "sent notification has no sent timestamp"
                    )
                    continue

                if notification.failure_reason:
                    self.error(
                        f"{notification_id}: "
                        "sent notification has a failure reason"
                    )
                    continue

            elif notification.notification_status == "failed":
                if (
                    notification.failure_reason is None
                    or not notification.failure_reason.strip()
                ):
                    self.error(
                        f"{notification_id}: "
                        "failed notification has no failure reason"
                    )
                    continue

                if notification.sent_at is not None:
                    self.error(
                        f"{notification_id}: "
                        "failed notification has a sent timestamp"
                    )
                    continue

            elif notification.notification_status == "pending":
                if notification.sent_at is not None:
                    self.error(
                        f"{notification_id}: "
                        "pending notification has a sent timestamp"
                    )
                    continue

                if notification.failure_reason:
                    self.error(
                        f"{notification_id}: "
                        "pending notification has a failure reason"
                    )
                    continue

            self.passed()


    def validate_event_history(self):
        """Validate bus capacity and route disruption event history."""

        capacity_events = (
            self.db.query(BusCapacityEvent)
            .yield_per(BATCH_SIZE)
        )

        for event in capacity_events:
            if event.previous_capacity <= 0 or event.new_capacity <= 0:
                self.error(
                    f"{event.capacity_event_id}: "
                    "capacity must be positive"
                )
            elif event.previous_capacity == event.new_capacity:
                self.error(
                    f"{event.capacity_event_id}: "
                    "capacity change has identical values"
                )
            elif event.reason is None or not event.reason.strip():
                self.error(
                    f"{event.capacity_event_id}: missing change reason"
                )
            else:
                self.passed()

        valid_disruption_statuses = {
            "active",
            "resolved",
            "cancelled",
        }

        disruptions = (
            self.db.query(RouteDisruptionEvent)
            .yield_per(BATCH_SIZE)
        )

        for event in disruptions:
            event_id = event.disruption_event_id

            if event.status not in valid_disruption_statuses:
                self.error(
                    f"{event_id}: "
                    f"invalid disruption status '{event.status}'"
                )
                continue

            if event.resolved_at and event.resolved_at < event.started_at:
                self.error(
                    f"{event_id}: "
                    "resolution precedes disruption start"
                )
                continue

            if event.status == "resolved":
                if (
                    event.resolved_at is None
                    or event.resolution_notes is None
                    or not event.resolution_notes.strip()
                ):
                    self.error(
                        f"{event_id}: "
                        "resolved event is missing resolution details"
                    )
                    continue

            elif event.status == "active":
                if event.resolved_at is not None:
                    self.error(
                        f"{event_id}: "
                        "active disruption has a resolution timestamp"
                    )
                    continue

            self.passed()


    def run(self):
        """Execute all validation groups."""

        self.validate_foreign_keys()
        self.validate_assignments()
        self.validate_capacity()
        self.validate_accessibility()
        self.validate_approvals()
        self.validate_routes()
        self.validate_attendance()
        self.validate_notifications()
        self.validate_event_history()

        return {
            "checks_passed": self.checks_passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "PASSED" if not self.errors else "FAILED",
        }


def main():
    parser = argparse.ArgumentParser(
        description="Validate SchoolRoute AI database."
    )

    parser.add_argument(
        "--database",
        choices=["starter", "full"],
        default="starter",
        help="Select the database to validate.",
    )

    args = parser.parse_args()

    session_factory = (
        FullSessionLocal
        if args.database == "full"
        else SessionLocal
    )

    db = session_factory()

    try:
        print("\nSCHOOLROUTE AI DATA VALIDATION")
        print("=" * 50)
        print(f"Database: {args.database}")
        print(f"Batch size: {BATCH_SIZE:,}")
        print("Running validation checks...\n")

        validator = DataValidator(db)
        report = validator.run()

        print("\nVALIDATION SUMMARY")
        print("=" * 50)
        print(f"Database:       {args.database}")
        print(f"Status:         {report['status']}")
        print(f"Checks passed:  {report['checks_passed']:,}")
        print(f"Errors:         {report['error_count']:,}")
        print(f"Warnings:       {report['warning_count']:,}")

        if report["errors"]:
            print("\nVALIDATION ERRORS")
            print("-" * 50)

            for error in report["errors"]:
                print(f"[ERROR] {error}")

        if report["warnings"]:
            print("\nVALIDATION WARNINGS")
            print("-" * 50)

            for warning in report["warnings"]:
                print(f"[WARNING] {warning}")

        print("=" * 50)

        if report["status"] == "FAILED":
            raise SystemExit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
