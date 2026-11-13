import gzip
import json
import sqlite3
import tempfile
from pathlib import Path

from app.config import PROJECT_ROOT

EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "full_scale"
SQL_FILE = EXPORT_DIR / "schoolroute_full.sql.gz"
MANIFEST_FILE = EXPORT_DIR / "sql_export_manifest.json"
TEMP_DIR = PROJECT_ROOT / "data" / "generated"


def main():
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print("\nSCHOOLROUTE AI SQL RESTORATION VERIFICATION")
    print("=" * 55)
    print("Restoring into a temporary database...")
    print("Original database will not be modified.")

    with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp:
        restored_db = Path(temp) / "restored_test.db"
        connection = sqlite3.connect(restored_db)
        cursor = connection.cursor()

        try:
            statement = ""

            with gzip.open(SQL_FILE, "rt", encoding="utf-8") as sql_file:
                for line in sql_file:
                    statement += line

                    if sqlite3.complete_statement(statement):
                        if statement.strip():
                            cursor.execute(statement)
                        statement = ""

            if statement.strip():
                raise RuntimeError("Incomplete SQL statement found.")

            connection.commit()
            connection.execute("PRAGMA foreign_keys = ON")

            tables = connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """).fetchall()

            actual_counts = {}

            for (table_name,) in tables:
                quoted = '"' + table_name.replace('"', '""') + '"'
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {quoted}"
                ).fetchone()[0]
                actual_counts[table_name] = count

            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_key_errors = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            expected_counts = manifest["tables"]
            counts_match = actual_counts == expected_counts

            print("\nRESTORATION RESULTS")
            print("=" * 55)
            print(f"Tables restored: {len(actual_counts)}")
            print(f"Records restored: {sum(actual_counts.values()):,}")
            print(f"Table counts match manifest: {counts_match}")
            print(f"Integrity check: {integrity}")
            print(f"Foreign key violations: {len(foreign_key_errors)}")

            success = (
                counts_match
                and integrity == "ok"
                and not foreign_key_errors
                and sum(actual_counts.values()) == manifest["total_rows"]
            )

            print("=" * 55)
            print("RESULT:", "PASSED" if success else "FAILED")

            if not success:
                if not counts_match:
                    print("Expected:", expected_counts)
                    print("Actual:", actual_counts)
                if foreign_key_errors:
                    print("Foreign key errors:", foreign_key_errors[:10])
                raise SystemExit(1)

        finally:
            connection.close()


if __name__ == "__main__":
    main()
