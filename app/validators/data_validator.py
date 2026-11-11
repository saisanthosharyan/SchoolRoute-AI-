
from collections import defaultdict
from datetime import datetime

from app.database.connection import SessionLocal
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
)


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

    def validate_foreign_keys(self):
        """Check important relationships between records."""

        checks = [
            (
                "Student address zones",
                self.db.query(Student)
                .outerjoin(
                    AddressZone,
                    Student.address_zone_id == AddressZone.zone_id,
                )
                .filter(AddressZone.zone_id.is_(None))
                .count(),
            ),
            (
                "Guardian students",
                self.db.query(GuardianContact)
                .outerjoin(
                    Student,
                    GuardianContact.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None))
                .count(),
            ),
            (
                "Route buses",
                self.db.query(Route)
                .outerjoin(Bus, Route.bus_id == Bus.bus_id)
                .filter(Bus.bus_id.is_(None))
                .count(),
            ),
            (
                "Route drivers",
                self.db.query(Route)
                .outerjoin(Driver, Route.driver_id == Driver.driver_id)
                .filter(Driver.driver_id.is_(None))
                .count(),
            ),
            (
                "Route stop routes",
                self.db.query(RouteStop)
                .outerjoin(Route, RouteStop.route_id == Route.route_id)
                .filter(Route.route_id.is_(None))
                .count(),
            ),
            (
                "Route stop locations",
                self.db.query(RouteStop)
                .outerjoin(Stop, RouteStop.stop_id == Stop.stop_id)
                .filter(Stop.stop_id.is_(None))
                .count(),
            ),
            (
                "Assignment students",
                self.db.query(Assignment)
                .outerjoin(
                    Student,
                    Assignment.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None))
                .count(),
            ),
            (
                "Assignment routes",
                self.db.query(Assignment)
                .outerjoin(Route, Assignment.route_id == Route.route_id)
                .filter(Route.route_id.is_(None))
                .count(),
            ),
            (
                "Assignment stops",
                self.db.query(Assignment)
                .outerjoin(Stop, Assignment.stop_id == Stop.stop_id)
                .filter(Stop.stop_id.is_(None))
                .count(),
            ),
            (
                "Attendance students",
                self.db.query(AttendanceEvent)
                .outerjoin(
                    Student,
                    AttendanceEvent.student_id == Student.student_id,
                )
                .filter(Student.student_id.is_(None))
                .count(),
            ),
            (
                "Notification guardians",
                self.db.query(Notification)
                .outerjoin(
                    GuardianContact,
                    Notification.guardian_id == GuardianContact.guardian_id,
                )
                .filter(GuardianContact.guardian_id.is_(None))
                .count(),
            ),
        ]

        for name, invalid_count in checks:
            if invalid_count:
                self.error(f"{name}: {invalid_count} invalid references")
            else:
                self.passed()

    def validate_assignments(self):
        """Check assignment dates, student identity and route-stop links."""

        assignments = self.db.query(Assignment).all()

        for assignment in assignments:
            if (
                assignment.effective_to is not None
                and assignment.effective_to < assignment.effective_from
            ):
                self.error(
                    f"{assignment.assignment_id}: invalid effective dates"
                )
                continue

            route_stop_exists = (
                self.db.query(RouteStop)
                .filter(
                    RouteStop.route_id == assignment.route_id,
                    RouteStop.stop_id == assignment.stop_id,
                )
                .first()
            )

            if not route_stop_exists:
                self.error(
                    f"{assignment.assignment_id}: "
                    "assigned stop is not part of its route"
                )
                continue

            self.passed()

    def validate_capacity(self):
        """Check assigned student counts against bus capacity."""

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
        """Check accessible vehicle and stop requirements."""

        assignments = (
            self.db.query(Assignment)
            .filter(Assignment.assignment_status == "active")
            .all()
        )

        for assignment in assignments:
            student = self.db.get(Student, assignment.student_id)
            route = self.db.get(Route, assignment.route_id)
            stop = self.db.get(Stop, assignment.stop_id)

            if student is None or route is None or stop is None:
                continue

            bus = self.db.get(Bus, route.bus_id)

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
        """Check approved student addresses and pickup stops."""

        for student in self.db.query(Student).all():
            if not student.address_is_approved:
                self.error(
                    f"{student.student_id}: student address is not approved"
                )
            else:
                self.passed()

        for stop in self.db.query(Stop).all():
            if not stop.is_approved:
                self.error(
                    f"{stop.stop_id}: pickup stop is not approved"
                )
            else:
                self.passed()

    def validate_routes(self):
        """Check route sequence, travel times and stop windows."""

        routes = self.db.query(Route).all()

        for route in routes:
            route_stops = (
                self.db.query(RouteStop)
                .filter(RouteStop.route_id == route.route_id)
                .order_by(RouteStop.sequence_number)
                .all()
            )

            sequences = [
                route_stop.sequence_number
                for route_stop in route_stops
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

                    stop = self.db.get(Stop, route_stop.stop_id)

                    if stop is None:
                        continue

                    window_start = datetime.strptime(
                        stop.pickup_window_start,
                        "%H:%M",
                    ).time()

                    window_end = datetime.strptime(
                        stop.pickup_window_end,
                        "%H:%M",
                    ).time()

                    if not window_start <= arrival <= window_end:
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
        """Check attendance status and assignment consistency."""

        events = self.db.query(AttendanceEvent).all()

        for event in events:
            if event.event_timestamp is None:
                self.error(
                    f"{event.attendance_event_id}: missing timestamp"
                )
                continue

            if event.assignment_id:
                assignment = self.db.get(
                    Assignment,
                    event.assignment_id,
                )

                if assignment is None:
                    self.error(
                        f"{event.attendance_event_id}: "
                        "assignment does not exist"
                    )
                    continue

                if assignment.student_id != event.student_id:
                    self.error(
                        f"{event.attendance_event_id}: "
                        "student does not match assignment"
                    )
                    continue

            valid_statuses = {
                "pickup": {"present", "absent", "missed_pickup"},
                "dropoff": {"completed", "not_applicable"},
            }

            allowed = valid_statuses.get(event.event_type, set())

            if event.event_status not in allowed:
                self.error(
                    f"{event.attendance_event_id}: "
                    "invalid event type/status combination"
                )
            else:
                self.passed()

    def validate_notifications(self):
        """Check guardian, student and attendance relationships."""

        notifications = self.db.query(Notification).all()

        for notification in notifications:
            guardian = self.db.get(
                GuardianContact,
                notification.guardian_id,
            )

            if guardian is None:
                self.error(
                    f"{notification.notification_id}: guardian missing"
                )
                continue

            if guardian.student_id != notification.student_id:
                self.error(
                    f"{notification.notification_id}: "
                    "guardian belongs to another student"
                )
                continue

            if notification.channel != guardian.preferred_channel:
                self.error(
                    f"{notification.notification_id}: "
                    "notification channel differs from preference"
                )
                continue

            if notification.notification_status == "sent":
                if not guardian.is_valid:
                    self.error(
                        f"{notification.notification_id}: "
                        "sent to invalid guardian contact"
                    )
                    continue

                if notification.sent_at is None:
                    self.error(
                        f"{notification.notification_id}: "
                        "sent notification has no sent timestamp"
                    )
                    continue

            if notification.notification_status == "failed":
                if not notification.failure_reason:
                    self.error(
                        f"{notification.notification_id}: "
                        "failed notification has no failure reason"
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

        return {
            "checks_passed": self.checks_passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "PASSED" if not self.errors else "FAILED",
        }


def main():
    db = SessionLocal()

    try:
        validator = DataValidator(db)
        report = validator.run()

        print("\nSCHOOLROUTE AI DATA VALIDATION")
        print("=" * 42)
        print(f"Status:         {report['status']}")
        print(f"Checks passed:  {report['checks_passed']}")
        print(f"Errors:         {report['error_count']}")
        print(f"Warnings:       {report['warning_count']}")

        if report["errors"]:
            print("\nVALIDATION ERRORS")
            print("-" * 42)

            for error in report["errors"]:
                print(f"[ERROR] {error}")

        if report["warnings"]:
            print("\nVALIDATION WARNINGS")
            print("-" * 42)

            for warning in report["warnings"]:
                print(f"[WARNING] {warning}")

        print("=" * 42)

        if report["status"] == "FAILED":
            raise SystemExit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
