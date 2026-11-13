import gzip
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import PROJECT_ROOT, settings

SOURCE_DB = PROJECT_ROOT / "schoolroute_full.db"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "full_scale"
OUTPUT_FILE = EXPORT_DIR / "schoolroute_full.sql.gz"
MANIFEST_FILE = EXPORT_DIR / "sql_export_manifest.json"


def calculate_sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Database not found: {SOURCE_DB}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        f"file:{SOURCE_DB.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        connection.execute("PRAGMA query_only = ON")

        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        table_counts = {}

        for (table_name,) in tables:
            quoted_name = '"' + table_name.replace('"', '""') + '"'
            count = connection.execute(
                f"SELECT COUNT(*) FROM {quoted_name}"
            ).fetchone()[0]
            table_counts[table_name] = count

        print("\nSCHOOLROUTE AI SQL EXPORT")
        print("=" * 55)
        print(f"Source: {SOURCE_DB.name}")
        print(f"Tables: {len(table_counts)}")
        print(f"Records: {sum(table_counts.values()):,}")
        print("Format: Compressed SQLite SQL dump")
        print("=" * 55)

        with OUTPUT_FILE.open("wb") as raw_file:
            with gzip.GzipFile(
                fileobj=raw_file,
                mode="wb",
                filename="",
                mtime=0,
            ) as compressed_file:
                with io.TextIOWrapper(
                    compressed_file,
                    encoding="utf-8",
                    newline="\n",
                ) as sql_file:

                    for statement in connection.iterdump():
                        sql_file.write(statement + "\n")

        checksum = calculate_sha256(OUTPUT_FILE)

        manifest = {
            "dataset": "SchoolRoute AI full-scale synthetic dataset",
            "source_database": SOURCE_DB.name,
            "random_seed": settings.RANDOM_SEED,
            "format": "SQLite SQL dump compressed with gzip",
            "file": OUTPUT_FILE.name,
            "compression": "gzip",
            "tables": table_counts,
            "total_tables": len(table_counts),
            "total_rows": sum(table_counts.values()),
            "file_size_bytes": OUTPUT_FILE.stat().st_size,
            "sha256": checksum,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        MANIFEST_FILE.write_text(
            json.dumps(manifest, indent=4),
            encoding="utf-8",
        )

        print("\nSQL EXPORT COMPLETED")
        print("=" * 55)
        print(f"Tables: {len(table_counts)}")
        print(f"Records: {manifest['total_rows']:,}")
        print(
            f"Compressed size: "
            f"{manifest['file_size_bytes'] / (1024 * 1024):.2f} MB"
        )
        print(f"SHA-256: {checksum}")
        print(f"SQL file: {OUTPUT_FILE}")
        print(f"Manifest: {MANIFEST_FILE}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
