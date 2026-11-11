import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import PROJECT_ROOT
from app.validators.data_validator import DataValidator


EXPECTED_ERROR_PATTERNS = {
    "bus_capacity_exceeded": "capacity exceeded",
    "incompatible_accessibility_assignment": "requires an accessible bus",
    "impossible_route_travel_time": "travel time exceeds",
    "invalid_contact_notification": "sent to invalid guardian contact",
    "unapproved_student_address": "student address is not approved",
}


def main():
    database_path = (
        PROJECT_ROOT / "data" / "generated" / "schoolroute_anomalies.db"
    )
    ground_truth_path = (
        PROJECT_ROOT / "data" / "ground_truth" / "ground_truth.json"
    )

    ground_truth = json.loads(
        ground_truth_path.read_text(encoding="utf-8")
    )

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        report = DataValidator(db).run()
        errors = report["errors"]

        detected = 0

        print("\nSCHOOLROUTE AI ANOMALY DETECTION REPORT")
        print("=" * 70)

        for anomaly in ground_truth["anomalies"]:
            record_id = anomaly["affected_record_id"]
            issue_type = anomaly["issue_type"]
            expected_pattern = EXPECTED_ERROR_PATTERNS[issue_type]

            matching_errors = [
                error for error in errors
                if record_id in error and expected_pattern in error
            ]

            success = bool(matching_errors)

            if success:
                detected += 1

            status = "DETECTED" if success else "NOT DETECTED"

            print(
                f"{anomaly['anomaly_id']} | "
                f"{issue_type} | {status}"
            )

            for error in matching_errors:
                print(f"    {error}")

        total = len(ground_truth["anomalies"])
        detection_rate = detected / total * 100 if total else 0

        print("\n" + "=" * 70)
        print(f"Expected anomalies: {total}")
        print(f"Detected correctly: {detected}")
        print(f"Detection rate:     {detection_rate:.1f}%")
        print(f"Total validator errors: {len(errors)}")
        print("=" * 70)

        if detected != total:
            raise SystemExit("Anomaly detection test FAILED.")

        print("\nALL FIVE ANOMALY TYPES WERE CORRECTLY DETECTED.")

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
