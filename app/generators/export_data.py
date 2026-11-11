import csv
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect

from app.config import PROJECT_ROOT, settings
from app.database.connection import SessionLocal
from app.database.base import Base

# Import models so SQLAlchemy metadata knows all tables.
from app.database import models  # noqa: F401


EXPORT_DIR = PROJECT_ROOT / "data" / "exports"


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return value


def calculate_sha256(file_path):
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    manifest = {
        "dataset": "SchoolRoute AI clean baseline dataset",
        "random_seed": settings.RANDOM_SEED,
        "source_database": "schoolroute.db",
        "export_formats": ["csv", "json"],
        "tables": {},
    }

    try:
        inspector = inspect(db.bind)
        table_names = sorted(inspector.get_table_names())

        print("\nSCHOOLROUTE AI DATA EXPORT")
        print("=" * 55)

        for table_name in table_names:
            table = Base.metadata.tables[table_name]
            rows = db.execute(table.select().order_by(*table.primary_key.columns)).mappings().all()

            records = [
                {
                    column: serialize_value(value)
                    for column, value in row.items()
                }
                for row in rows
            ]

            # CSV export.
            csv_path = EXPORT_DIR / f"{table_name}.csv"

            with csv_path.open(
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[column.name for column in table.columns],
                )
                writer.writeheader()
                writer.writerows(records)

            # JSON export.
            json_path = EXPORT_DIR / f"{table_name}.json"

            json_path.write_text(
                json.dumps(records, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            manifest["tables"][table_name] = {
                "row_count": len(records),
                "csv_file": csv_path.name,
                "json_file": json_path.name,
                "csv_sha256": calculate_sha256(csv_path),
                "json_sha256": calculate_sha256(json_path),
            }

            print(f"{table_name:<22} {len(records):>8} rows")

        manifest["total_tables"] = len(table_names)
        manifest["total_rows"] = sum(
            item["row_count"]
            for item in manifest["tables"].values()
        )

        manifest_path = EXPORT_DIR / "manifest.json"

        manifest_path.write_text(
            json.dumps(manifest, indent=4),
            encoding="utf-8",
        )

        print("=" * 55)
        print(f"Tables exported: {manifest['total_tables']}")
        print(f"Total rows:      {manifest['total_rows']}")
        print(f"Output:          {EXPORT_DIR}")
        print("Manifest:        manifest.json")
        print("\nDATA EXPORT COMPLETED SUCCESSFULLY.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
