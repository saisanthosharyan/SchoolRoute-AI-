import random
from collections import Counter
from datetime import date

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import (
    Student,
    Stop,
    Bus,
    Driver,
    Route,
    RouteStop,
    Assignment,
)


def generate_operations(seed=settings.RANDOM_SEED):
    """Generate routes, route stops, and valid student assignments."""

    rng = random.Random(seed)
    db = SessionLocal()

    try:
        if (
            db.query(Route).first()
            or db.query(RouteStop).first()
            or db.query(Assignment).first()
        ):
            raise RuntimeError(
                "Operational records already exist. "
                "Use an empty operational dataset."
            )

        students = db.query(Student).order_by(Student.student_id).all()
        stops = db.query(Stop).filter(Stop.is_approved.is_(True)).all()
        buses = db.query(Bus).order_by(Bus.bus_id).all()
        drivers = db.query(Driver).order_by(Driver.driver_id).all()

        if not students or not stops or not buses or not drivers:
            raise RuntimeError(
                "Master data is missing. Generate master data first."
            )

        if len(buses) != len(drivers):
            raise RuntimeError(
                "This starter generator expects one driver per bus."
            )

        # Divide students evenly across available buses.
        student_groups = [[] for _ in buses]

        for index, student in enumerate(students):
            student_groups[index % len(buses)].append(student)

        stops_by_zone = {}

        for stop in stops:
            stops_by_zone.setdefault(stop.address_zone_id, []).append(stop)

        assignments_created = 0
        route_stops_created = 0

        for route_index, (bus, driver, group) in enumerate(
            zip(buses, drivers, student_groups),
            start=1,
        ):
            if not group:
                continue

            if len(group) > bus.capacity:
                raise ValueError(
                    f"Capacity exceeded for {bus.bus_id}: "
                    f"{len(group)} students / {bus.capacity} seats"
                )

            # Accessible students require an accessible vehicle.
            has_accessibility_need = any(
                student.requires_accessible_vehicle for student in group
            )

            if has_accessibility_need:
                bus.is_accessible = True

            route_id = f"ROUTE-2026-{route_index:06d}"

            route = Route(
                route_id=route_id,
                bus_id=bus.bus_id,
                driver_id=driver.driver_id,
                route_name=f"School Route {route_index:03d}",
                school_year=2026,
                estimated_duration_minutes=45,
                total_distance_km=round(rng.uniform(8, 25), 2),
                route_status="active",
                effective_from=date(2026, 6, 1),
                effective_to=None,
            )

            db.add(route)
            db.flush()

            # Choose up to three stops from the zones with the most students.
            zone_counts = Counter(
                student.address_zone_id for student in group
            )

            selected_zones = [
                zone_id
                for zone_id, _ in zone_counts.most_common(3)
            ]

            selected_stops = []

            for zone_id in selected_zones:
                candidates = stops_by_zone.get(zone_id, [])

                if candidates:
                    selected_stops.append(rng.choice(candidates))

            # Fill any remaining route stop positions.
            remaining_stops = [
                stop for stop in stops
                if stop.stop_id not in {
                    selected.stop_id for selected in selected_stops
                }
            ]

            while len(selected_stops) < min(3, len(stops)):
                if not remaining_stops:
                    break

                selected = rng.choice(remaining_stops)
                remaining_stops.remove(selected)
                selected_stops.append(selected)

            # Ensure an accessible stop is available for accessible students.
            if has_accessibility_need and selected_stops:
                accessible_stop_exists = any(
                    stop.is_accessible for stop in selected_stops
                )

                if not accessible_stop_exists:
                    accessible_candidates = [
                        stop for stop in stops
                        if stop.is_accessible
                        and stop.stop_id not in {
                            item.stop_id for item in selected_stops
                        }
                    ]

                    if accessible_candidates:
                        selected_stops[-1] = rng.choice(
                            accessible_candidates
                        )
                    else:
                        selected_stops[0].is_accessible = True

                # The route's selected stops must be accessible where needed.
                if not any(stop.is_accessible for stop in selected_stops):
                    selected_stops[0].is_accessible = True

            db.flush()

            # Create ordered route stops.
            for sequence, stop in enumerate(selected_stops, start=1):
                route_stop = RouteStop(
                    route_stop_id=(
                        f"RSTOP-{route_index:06d}-{sequence:02d}"
                    ),
                    route_id=route_id,
                    stop_id=stop.stop_id,
                    sequence_number=sequence,
                    estimated_arrival=[
                        "07:00",
                        "07:15",
                        "07:30",
                    ][sequence - 1],
                    travel_time_from_previous_minutes=(
                        0 if sequence == 1 else 15
                    ),
                )

                db.add(route_stop)
                route_stops_created += 1

            db.flush()

            # Create assignments only to stops on this route.
            for student in group:
                if not selected_stops:
                    raise RuntimeError(
                        f"No stops available for route {route_id}"
                    )

                if student.requires_accessible_vehicle:
                    eligible_stops = [
                        stop for stop in selected_stops
                        if stop.is_accessible
                    ]

                    if not eligible_stops:
                        raise RuntimeError(
                            f"No accessible stop for {student.student_id}"
                        )
                else:
                    eligible_stops = selected_stops

                # Prefer a stop in the student's own zone.
                same_zone = [
                    stop for stop in eligible_stops
                    if stop.address_zone_id == student.address_zone_id
                ]

                if same_zone:
                    assigned_stop = same_zone[0]
                else:
                    # Otherwise use the geographically closest route stop.
                    assigned_stop = min(
                        eligible_stops,
                        key=lambda stop: (
                            (stop.latitude - student.latitude) ** 2
                            + (stop.longitude - student.longitude) ** 2
                        ),
                    )

                assignment = Assignment(
                    assignment_id=f"ASN-{student.student_id}-2026",
                    student_id=student.student_id,
                    route_id=route_id,
                    stop_id=assigned_stop.stop_id,
                    school_year=2026,
                    effective_from=date(2026, 6, 1),
                    effective_to=None,
                    assignment_status="active",
                )

                db.add(assignment)
                assignments_created += 1

        db.flush()

        # Validate assignment-to-route-stop consistency.
        route_stop_pairs = {
            (item.route_id, item.stop_id)
            for item in db.query(RouteStop).all()
        }

        for assignment in db.query(Assignment).all():
            if (assignment.route_id, assignment.stop_id) not in route_stop_pairs:
                raise ValueError(
                    f"Assignment {assignment.assignment_id} "
                    "references a stop outside its route."
                )

        # Validate capacity and accessibility.
        for route in db.query(Route).all():
            passenger_count = (
                db.query(Assignment)
                .filter(
                    Assignment.route_id == route.route_id,
                    Assignment.assignment_status == "active",
                )
                .count()
            )

            if passenger_count > route.bus.capacity:
                raise ValueError(
                    f"Capacity exceeded on {route.route_id}"
                )

            route_students = (
                db.query(Student)
                .join(
                    Assignment,
                    Assignment.student_id == Student.student_id,
                )
                .filter(Assignment.route_id == route.route_id)
                .all()
            )

            if any(
                student.requires_accessible_vehicle
                for student in route_students
            ) and not route.bus.is_accessible:
                raise ValueError(
                    f"Accessibility mismatch on {route.route_id}"
                )

        db.commit()

        print("\nOPERATIONAL DATA GENERATED SUCCESSFULLY")
        print("---------------------------------------")
        print(f"Routes created:       {db.query(Route).count():,}")
        print(f"Route stops created:  {route_stops_created:,}")
        print(f"Assignments created:  {assignments_created:,}")
        print("---------------------------------------")
        print("Capacity validation: PASSED")
        print("Accessibility validation: PASSED")
        print("Route-stop validation: PASSED")
        print(f"Seed: {seed}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_operations()
