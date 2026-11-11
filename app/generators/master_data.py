import random
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import (
    AddressZone,
    Student,
    GuardianContact,
    Stop,
    Bus,
    Driver,
)


def generate_master_data(
    seed=settings.RANDOM_SEED,
    student_count=settings.STARTER_STUDENTS,
    bus_count=settings.STARTER_BUSES,
    stop_count=settings.STARTER_STOPS,
):
    """Generate reproducible synthetic master data."""

    rng = random.Random(seed)
    fake = Faker("en_IN")
    fake.seed_instance(seed)

    db = SessionLocal()

    try:
        # Avoid accidentally duplicating or replacing existing records.
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
                    "Use an empty database for this generator."
                )

        print(f"Generating master data with seed: {seed}")

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
                    latitude=round(17.385 + rng.uniform(-0.08, 0.08), 6),
                    longitude=round(78.486 + rng.uniform(-0.08, 0.08), 6),
                    is_active=True,
                )
            )

        db.add_all(zones)
        db.flush()

        # 2. Students
        students = []

        for i in range(1, student_count + 1):
            zone = rng.choice(zones)

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
                    requires_accessible_vehicle=(rng.random() < 0.08),
                    address_is_approved=True,
                    enrollment_status="active",
                    created_at=(
                        datetime(2026, 1, 1, tzinfo=timezone.utc)
                        + timedelta(days=rng.randint(0, 300))
                    ),
                )
            )

        db.add_all(students)
        db.flush()

        # 3. Guardian contacts
        guardians = []

        for i, student in enumerate(students, start=1):
            guardian_count = rng.choices([1, 2], weights=[0.75, 0.25])[0]

            for contact_number in range(1, guardian_count + 1):
                guardians.append(
                    GuardianContact(
                        guardian_id=f"GRD-{i:06d}-{contact_number:02d}",
                        student_id=student.student_id,
                        guardian_name=fake.name(),
                        synthetic_phone=f"SYNTHETIC-PHONE-{i:06d}-{contact_number:02d}",
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

        db.add_all(guardians)

        # 4. Approved pickup stops
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
                    is_accessible=(rng.random() < 0.25),
                )
            )

        db.add_all(stops)

        # 5. Buses
        buses = []

        for i in range(1, bus_count + 1):
            buses.append(
                Bus(
                    bus_id=f"BUS-{i:06d}",
                    registration_number=f"SYN-BUS-{i:04d}",
                    capacity=rng.choice([30, 35, 40, 45, 50]),
                    is_accessible=(rng.random() < 0.20),
                    operational_status="active",
                    capacity_effective_from=date(2026, 1, 1),
                    capacity_effective_to=None,
                )
            )

        db.add_all(buses)

        # 6. Drivers
        drivers = []

        for i in range(1, bus_count + 1):
            drivers.append(
                Driver(
                    driver_id=f"DRV-{i:06d}",
                    driver_name=fake.name(),
                    synthetic_license_number=f"SYN-LIC-{i:06d}",
                    license_valid_until=date(2028, 12, 31),
                    is_active=True,
                )
            )

        db.add_all(drivers)

        db.commit()

        print("\nMASTER DATA GENERATED SUCCESSFULLY")
        print("----------------------------------")

        for model in master_models:
            print(
                f"{model.__tablename__:20s}: "
                f"{db.query(model).count():,}"
            )

        print("----------------------------------")
        print(f"Seed: {seed}")
        print("All master records committed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_master_data()
