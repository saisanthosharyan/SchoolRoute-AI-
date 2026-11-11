import json
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings, PROJECT_ROOT
from app.database.models import (
    Bus,
    Route,
    RouteStop,
    Assignment,
    Student,
    GuardianContact,
    Notification,
)


def main():
    # Resolve the clean source database.
    database_url = make_url(settings.DATABASE_URL)
    source_path = Path(database_url.database)

    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    source_path = source_path.resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Clean database not found: {source_path}")

    # Create a separate SQLite copy using SQLite's backup API.
    anomaly_dir = PROJECT_ROOT / "data" / "generated"
    anomaly_dir.mkdir(parents=True, exist_ok=True)

    anomaly_path = anomaly_dir / "schoolroute_anomalies.db"

    if anomaly_path.exists():
        anomaly_path.unlink()

    with sqlite3.connect(str(source_path)) as source_conn:
        with sqlite3.connect(str(anomaly_path)) as target_conn:
            source_conn.backup(target_conn)

    engine = create_engine(
        f"sqlite:///{anomaly_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()

    anomalies = []

    try:
        # 1. Bus capacity exceeded.
        buses = db.query(Bus).all()
        capacity_result = None

        for bus in buses:
            assignment_count = (
                db.query(Assignment)
                .join(Route, Assignment.route_id == Route.route_id)
                .filter(
                    Route.bus_id == bus.bus_id,
                    Assignment.assignment_status == "active",
                )
                .count()
            )

            if assignment_count > 1:
                bus.capacity = assignment_count - 1
                capacity_result = {
                    "anomaly_id": "ANOM-001",
                    "issue_type": "bus_capacity_exceeded",
                    "affected_record_type": "Bus",
                    "affected_record_id": bus.bus_id,
                    "expected_detection": (
                        f"Active assignments ({assignment_count}) exceed "
                        f"bus capacity ({bus.capacity})."
                    ),
                }
                break

        if capacity_result is None:
            raise RuntimeError("Could not find a bus suitable for capacity anomaly.")

        anomalies.append(capacity_result)

        # 2. Accessible student assigned to a non-accessible bus.
        accessible_students = (
            db.query(Student)
            .filter(Student.requires_accessible_vehicle.is_(True))
            .all()
        )

        accessibility_result = None

        for student in accessible_students:
            assignment = (
                db.query(Assignment)
                .filter(
                    Assignment.student_id == student.student_id,
                    Assignment.assignment_status == "active",
                )
                .first()
            )

            if assignment is None:
                continue

            route = db.query(Route).filter(
                Route.route_id == assignment.route_id
            ).first()

            if route is None:
                continue

            bus = db.query(Bus).filter(Bus.bus_id == route.bus_id).first()

            if bus is not None:
                bus.is_accessible = False
                accessibility_result = {
                    "anomaly_id": "ANOM-002",
                    "issue_type": "incompatible_accessibility_assignment",
                    "affected_record_type": "Assignment",
                    "affected_record_id": assignment.assignment_id,
                    "related_record_id": bus.bus_id,
                    "expected_detection": (
                        "A student requiring an accessible vehicle is assigned "
                        "to a non-accessible bus."
                    ),
                }
                break

        if accessibility_result is None:
            raise RuntimeError(
                "Could not find an accessible student with an active assignment."
            )

        anomalies.append(accessibility_result)

        # 3. Impossible route duration.
        routes = db.query(Route).all()
        duration_result = None

        for route in routes:
            route_stops = (
                db.query(RouteStop)
                .filter(RouteStop.route_id == route.route_id)
                .all()
            )

            total_travel = sum(
                stop.travel_time_from_previous_minutes or 0
                for stop in route_stops
            )

            if total_travel > 1:
                route.estimated_duration_minutes = 1
                duration_result = {
                    "anomaly_id": "ANOM-003",
                    "issue_type": "impossible_route_travel_time",
                    "affected_record_type": "Route",
                    "affected_record_id": route.route_id,
                    "expected_detection": (
                        f"Route travel time ({total_travel} minutes) exceeds "
                        "the declared route duration (1 minute)."
                    ),
                }
                break

        if duration_result is None:
            raise RuntimeError("Could not find a route suitable for duration anomaly.")

        anomalies.append(duration_result)

        # 4. Invalid guardian contact used for a sent notification.
        sent_notifications = (
            db.query(Notification)
            .filter(Notification.notification_status == "sent")
            .all()
        )

        notification_result = None

        for notification in sent_notifications:
            guardian = (
                db.query(GuardianContact)
                .filter(
                    GuardianContact.guardian_id == notification.guardian_id
                )
                .first()
            )

            if guardian is not None:
                guardian.is_valid = False
                notification_result = {
                    "anomaly_id": "ANOM-004",
                    "issue_type": "invalid_contact_notification",
                    "affected_record_type": "Notification",
                    "affected_record_id": notification.notification_id,
                    "related_record_id": guardian.guardian_id,
                    "expected_detection": (
                        "A sent notification is associated with an invalid "
                        "guardian contact."
                    ),
                }
                break

        if notification_result is None:
            raise RuntimeError(
                "Could not find a sent notification with a guardian contact."
            )

        anomalies.append(notification_result)

        # 5. Student with an unapproved address.
        assigned_students = (
            db.query(Student)
            .join(Assignment, Assignment.student_id == Student.student_id)
            .filter(Assignment.assignment_status == "active")
            .all()
        )

        address_result = None

        for student in assigned_students:
            student.address_is_approved = False
            address_result = {
                "anomaly_id": "ANOM-005",
                "issue_type": "unapproved_student_address",
                "affected_record_type": "Student",
                "affected_record_id": student.student_id,
                "expected_detection": (
                    "A student with an active assignment has an unapproved address."
                ),
            }
            break

        if address_result is None:
            raise RuntimeError(
                "Could not find a student with an active assignment."
            )

        anomalies.append(address_result)

        db.commit()

        # Store labels separately from the anomaly database.
        ground_truth = {
            "dataset": "SchoolRoute AI synthetic anomaly test dataset",
            "seed": settings.RANDOM_SEED,
            "source_database": "schoolroute.db",
            "anomaly_database": "data/generated/schoolroute_anomalies.db",
            "labels_separated_from_validation_input": True,
            "anomalies": anomalies,
        }

        ground_truth_dir = PROJECT_ROOT / "data" / "ground_truth"
        ground_truth_dir.mkdir(parents=True, exist_ok=True)

        ground_truth_path = ground_truth_dir / "ground_truth.json"
        ground_truth_path.write_text(
            json.dumps(ground_truth, indent=4),
            encoding="utf-8",
        )

        print("\nANOMALY DATASET CREATED SUCCESSFULLY")
        print("=" * 45)
        print(f"Clean source:    {source_path}")
        print(f"Anomaly copy:    {anomaly_path}")
        print(f"Ground truth:    {ground_truth_path}")
        print(f"Anomalies added: {len(anomalies)}")

        for item in anomalies:
            print(
                f"{item['anomaly_id']} | "
                f"{item['issue_type']} | "
                f"{item['affected_record_id']}"
            )

        print("\nThe original schoolroute.db was not modified.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
