import csv
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect

from app.config import PROJECT_ROOT, settings
from app.database.connection import FullSessionLocal
from app.database.base import Base

# Register all SQLAlchemy models.
from app.database import models  # noqa: F401


EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "full_scale"
BATCH_SIZE = 10_000


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


def export_table(db, table_name, table):
    csv_path = EXPORT_DIR / f"{table_name}.csv"
    jsonl_path = EXPORT_DIR / f"{table_name}.jsonl"

    statement = table.select().order_by(*table.primary_key.columns)

    result = db.execute(statement.execution_options(stream_results=True))
    columns = [column.name for column in table.columns]

    row_count = 0

    with (
        csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file,
        jsonl_path.open("w", encoding="utf-8") as jsonl_file,
    ):
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()

        while True:
            batch = result.mappings().fetchmany(BATCH_SIZE)

            if not batch:
                break

            for row in batch:
                record = {
                    column: serialize_value(value)
                    for column, value in row.items()
                }

                writer.writerow(record)
                jsonl_file.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

                row_count += 1

            if row_count and row_count % 100_000 == 0:
                print(f"  {table_name}: {row_count:,} rows exported")

    result.close()

    return {
        "row_count": row_count,
        "csv_file": csv_path.name,
        "jsonl_file": jsonl_path.name,
        "csv_sha256": calculate_sha256(csv_path),
        "jsonl_sha256": calculate_sha256(jsonl_path),
    }


def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    db = FullSessionLocal()

    manifest = {
        "dataset": "SchoolRoute AI full-scale synthetic dataset",
        "random_seed": settings.RANDOM_SEED,
        "source_database": "schoolroute_full.db",
        "export_formats": ["csv", "jsonl"],
        "batch_size": BATCH_SIZE,
        "tables": {},
    }

    try:
        inspector = inspect(db.bind)
        table_names = sorted(inspector.get_table_names())

        print("\nSCHOOLROUTE AI FULL-SCALE DATA EXPORT")
        print("=" * 60)
        print(f"Database: schoolroute_full.db")
        print(f"Batch size: {BATCH_SIZE:,}")
        print(f"Tables: {len(table_names)}")
        print("=" * 60)

        for table_name in table_names:
            table = Base.metadata.tables[table_name]

            print(f"\nExporting {table_name}...")

            manifest["tables"][table_name] = export_table(
                db,
                table_name,
                table,
            )

            print(
                f"Completed: "
                f"{manifest['tables'][table_name]['row_count']:,} rows"
            )

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

        print("\n" + "=" * 60)
        print("FULL-SCALE EXPORT COMPLETED")
        print("=" * 60)
        print(f"Tables: {manifest['total_tables']}")
        print(f"Rows: {manifest['total_rows']:,}")
        print(f"Output: {EXPORT_DIR}")
        print("Formats: CSV and JSON Lines")
        print("Checksums: SHA-256")

    finally:
        db.close()


if __name__ == "__main__":
    main()
