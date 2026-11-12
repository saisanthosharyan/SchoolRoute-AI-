import random
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import insert, select

from app.config import settings
from app.database.connection import FullSessionLocal
from app.database.models import (
    Assignment,
    GuardianContact,
    AttendanceEvent,
    Notification,
)


START_DATE = date(2026, 6, 1)
BATCH_SIZE = 10_000

ABSENCE_RATE = 0.04
MISSED_PICKUP_RATE = 0.01


def get_school_days(start_date, count):
    """Return a deterministic sequence of weekdays."""

    days = []
    current = start_date

    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)

        current += timedelta(days=1)

    return days


def flush_batch(db, model, batch, dry_run):
    """Insert a batch without constructing ORM objects."""

    if not batch:
        return

    if not dry_run:
        db.execute(insert(model), batch)

    batch.clear()


def generate_full_attendance(
    seed=settings.RANDOM_SEED,
    school_days=settings.FULL_SCHOOL_DAYS,
    batch_size=BATCH_SIZE,
    dry_run=True,
):
    """
    Generate full-scale attendance and simulated guardian notifications.

    Dry-run is the default. No records are written unless explicitly
    called with dry_run=False.
    """

    if school_days < 1:
        raise ValueError("school_days must be at least 1")

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    rng = random.Random(seed)
    db = FullSessionLocal()

    try:
        if db.execute(
            select(AttendanceEvent.attendance_event_id).limit(1)
        ).first():
            raise RuntimeError(
                "Attendance events already exist in the full database. "
                "Refusing to generate duplicate history."
            )

        if db.execute(
            select(Notification.notification_id).limit(1)
        ).first():
            raise RuntimeError(
                "Notifications already exist in the full database. "
                "Refusing to generate duplicate notifications."
            )

        assignments = db.execute(
            select(
                Assignment.assignment_id,
                Assignment.student_id,
            )
            .where(Assignment.assignment_status == "active")
            .order_by(Assignment.student_id)
        ).all()

        if not assignments:
            raise RuntimeError(
                "No active assignments found. Generate full operations first."
            )

        guardians = db.execute(
            select(
                GuardianContact.guardian_id,
                GuardianContact.student_id,
                GuardianContact.preferred_channel,
                GuardianContact.synthetic_phone,
                GuardianContact.synthetic_email,
                GuardianContact.is_valid,
            )
            .where(GuardianContact.is_primary.is_(True))
            .order_by(GuardianContact.guardian_id)
        ).all()

        guardian_by_student = {
            row.student_id: row
            for row in guardians
        }

        missing_guardians = [
            row.student_id
            for row in assignments
            if row.student_id not in guardian_by_student
        ]

        if missing_guardians:
            raise RuntimeError(
                f"{len(missing_guardians)} assigned students have no "
                "primary guardian. Refusing to generate incomplete data."
            )

        school_dates = get_school_days(START_DATE, school_days)

        attendance_batch = []
        notification_batch = []

        attendance_count = 0
        notification_count = 0
        absence_count = 0
        missed_pickup_count = 0
        successful_notifications = 0
        failed_notifications = 0

        for service_date in school_dates:

            for assignment in assignments:

                student_id = assignment.student_id
                guardian = guardian_by_student[student_id]

                is_absent = rng.random() < ABSENCE_RATE

                is_missed = (
                    not is_absent
                    and rng.random() < MISSED_PICKUP_RATE
                )

                pickup_timestamp = datetime.combine(
                    service_date,
                    time(7, 15),
                    tzinfo=timezone.utc,
                )

                dropoff_timestamp = datetime.combine(
                    service_date,
                    time(15, 30),
                    tzinfo=timezone.utc,
                )

                if is_absent:
                    pickup_status = "absent"
                    dropoff_status = "not_applicable"
                    absence_count += 1

                elif is_missed:
                    pickup_status = "missed_pickup"
                    dropoff_status = "not_applicable"
                    missed_pickup_count += 1

                else:
                    pickup_status = "present"
                    dropoff_status = "completed"

                pickup_event_id = (
                    f"ATT-{student_id}-{service_date:%Y%m%d}-P"
                )

                dropoff_event_id = (
                    f"ATT-{student_id}-{service_date:%Y%m%d}-D"
                )

                attendance_batch.extend([
                    {
                        "attendance_event_id": pickup_event_id,
                        "student_id": student_id,
                        "assignment_id": assignment.assignment_id,
                        "service_date": service_date,
                        "event_type": "pickup",
                        "event_status": pickup_status,
                        "event_timestamp": pickup_timestamp,
                        "notes": (
                            "Synthetic absence"
                            if is_absent
                            else "Synthetic missed pickup"
                            if is_missed
                            else "Synthetic pickup recorded"
                        ),
                    },
                    {
                        "attendance_event_id": dropoff_event_id,
                        "student_id": student_id,
                        "assignment_id": assignment.assignment_id,
                        "service_date": service_date,
                        "event_type": "dropoff",
                        "event_status": dropoff_status,
                        "event_timestamp": dropoff_timestamp,
                        "notes": (
                            "Not applicable because pickup did not occur"
                            if is_absent or is_missed
                            else "Synthetic drop-off recorded"
                        ),
                    },
                ])

                attendance_count += 2

                if (is_absent or is_missed):

                    if guardian.preferred_channel == "sms":
                        recipient = guardian.synthetic_phone

                    elif guardian.preferred_channel == "email":
                        recipient = guardian.synthetic_email

                    else:
                        recipient = (
                            f"SYNTHETIC-PUSH-{guardian.guardian_id}"
                        )

                    notification_count += 1

                    is_valid = bool(guardian.is_valid)

                    if is_valid:
                        successful_notifications += 1
                    else:
                        failed_notifications += 1

                    notification_batch.append({
                        "notification_id": (
                            f"NOT-2026-{notification_count:06d}"
                        ),
                        "student_id": student_id,
                        "guardian_id": guardian.guardian_id,
                        "attendance_event_id": pickup_event_id,
                        "channel": guardian.preferred_channel,
                        "message_type": (
                            "student_absence"
                            if is_absent
                            else "missed_pickup"
                        ),
                        "notification_status": (
                            "sent" if is_valid else "failed"
                        ),
                        "synthetic_recipient": recipient,
                        "created_at": datetime.combine(
                            service_date,
                            time(7, 20),
                            tzinfo=timezone.utc,
                        ),
                        "sent_at": (
                            datetime.combine(
                                service_date,
                                time(7, 21),
                                tzinfo=timezone.utc,
                            )
                            if is_valid else None
                        ),
                        "failure_reason": (
                            None
                            if is_valid
                            else "Synthetic invalid guardian contact"
                        ),
                    })

                if len(attendance_batch) >= batch_size:
                    flush_batch(
                        db,
                        AttendanceEvent,
                        attendance_batch,
                        dry_run,
                    )

                if len(notification_batch) >= batch_size:
                    flush_batch(
                        db,
                        Notification,
                        notification_batch,
                        dry_run,
                    )

            # Flush at the end of each school day.
            # Attendance is inserted before notifications that reference it.
            flush_batch(
                db,
                AttendanceEvent,
                attendance_batch,
                dry_run,
            )

            flush_batch(
                db,
                Notification,
                notification_batch,
                dry_run,
            )

        if dry_run:
            db.rollback()
        else:
            db.commit()

        print("\nFULL-SCALE ATTENDANCE GENERATION")
        print("================================")
        print(f"Mode:                 {'DRY RUN' if dry_run else 'DATABASE COMMIT'}")
        print(f"School days:          {len(school_dates):,}")
        print(f"Date range:           {school_dates[0]} to {school_dates[-1]}")
        print(f"Active assignments:   {len(assignments):,}")
        print(f"Attendance events:    {attendance_count:,}")
        print(f"Absences:             {absence_count:,}")
        print(f"Missed pickups:       {missed_pickup_count:,}")
        print(f"Notifications:        {notification_count:,}")
        print(f"Simulated sent:       {successful_notifications:,}")
        print(f"Simulated failed:     {failed_notifications:,}")
        print(f"Random seed:          {seed:,}")
        print(f"Batch size:           {batch_size:,}")
        print("================================")

        if dry_run:
            print("DRY RUN PASSED. No database records were inserted.")
        else:
            print("DATABASE COMMIT SUCCESSFUL.")
            print("Notification mode: SIMULATION ONLY")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_full_attendance(dry_run=True)
