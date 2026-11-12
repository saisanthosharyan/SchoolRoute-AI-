from collections import Counter
from datetime import date, datetime
from math import ceil, radians, sin, cos, sqrt
from pathlib import Path

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.config import settings
from app.database.connection import FullSessionLocal
from app.database.models import (
    Student,
    Bus,
    Stop,
    Driver,
    Route,
    RouteStop,
    Assignment,
)


EFFECTIVE_FROM = date(2026, 6, 1)
AVERAGE_SPEED_KMH = 25
STOP_DWELL_MINUTES = 2
SOLVER_TIME_LIMIT_MS = 50


class RoutePlanningError(Exception):
    """Raised when a valid full-scale route plan cannot be created."""


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two coordinates."""

    radius = 6371.0

    lat1, lon1, lat2, lon2 = map(
        radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    value = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * radius * asin_safe(value)


def asin_safe(value):
    from math import asin
    return asin(sqrt(max(0.0, min(1.0, value))))


def travel_minutes(distance_km):
    return max(1, ceil(distance_km / AVERAGE_SPEED_KMH * 60))



def spatial_sort(records):
    """Deterministic geographic ordering."""

    return sorted(
        records,
        key=lambda item: (
            item.latitude,
            item.longitude,
            item.student_id,
        ),
    )


def balanced_spatial_clusters(records, cluster_sizes):
    """
    Divide records into balanced, geographically compact clusters.

    Recursively split along the widest geographic dimension.
    This avoids creating long, scattered latitude-only groups.
    """

    if sum(cluster_sizes) != len(records):
        raise RoutePlanningError(
            "Cluster sizes do not match the number of records."
        )

    if any(size <= 0 for size in cluster_sizes):
        raise RoutePlanningError(
            "Every geographic cluster must contain students."
        )

    def split(items, sizes):
        if len(sizes) == 1:
            return [sorted(items, key=lambda item: item.student_id)]

        latitudes = [item.latitude for item in items]
        longitudes = [item.longitude for item in items]

        latitude_span = max(latitudes) - min(latitudes)
        longitude_span = (
            (max(longitudes) - min(longitudes))
            * cos(radians(sum(latitudes) / len(latitudes)))
        )

        if latitude_span >= longitude_span:
            axis = lambda item: item.latitude
        else:
            axis = lambda item: item.longitude

        ordered = sorted(
            items,
            key=lambda item: (axis(item), item.student_id),
        )

        middle = len(sizes) // 2
        left_size = sum(sizes[:middle])

        left_records = ordered[:left_size]
        right_records = ordered[left_size:]

        return (
            split(left_records, sizes[:middle])
            + split(right_records, sizes[middle:])
        )

    return split(list(records), list(cluster_sizes))


def build_student_groups(students, buses):
    """
    Allocate students into balanced geographic bus groups.

    Accessibility-required students only use accessible buses.
    Remaining seats are filled with nearby regular students.
    All other students are geographically clustered for regular buses.
    """

    accessible_buses = sorted(
        [bus for bus in buses if bus.is_accessible],
        key=lambda bus: bus.bus_id,
    )

    regular_buses = sorted(
        [bus for bus in buses if not bus.is_accessible],
        key=lambda bus: bus.bus_id,
    )

    accessible_students = [
        student for student in students
        if student.requires_accessible_vehicle
    ]

    regular_students = [
        student for student in students
        if not student.requires_accessible_vehicle
    ]

    if not accessible_buses and accessible_students:
        raise RoutePlanningError(
            "Accessible students exist but no accessible buses are available."
        )

    if len(accessible_students) > sum(
        bus.capacity for bus in accessible_buses
    ):
        raise RoutePlanningError(
            "Accessible bus capacity is insufficient."
        )

    if accessible_buses and (
        len(accessible_students) < len(accessible_buses)
    ):
        raise RoutePlanningError(
            "Not enough accessible students for the accessible bus grouping."
        )

    groups = []
    remaining_regular = list(regular_students)

    # ---------------------------------------------------------
    # 1. Cluster accessible students geographically.
    # ---------------------------------------------------------

    if accessible_buses:
        base_size, remainder = divmod(
            len(accessible_students),
            len(accessible_buses),
        )

        accessible_sizes = [
            base_size + (1 if index < remainder else 0)
            for index in range(len(accessible_buses))
        ]

        accessible_chunks = balanced_spatial_clusters(
            accessible_students,
            accessible_sizes,
        )

        for bus, accessible_group in zip(
            accessible_buses,
            accessible_chunks,
        ):
            group = list(accessible_group)

            if len(group) > bus.capacity:
                raise RoutePlanningError(
                    f"Accessible students exceed capacity of {bus.bus_id}."
                )

            # Fill remaining seats using the nearest regular students.
            needed = bus.capacity - len(group)

            if needed:
                center_lat = sum(
                    student.latitude for student in group
                ) / len(group)

                center_lon = sum(
                    student.longitude for student in group
                ) / len(group)

                nearest = sorted(
                    remaining_regular,
                    key=lambda student: (
                        (student.latitude - center_lat) ** 2
                        + (
                            (student.longitude - center_lon)
                            * cos(radians(center_lat))
                        ) ** 2,
                        student.student_id,
                    ),
                )[:needed]

                selected_ids = {
                    student.student_id for student in nearest
                }

                group.extend(nearest)

                remaining_regular = [
                    student for student in remaining_regular
                    if student.student_id not in selected_ids
                ]

            groups.append((bus, group))

    # ---------------------------------------------------------
    # 2. Cluster remaining regular students across regular buses.
    # ---------------------------------------------------------

    if len(remaining_regular) > sum(
        bus.capacity for bus in regular_buses
    ):
        raise RoutePlanningError(
            "Remaining regular students exceed regular bus capacity."
        )

    if regular_buses:
        base_size, remainder = divmod(
            len(remaining_regular),
            len(regular_buses),
        )

        regular_sizes = [
            base_size + (1 if index < remainder else 0)
            for index in range(len(regular_buses))
        ]

        if any(size == 0 for size in regular_sizes):
            raise RoutePlanningError(
                "Not enough students for the configured regular buses."
            )

        for bus, size in zip(regular_buses, regular_sizes):
            if size > bus.capacity:
                raise RoutePlanningError(
                    f"Capacity exceeded for {bus.bus_id}."
                )

        regular_chunks = balanced_spatial_clusters(
            remaining_regular,
            regular_sizes,
        )

        for bus, group in zip(regular_buses, regular_chunks):
            groups.append((bus, group))

    elif remaining_regular:
        raise RoutePlanningError(
            "Regular students exist but no regular buses are available."
        )

    # ---------------------------------------------------------
    # 3. Validate allocation integrity.
    # ---------------------------------------------------------

    assigned_ids = [
        student.student_id
        for _, group in groups
        for student in group
    ]

    if len(assigned_ids) != len(set(assigned_ids)):
        raise RoutePlanningError(
            "Duplicate student allocation detected."
        )

    if len(assigned_ids) != len(students):
        raise RoutePlanningError(
            "Some students were not allocated."
        )

    for bus, group in groups:
        if len(group) > bus.capacity:
            raise RoutePlanningError(
                f"Capacity exceeded for {bus.bus_id}."
            )

        if any(
            student.requires_accessible_vehicle
            for student in group
        ) and not bus.is_accessible:
            raise RoutePlanningError(
                f"Accessibility violation on {bus.bus_id}."
            )

    return groups



def choose_stop(student, stops):
    """Choose an approved stop, enforcing accessibility requirements."""

    eligible = [
        stop for stop in stops
        if (
            not student.requires_accessible_vehicle
            or stop.is_accessible
        )
    ]

    if not eligible:
        raise RoutePlanningError(
            f"No eligible approved stop for {student.student_id}."
        )

    same_zone = [
        stop for stop in eligible
        if stop.address_zone_id == student.address_zone_id
    ]

    candidates = same_zone if same_zone else eligible

    return min(
        candidates,
        key=lambda stop: haversine_km(
            student.latitude,
            student.longitude,
            stop.latitude,
            stop.longitude,
        ),
    )


def optimize_stop_order(stops):
    """Optimize a route's stop order using the OR-Tools routing solver."""

    if len(stops) <= 2:
        return list(stops)

    count = len(stops)

    matrix = [
        [
            round(
                haversine_km(
                    stops[i].latitude,
                    stops[i].longitude,
                    stops[j].latitude,
                    stops[j].longitude,
                ) * 1000
            )
            for j in range(count)
        ]
        for i in range(count)
    ]

    manager = pywrapcp.RoutingIndexManager(
        count,
        1,
        [0],
        [count - 1],
    )

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return matrix[from_node][to_node]

    callback_index = routing.RegisterTransitCallback(
        distance_callback
    )

    routing.SetArcCostEvaluatorOfAllVehicles(callback_index)

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    parameters.time_limit.FromMilliseconds(
        SOLVER_TIME_LIMIT_MS
    )

    solution = routing.SolveWithParameters(parameters)

    if solution is None:
        raise RoutePlanningError(
            "OR-Tools could not find a valid stop sequence."
        )

    ordered_indices = []
    index = routing.Start(0)

    while not routing.IsEnd(index):
        ordered_indices.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))

    ordered_indices.append(manager.IndexToNode(index))

    return [stops[index] for index in ordered_indices]


def parse_clock(value):
    try:
        return datetime.strptime(value, "%H:%M").hour * 60 + (
            datetime.strptime(value, "%H:%M").minute
        )
    except (TypeError, ValueError):
        raise RoutePlanningError(
            f"Invalid pickup window time: {value}"
        )


def format_clock(minutes):
    hours, mins = divmod(minutes, 60)

    if hours >= 24:
        raise RoutePlanningError("Route arrival exceeds one day.")

    return f"{hours:02d}:{mins:02d}"


def schedule_stops(ordered_stops):
    """Calculate arrivals and validate every pickup window."""

    current_time = 7 * 60
    route_start = current_time
    total_distance = 0.0
    records = []
    previous_stop = None

    for sequence, stop in enumerate(ordered_stops, start=1):
        travel = 0

        if previous_stop is not None:
            distance = haversine_km(
                previous_stop.latitude,
                previous_stop.longitude,
                stop.latitude,
                stop.longitude,
            )

            travel = travel_minutes(distance)
            total_distance += distance
            current_time += travel

        window_start = parse_clock(stop.pickup_window_start)
        window_end = parse_clock(stop.pickup_window_end)

        arrival = max(current_time, window_start)

        if arrival > window_end:
            raise RoutePlanningError(
                f"Pickup window violation at {stop.stop_id}: "
                f"arrival {format_clock(arrival)}, "
                f"window ends {stop.pickup_window_end}."
            )

        records.append({
            "stop": stop,
            "sequence": sequence,
            "arrival": format_clock(arrival),
            "travel": travel,
        })

        current_time = arrival + STOP_DWELL_MINUTES
        previous_stop = stop

    duration = max(1, current_time - route_start)

    return records, duration, round(total_distance, 3)


def build_route_plan(db):
    """Build and validate the complete plan without writing records."""

    if db.query(Route).count() or db.query(Assignment).count():
        raise RoutePlanningError(
            "Full database already contains routes or assignments. "
            "Refusing to create duplicate operations."
        )

    students = db.query(Student).filter(
        Student.enrollment_status == "active",
        Student.address_is_approved.is_(True),
    ).order_by(Student.student_id).all()

    buses = db.query(Bus).filter(
        Bus.operational_status == "active",
    ).order_by(Bus.bus_id).all()

    drivers = db.query(Driver).filter(
        Driver.is_active.is_(True),
        Driver.license_valid_until >= EFFECTIVE_FROM,
    ).order_by(Driver.driver_id).all()

    stops = db.query(Stop).filter(
        Stop.is_approved.is_(True),
    ).order_by(Stop.stop_id).all()

    if not students or not buses or not drivers or not stops:
        raise RoutePlanningError(
            "Required students, buses, drivers, or approved stops are missing."
        )

    if len(drivers) < len(buses):
        raise RoutePlanningError(
            "There are not enough licensed active drivers for all buses."
        )

    if any(
        student.latitude is None or student.longitude is None
        for student in students
    ):
        raise RoutePlanningError("A student is missing coordinates.")

    if any(
        stop.latitude is None or stop.longitude is None
        for stop in stops
    ):
        raise RoutePlanningError("An approved stop is missing coordinates.")

    groups = build_student_groups(students, buses)

    accessible_stops = [
        stop for stop in stops if stop.is_accessible
    ]

    if not accessible_stops and any(
        student.requires_accessible_vehicle for student in students
    ):
        raise RoutePlanningError(
            "No accessible approved stops are available."
        )

    route_objects = []
    route_stop_objects = []
    assignment_objects = []

    route_summaries = []
    total_assigned = 0
    total_route_stops = 0

    for route_number, (bus, group) in enumerate(groups, start=1):
        driver = drivers[route_number - 1]

        if len(group) > bus.capacity:
            raise RoutePlanningError(
                f"Capacity exceeded for {bus.bus_id}."
            )

        if any(
            student.requires_accessible_vehicle
            for student in group
        ) and not bus.is_accessible:
            raise RoutePlanningError(
                f"Accessibility violation on {bus.bus_id}."
            )

        student_stop_map = {}

        for student in group:
            selected_stop = choose_stop(student, stops)
            student_stop_map[student.student_id] = selected_stop

        unique_stops = {
            stop.stop_id: stop
            for stop in student_stop_map.values()
        }

        ordered_stops = optimize_stop_order(
            list(unique_stops.values())
        )

        schedule, duration, distance = schedule_stops(
            ordered_stops
        )

        route_id = f"ROUTE-{settings.SCHOOL_YEAR}-{route_number:06d}"

        route_objects.append(Route(
            route_id=route_id,
            bus_id=bus.bus_id,
            driver_id=driver.driver_id,
            route_name=f"School Route {route_number:03d}",
            school_year=settings.SCHOOL_YEAR,
            estimated_duration_minutes=duration,
            total_distance_km=distance,
            route_status="active",
            effective_from=EFFECTIVE_FROM,
            effective_to=None,
        ))

        for item in schedule:
            stop = item["stop"]

            route_stop_objects.append(RouteStop(
                route_stop_id=(
                    f"RSTOP-{route_number:06d}-{item['sequence']:03d}"
                ),
                route_id=route_id,
                stop_id=stop.stop_id,
                sequence_number=item["sequence"],
                estimated_arrival=item["arrival"],
                travel_time_from_previous_minutes=item["travel"],
            ))

        route_stop_ids = {
            stop.stop_id for stop in ordered_stops
        }

        for student in group:
            stop = student_stop_map[student.student_id]

            if stop.stop_id not in route_stop_ids:
                raise RoutePlanningError(
                    "Student's assigned stop is missing from the route."
                )

            assignment_objects.append(Assignment(
                assignment_id=(
                    f"ASN-{student.student_id}-{settings.SCHOOL_YEAR}"
                ),
                student_id=student.student_id,
                route_id=route_id,
                stop_id=stop.stop_id,
                school_year=settings.SCHOOL_YEAR,
                effective_from=EFFECTIVE_FROM,
                effective_to=None,
                assignment_status="active",
            ))

        accessible_count = sum(
            bool(student.requires_accessible_vehicle)
            for student in group
        )

        route_summaries.append({
            "route_id": route_id,
            "bus_id": bus.bus_id,
            "driver_id": driver.driver_id,
            "students": len(group),
            "accessible_students": accessible_count,
            "stops": len(ordered_stops),
            "duration": duration,
            "distance": distance,
        })

        total_assigned += len(group)
        total_route_stops += len(ordered_stops)

    if total_assigned != len(students):
        raise RoutePlanningError(
            "Final student assignment count does not match student count."
        )

    return {
        "routes": route_objects,
        "route_stops": route_stop_objects,
        "assignments": assignment_objects,
        "summaries": route_summaries,
        "student_count": len(students),
        "bus_count": len(buses),
        "driver_count": len(drivers),
        "approved_stop_count": len(stops),
        "route_stop_count": total_route_stops,
    }


def generate_full_operations(dry_run=True):
    """Generate operations. Dry run is the safe default."""

    db = FullSessionLocal()

    try:
        plan = build_route_plan(db)

        print("\n========== FULL-SCALE ROUTE PLAN ==========")
        print("Mode:", "DRY RUN - NO DATABASE WRITES" if dry_run else "COMMIT")
        print("Students:", plan["student_count"])
        print("Buses:", plan["bus_count"])
        print("Drivers:", plan["driver_count"])
        print("Approved stops:", plan["approved_stop_count"])
        print("Routes planned:", len(plan["routes"]))
        print("Route stops planned:", plan["route_stop_count"])
        print("Assignments planned:", len(plan["assignments"]))

        print("\n========== ROUTE SUMMARY ==========")

        for summary in plan["summaries"]:
            print(
                f"{summary['route_id']} | "
                f"Bus: {summary['bus_id']} | "
                f"Students: {summary['students']} | "
                f"Accessible: {summary['accessible_students']} | "
                f"Stops: {summary['stops']} | "
                f"Duration: {summary['duration']} min | "
                f"Distance: {summary['distance']} km"
            )

        if dry_run:
            print("\nDRY RUN PASSED.")
            print("No database records were inserted.")
            return plan

        db.add_all(plan["routes"])
        db.add_all(plan["route_stops"])
        db.add_all(plan["assignments"])

        db.flush()
        db.commit()

        print("\nDATABASE COMMIT SUCCESSFUL.")
        print("Routes inserted:", len(plan["routes"]))
        print("Route stops inserted:", len(plan["route_stops"]))
        print("Assignments inserted:", len(plan["assignments"]))

        return plan

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_full_operations(dry_run=True)
