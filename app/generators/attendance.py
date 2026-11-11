
import random
from datetime import date, datetime, time, timedelta, timezone

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import (
    Assignment,
    GuardianContact,
    AttendanceEvent,
    Notification,
)


def get_school_days(start_date, count):
    """Return the requested number of weekdays."""

    days = []
    current = start_date

    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)

        current += timedelta(days=1)

    return days


def generate_attendance(seed=settings.RANDOM_SEED):
    """Generate reproducible attendance and simulated notifications."""

    rng = random.Random(seed)
    db = SessionLocal()

    try:
        if db.query(AttendanceEvent).first():
            raise RuntimeError(
                "Attendance events already exist. "
                "Use an empty attendance dataset."
            )

        if db.query(Notification).first():
            raise RuntimeError(
                "Notifications already exist. "
                "Use an empty notification dataset."
            )

        assignments = (
            db.query(Assignment)
            .filter(Assignment.assignment_status == "active")
            .order_by(Assignment.assignment_id)
            .all()
        )

        if not assignments:
            raise RuntimeError(
                "No active assignments found. Generate operations first."
            )

        guardians = (
            db.query(GuardianContact)
            .filter(GuardianContact.is_primary.is_(True))
            .order_by(GuardianContact.guardian_id)
            .all()
        )

        guardian_by_student = {
            guardian.student_id: guardian
            for guardian in guardians
        }

        school_days = get_school_days(
            date(2026, 6, 1),
            settings.STARTER_SCHOOL_DAYS,
        )

        event_count = 0
        notification_count = 0
        absence_count = 0
        missed_pickup_count = 0

        for assignment in assignments:
            guardian = guardian_by_student.get(assignment.student_id)

            for service_date in school_days:

                is_absent = rng.random() < 0.04

                is_missed = (
                    not is_absent and rng.random() < 0.01
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

                pickup_event = AttendanceEvent(
                    attendance_event_id=(
                        f"ATT-{assignment.student_id}-"
                        f"{service_date:%Y%m%d}-P"
                    ),
                    student_id=assignment.student_id,
                    assignment_id=assignment.assignment_id,
                    service_date=service_date,
                    event_type="pickup",
                    event_status=pickup_status,
                    event_timestamp=pickup_timestamp,
                    notes=(
                        "Synthetic absence"
                        if is_absent
                        else "Synthetic missed pickup"
                        if is_missed
                        else "Synthetic pickup recorded"
                    ),
                )

                dropoff_event = AttendanceEvent(
                    attendance_event_id=(
                        f"ATT-{assignment.student_id}-"
                        f"{service_date:%Y%m%d}-D"
                    ),
                    student_id=assignment.student_id,
                    assignment_id=assignment.assignment_id,
                    service_date=service_date,
                    event_type="dropoff",
                    event_status=dropoff_status,
                    event_timestamp=dropoff_timestamp,
                    notes=(
                        "Not applicable because pickup did not occur"
                        if is_absent or is_missed
                        else "Synthetic drop-off recorded"
                    ),
                )

                db.add_all([pickup_event, dropoff_event])
                event_count += 2

                # Notify the primary guardian for attendance exceptions.
                if (is_absent or is_missed) and guardian is not None:

                    if guardian.preferred_channel == "sms":
                        recipient = guardian.synthetic_phone

                    elif guardian.preferred_channel == "email":
                        recipient = guardian.synthetic_email

                    else:
                        recipient = (
                            f"SYNTHETIC-PUSH-{guardian.guardian_id}"
                        )

                    # Deterministic notification timestamps.
                    notification_created_at = datetime.combine(
                        service_date,
                        time(7, 20),
                        tzinfo=timezone.utc,
                    )

                    notification_sent_at = datetime.combine(
                        service_date,
                        time(7, 21),
                        tzinfo=timezone.utc,
                    )

                    notification = Notification(
                        notification_id=(
                            f"NOT-2026-{notification_count + 1:06d}"
                        ),
                        student_id=assignment.student_id,
                        guardian_id=guardian.guardian_id,
                        attendance_event_id=pickup_event.attendance_event_id,
                        channel=guardian.preferred_channel,
                        message_type=(
                            "student_absence"
                            if is_absent
                            else "missed_pickup"
                        ),
                        notification_status=(
                            "sent" if guardian.is_valid else "failed"
                        ),
                        synthetic_recipient=recipient,
                        created_at=notification_created_at,
                        sent_at=(
                            notification_sent_at
                            if guardian.is_valid
                            else None
                        ),
                        failure_reason=(
                            None if guardian.is_valid
                            else "Synthetic invalid guardian contact"
                        ),
                    )

                    db.add(notification)
                    notification_count += 1

        db.commit()

        print("\nATTENDANCE DATA GENERATED SUCCESSFULLY")
        print("--------------------------------------")
        print(f"School days:          {len(school_days)}")
        print(f"Active assignments:   {len(assignments):,}")
        print(f"Attendance events:    {event_count:,}")
        print(f"Absences:             {absence_count:,}")
        print(f"Missed pickups:       {missed_pickup_count:,}")
        print(f"Notifications:        {notification_count:,}")
        print("--------------------------------------")
        print("Notification mode: SIMULATION ONLY")
        print(f"Seed: {seed}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_attendance()
