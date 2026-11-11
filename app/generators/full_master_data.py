import random
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from app.config import settings
from app.database.connection import FullSessionLocal
from app.database.models import (
    AddressZone,
    Student,
    GuardianContact,
    Stop,
    Bus,
    Driver,
)


def generate_full_master_data(
    seed=settings.RANDOM_SEED,
    student_count=settings.FULL_STUDENTS,
    bus_count=settings.FULL_BUSES,
    stop_count=settings.FULL_STOPS,
):
    """Generate deterministic full-scale synthetic master data."""

    if student_count <= 0 or bus_count <= 0 or stop_count <= 0:
        raise ValueError("All record counts must be positive.")

    accessible_bus_count = min(bus_count, max(1, round(bus_count * 0.20)))
    accessible_student_count = round(student_count * 0.08)

    # Guarantee sufficient capacity for all students.
    minimum_bus_capacity = (
        student_count + bus_count - 1
    ) // bus_count

    bus_capacity = max(60, minimum_bus_capacity)

    if accessible_student_count > accessible_bus_count * bus_capacity:
        raise ValueError(
            "Accessible buses do not have enough combined capacity."
        )

    rng = random.Random(seed)

    fake = Faker("en_IN")
    fake.seed_instance(seed)

    db = FullSessionLocal()

    try:
        master_models = [
            AddressZone,
            Student,
            GuardianContact,
            Stop,
            Bus,
            Driver,
        ]

        for model in master_models:
            if db.query(model).first() is not None:
                raise RuntimeError(
                    f"{model.__tablename__} already contains records. "
                    "Use an empty full database."
                )

        print("GENERATING FULL-SCALE MASTER DATA")
        print("=" * 50)
        print(f"Seed: {seed}")
        print(f"Students: {student_count:,}")
        print(f"Buses: {bus_count:,}")
        print(f"Stops: {stop_count:,}")
        print(f"Accessible buses: {accessible_bus_count:,}")
        print(f"Accessible students: {accessible_student_count:,}")
        print(f"Capacity per bus: {bus_capacity:,}")

        # 1. Address zones
        zone_count = min(30, max(10, stop_count // 10))
        zones = []

        for i in range(1, zone_count + 1):
            zones.append(
                AddressZone(
                    zone_id=f"ZONE-{i:03d}",
                    zone_name=f"Hyderabad Zone {i:02d}",
                    city="Hyderabad",
                    postal_code=f"SYN-{500000 + i:06d}",
                    latitude=round(
                        17.385 + rng.uniform(-0.08, 0.08), 6
                    ),
                    longitude=round(
                        78.486 + rng.uniform(-0.08, 0.08), 6
                    ),
                    is_active=True,
                )
            )

        db.add_all(zones)
        db.flush()

        # 2. Buses and drivers
        buses = []
        drivers = []

        for i in range(1, bus_count + 1):
            is_accessible = i <= accessible_bus_count

            buses.append(
                Bus(
                    bus_id=f"BUS-{i:06d}",
                    registration_number=f"SYN-BUS-{i:04d}",
                    capacity=bus_capacity,
                    is_accessible=is_accessible,
                    operational_status="active",
                    capacity_effective_from=date(2026, 1, 1),
                    capacity_effective_to=None,
                )
            )

            drivers.append(
                Driver(
                    driver_id=f"DRV-{i:06d}",
                    driver_name=fake.name(),
                    synthetic_license_number=f"SYN-LIC-{i:06d}",
                    license_valid_until=date(2028, 12, 31),
                    is_active=True,
                )
            )

        db.add_all(buses)
        db.add_all(drivers)
        db.flush()

        # 3. Approved stops
        stops = []

        for i in range(1, stop_count + 1):
            zone = rng.choice(zones)

            stops.append(
                Stop(
                    stop_id=f"STOP-{i:06d}",
                    stop_name=f"Synthetic Pickup Stop {i:03d}",
                    address_zone_id=zone.zone_id,
                    latitude=round(
                        zone.latitude + rng.uniform(-0.01, 0.01), 6
                    ),
                    longitude=round(
                        zone.longitude + rng.uniform(-0.01, 0.01), 6
                    ),
                    pickup_window_start="07:00",
                    pickup_window_end="08:30",
                    is_approved=True,
                    is_accessible=(rng.random() < 0.30),
                )
            )

        # Guarantee accessible stops exist.
        if not any(stop.is_accessible for stop in stops):
            stops[0].is_accessible = True

        db.add_all(stops)
        db.flush()

        accessible_stops = [
            stop for stop in stops if stop.is_accessible
        ]

        # 4. Students and guardian contacts
        students = []
        guardians = []

        accessible_student_ids = set(
            rng.sample(
                range(1, student_count + 1),
                accessible_student_count,
            )
        )

        for i in range(1, student_count + 1):
            zone = rng.choice(zones)
            requires_accessible = i in accessible_student_ids

            students.append(
                Student(
                    student_id=f"STU-{i:06d}",
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    grade=rng.randint(1, 12),
                    address_zone_id=zone.zone_id,
                    synthetic_address=(
                        f"{fake.street_address()}, "
                        f"{zone.zone_name}, Hyderabad"
                    ),
                    latitude=round(
                        zone.latitude + rng.uniform(-0.008, 0.008), 6
                    ),
                    longitude=round(
                        zone.longitude + rng.uniform(-0.008, 0.008), 6
                    ),
                    requires_accessible_vehicle=requires_accessible,
                    address_is_approved=True,
                    enrollment_status="active",
                    created_at=(
                        datetime(2026, 1, 1, tzinfo=timezone.utc)
                        + timedelta(days=rng.randint(0, 300))
                    ),
                )
            )

            guardian_count = rng.choices(
                [1, 2],
                weights=[0.75, 0.25],
            )[0]

            for contact_number in range(1, guardian_count + 1):
                guardians.append(
                    GuardianContact(
                        guardian_id=(
                            f"GRD-{i:06d}-{contact_number:02d}"
                        ),
                        student_id=f"STU-{i:06d}",
                        guardian_name=fake.name(),
                        synthetic_phone=(
                            f"SYNTHETIC-PHONE-{i:06d}-{contact_number:02d}"
                        ),
                        synthetic_email=(
                            f"guardian{i:06d}-{contact_number:02d}"
                            "@example.invalid"
                        ),
                        relationship_type=rng.choice(
                            ["parent", "mother", "father", "guardian"]
                        ),
                        preferred_channel=rng.choice(
                            ["sms", "email", "push"]
                        ),
                        is_valid=True,
                        is_primary=(contact_number == 1),
                    )
                )

        # Insert in manageable batches.
        batch_size = 500

        for start in range(0, len(students), batch_size):
            db.add_all(students[start:start + batch_size])
            db.flush()

        for start in range(0, len(guardians), batch_size):
            db.add_all(guardians[start:start + batch_size])
            db.flush()

        db.commit()

        print("\nMASTER DATA GENERATED SUCCESSFULLY")
        print("-" * 50)

        for model in master_models:
            print(
                f"{model.__tablename__:<20}: "
                f"{db.query(model).count():>8,}"
            )

        total_capacity = db.query(Bus).count() * bus_capacity

        print("-" * 50)
        print(f"Total bus capacity: {total_capacity:,}")
        print(f"Accessible stops: {len(accessible_stops):,}")
        print(f"Random seed: {seed}")
        print("Database: schoolroute_full.db")
        print("All records committed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_full_master_data()
