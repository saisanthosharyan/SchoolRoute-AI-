# SchoolRoute AI

**AI-assisted school transportation data generation, validation, anomaly detection, and route-planning system.**

SchoolRoute AI is a school transportation management and optimization prototype built around realistic synthetic operational data. It models students, guardians, geographic zones, approved bus stops, buses, drivers, routes, assignments, attendance events, notifications, and operational history.

The project focuses on reliable data generation, constraint-aware student-to-route assignment, transportation safety validation, attendance monitoring, anomaly detection, and traceable operational decisions.

> **Project status:** Functional prototype implemented. The 13-table relational database, full-scale synthetic dataset, route planning, student assignments, 200-day attendance simulation, simulated guardian notifications, operational event history, anomaly scenarios, validation, CSV/JSON/JSONL/SQL exports, FastAPI API, Streamlit administration dashboard, and initial automated tests are implemented. Expanded automated testing and production integrations remain future work.

---

## 1. Objectives

- Generate reproducible synthetic school transportation datasets.
- Maintain relational integrity across transportation entities.
- Model student assignments, buses, drivers, stops, and routes.
- Respect bus capacity and accessibility requirements.
- Represent daily pickup and drop-off attendance.
- Validate pickup windows, route timing, and approved stops.
- Simulate absences and missed pickups.
- Generate synthetic guardian notification records.
- Inject controlled operational anomalies.
- Keep anomaly ground-truth labels separate from validation inputs.
- Preserve operational changes as historical events.
- Export structured CSV, JSON, JSONL, and SQL data.
- Expose operational information through an API and administration dashboard.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data validation/configuration | Pydantic, Pydantic Settings |
| API | FastAPI |
| Synthetic data | Faker |
| Data processing | NumPy, Pandas |
| Route optimization | Google OR-Tools |
| Dashboard | Streamlit |
| Testing | Pytest, HTTPX |
| SQL export | SQLite, gzip |
| Version control | Git, GitHub |

## 3. Architecture

```text
SchoolRoute-AI/
|
+-- app/
|   +-- analytics/
|   +-- api/
|   |   +-- routes/
|   |       +-- dashboard.py
|   +-- database/
|   |   +-- base.py
|   |   +-- connection.py
|   |   +-- init_db.py
|   |   +-- models.py
|   +-- generators/
|   |   +-- master_data.py
|   |   +-- full_master_data.py
|   |   +-- operations.py
|   |   +-- full_operations.py
|   |   +-- attendance.py
|   |   +-- full_attendance.py
|   |   +-- anomaly_data.py
|   |   +-- export_data.py
|   |   +-- export_full_data.py
|   |   +-- export_sql.py
|   +-- services/
|   |   +-- event_service.py
|   +-- validators/
|       +-- data_validator.py
|
+-- data/
|   +-- generated/
|   +-- ground_truth/
|   +-- exports/
|
+-- docs/
|   +-- DATA_MODEL.md
|   +-- AI_USAGE.md
|
+-- scripts/
|   +-- validate_anomalies.py
|   +-- verify_sql_export.py
|
+-- tests/
|   +-- test_event_service.py
|
+-- dashboard.py
+-- .env.example
+-- .gitignore
+-- requirements.txt
+-- README.md
```

## 4. Database Design

The relational database currently contains 13 entities.

| Entity | Purpose |
|---|---|
| AddressZone | Synthetic geographic zones |
| Student | Student and transportation requirements |
| GuardianContact | Guardian contact details and preferences |
| Stop | Approved pickup and drop-off locations |
| Bus | Vehicle capacity and accessibility |
| Driver | Driver details and license validity |
| Route | Bus route and operational status |
| RouteStop | Ordered stops belonging to routes |
| Assignment | Student-to-route and stop assignment |
| AttendanceEvent | Pickup and drop-off attendance history |
| Notification | Guardian notification records |
| BusCapacityEvent | Historical bus capacity changes |
| RouteDisruptionEvent | Route disruption and resolution history |

Primary keys, foreign keys, relationships, cardinalities, optional relationships, lifecycle states, and validation responsibilities are documented in [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

The design uses explicit event records to preserve operational history instead of silently overwriting previous state.

## 5. Synthetic Dataset

The full-scale master-data generator uses a fixed random seed:

`20261022`

Configured full-scale targets:

| Dataset | Target |
|---|---:|
| Students | 5,000 |
| Guardian contacts | Generated per student |
| Address zones | 30 |
| Approved stops | 300 |
| Buses | 100 |
| Drivers | 100 |
| Accessible students | 400 |
| Accessible buses | 20 |
| School days | 200 |

The full-scale database has been populated with:

- 5,000 students.
- 6,239 guardian contacts.
- 30 address zones.
- 300 approved stops.
- 100 buses and 100 drivers.
- 100 generated routes.
- 710 route stops.
- 5,000 student assignments.
- 2,000,000 attendance events.
- 49,648 simulated guardian notifications.
- Historical bus capacity and route disruption events.

The full-scale database is generated locally as `schoolroute_full.db` and is excluded from Git.

All generated people, addresses, and contact information are synthetic. They must not be treated as real personal information.

## 6. Installation and Setup

### Prerequisites

- Python 3.12
- Git
- Windows PowerShell or a compatible terminal

Clone the repository:

```powershell
git clone https://github.com/saisanthosharyan/SchoolRoute-AI-.git
cd SchoolRoute-AI-
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create the environment configuration:

```powershell
Copy-Item .env.example .env
```

Initialize the starter database:

```powershell
python -m app.database.init_db
```

### Starter data generation

Generate starter master data:

```powershell
python -m app.generators.master_data
```

Generate starter operations:

```powershell
python -m app.generators.operations
```

Generate starter attendance events:

```powershell
python -m app.generators.attendance
```

### Full-scale data generation

Generate full-scale master data:

```powershell
python -m app.generators.full_master_data
```

Preview full-scale route planning:

```powershell
python -m app.generators.full_operations
```

Preview full-scale attendance generation:

```powershell
python -m app.generators.full_attendance
```

The full-scale route and attendance generators default to dry-run mode. Database-writing execution must be explicitly requested through their Python functions after reviewing the implementation.

**Important:** Generators are staged workflows. Do not run generators repeatedly against an already-populated database unless their implementation explicitly supports that operation. Some generators intentionally refuse to run when records already exist.

The existing full-scale database already contains the generated dataset. Do not regenerate it when following the API and dashboard instructions below.

## 7. Data Validation

Run the baseline data validator:

```powershell
python -m app.validators.data_validator
```

The validator checks operational constraints including:

- Primary-key uniqueness and foreign-key integrity.
- Student assignment consistency.
- Bus capacity.
- Accessibility compatibility.
- Approved pickup locations.
- Route-stop ordering.
- Route travel-time and duration consistency.
- Attendance event validity.
- Guardian notification consistency.

A previously executed starter-dataset validation produced:

| Result | Count |
|---|---:|
| Checks passed | 2,443 |
| Errors | 0 |
| Warnings | 0 |

These figures describe that specific validation run, not a guarantee for every future generated dataset.

Separate full-scale database checks also verified route, assignment, attendance, notification, event-history, foreign-key, and SQLite integrity constraints.

## 8. Automated Tests

The project includes nine automated event-service tests using an isolated in-memory SQLite database.

Run the test suite:

```powershell
python -m pytest -v
```

The tests cover:

- Bus capacity changes.
- Historical capacity event creation.
- Invalid capacity inputs.
- Route disruption creation.
- Multiple simultaneous disruptions.
- Invalid disruption inputs.
- Disruption resolution.
- Resolution lifecycle rules.

The tests use an isolated in-memory SQLite database and do not modify the starter or full-scale project databases.

The current automated suite contains nine tests. Full-scale database integrity and operational checks have also been executed separately; those checks are not yet all represented as automated pytest tests.

## 9. Anomaly Detection

The project includes controlled anomaly injection into a separate SQLite database.

Generate the anomaly dataset:

```powershell
python -m app.generators.anomaly_data
```

Run the anomaly validator:

```powershell
python scripts/validate_anomalies.py
```

If running the validator directly results in an import-path error, use:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/validate_anomalies.py
```

The five anomaly scenarios include:

1. Bus capacity exceeded.
2. Accessibility incompatibility.
3. Impossible route duration.
4. Invalid guardian contact notification.
5. Unapproved student address exposed.

Ground-truth labels are stored separately:

`data/ground_truth/ground_truth.json`

The anomaly generator copies the clean starter database before injecting anomalies, preserving the original database.

A previous anomaly-validation run detected all five expected anomaly categories. The validator reported seven errors because two injected conditions affected more than one record.

## 10. Data Export

### Starter export

The starter exporter produces CSV and JSON files from the starter database:

```powershell
python -m app.generators.export_data
```

### Full-scale CSV and JSONL export

The full-scale exporter uses batched reads to handle the large database:

```powershell
python -m app.generators.export_full_data
```

It generates:

- CSV files for all 13 database tables.
- JSON Lines (JSONL) files for all 13 database tables.
- A `manifest.json` file containing dataset metadata and integrity information.

**Verified full-scale export results:**

| Metric | Result |
|---|---:|
| Database tables | 13 |
| Total records | 2,067,229 |
| CSV files | 13 |
| JSONL files | 13 |
| Total data files | 26 |
| Batch size | 10,000 |
| Verification errors | 0 |

The manifest records:

- Random seed.
- Source database.
- Export formats.
- Batch size.
- Per-table row counts.
- SHA-256 file checksums.

All 26 exported files passed row-count and SHA-256 checksum verification with zero errors.

### Compressed SQL export

Generate a compressed SQL backup of the full-scale database:

```powershell
python -m app.generators.export_sql
```

The exporter uses read-only access to the source database and generates:

- `schoolroute_full.sql.gz`
- `sql_export_manifest.json`

The SQL manifest contains:

- Source database.
- Random seed.
- Table names and row counts.
- Total table and record counts.
- Compressed file size.
- SHA-256 checksum.
- Export timestamp.

### SQL restoration verification

Verify that the compressed SQL backup can recreate the database:

```powershell
python -m scripts.verify_sql_export
```

The verification script restores the SQL dump into a separate temporary SQLite database. It compares table counts with the export manifest and checks SQLite integrity and foreign-key relationships.

**Verified SQL restoration results:**

| Metric | Result |
|---|---:|
| Tables restored | 13 |
| Records restored | 2,067,229 |
| Table counts match manifest | Yes |
| SQLite integrity | `ok` |
| Foreign-key violations | 0 |
| Restoration verification | PASSED |
| Compressed SQL size | 14.74 MB |

SHA-256:

```text
6933a0eb1c139a27e86f63cf51b26eea42184ae540294dafeff3a5081d09dad1
```

The original full-scale database remains unchanged during restoration verification.

Generated exports are stored under `data/exports/` and excluded from Git by default.

## 11. FastAPI Application

The project includes a FastAPI application exposing a health endpoint and a full-scale dashboard summary endpoint.

Start the API:

```powershell
uvicorn app.main:app --reload
```

Available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Health status |
| GET | `/api/v1/dashboard/summary` | Full-scale database statistics |

Interactive API documentation:

`http://127.0.0.1:8000/docs`

The dashboard summary exposes record counts for all 13 database entities.

The API was tested using FastAPI TestClient. The root, health, and dashboard summary endpoints returned HTTP 200 with the expected full-scale record counts.

## 12. Streamlit Administration Dashboard

The project includes a Streamlit dashboard for inspecting synthetic school transportation operations.

Start the dashboard in another terminal:

```powershell
python -m streamlit run dashboard.py
```

Default address:

`http://localhost:8501`

The dashboard includes:

- **Overview:** students, buses, routes, assignments, and database statistics.
- **Routes:** route, bus, driver, stop, distance, duration, and status information.
- **Students:** student search and assignment information.
- **Attendance:** date-based pickup and drop-off attendance summaries.
- **Alerts:** route disruption history, bus capacity changes, and notification records.

Synthetic guardian contact information and student home addresses are deliberately excluded from the dashboard views.

The dashboard has been manually inspected using the populated full-scale database.

## 13. Configuration

Important environment variables:

| Variable | Default |
|---|---|
| APP_NAME | SchoolRoute AI |
| APP_VERSION | 1.0.0 |
| APP_ENV | development |
| DATABASE_URL | sqlite:///./schoolroute.db |
| RANDOM_SEED | 20261022 |

See `.env.example` for the configuration template.

The starter and full-scale databases are separate:

- `schoolroute.db`
- `schoolroute_full.db`

Database files and environment secrets are excluded from version control.

## 14. Reproducibility and Data Integrity

The project uses a fixed random seed for repeatable synthetic generation.

Export manifests include SHA-256 checksums to support file-integrity verification.

The full-scale CSV and JSONL export was verified using row counts and checksums for all 26 files.

The compressed SQL export was independently restored into a temporary SQLite database and verified against its manifest.

Anomaly ground truth is maintained separately from the anomaly database to avoid using expected labels as validation inputs.

The full-scale attendance generator uses deterministic random generation and batched inserts.

**Reproducibility limitation:** The existing full-scale export and SQL restoration have been verified, but two independent full-scale regeneration runs with a comparison of all resulting checksums have not yet been demonstrated. The project therefore does not claim that this acceptance criterion has been fully verified.

The synthetic dataset is intended for development, testing, and demonstration rather than real-world transportation decisions.

## 15. Current Limitations

The following limitations remain:

- Expanded automated pytest coverage for full-scale generators and end-to-end workflows.
- A consolidated automated validation suite.
- Independent full-scale regeneration and checksum comparison.
- Real-world traffic data, road-network travel times, and live GPS integration.
- Production notification-provider integration.
- School holiday calendars and more detailed operational scheduling.
- Further route-optimization improvements and performance benchmarking.

The full-scale routing workflow currently uses geographic clustering, approved-stop selection, and an OR-Tools travelling-salesperson path optimization.

Travel times are approximated using straight-line geographic distance and a fixed average speed. This is a synthetic planning model, not a production road-routing engine.

Guardian notifications are simulated; no real SMS, email, or push notification is sent.

The 200-day attendance calendar uses weekdays and does not model school holidays.

The project currently uses synthetic operational data and is not intended to make real-world student transportation decisions.

## 16. Development Roadmap

- [x] Relational database foundation.
- [x] Thirteen database entities.
- [x] Starter synthetic master data.
- [x] Full-scale synthetic master data.
- [x] Starter operations and assignments.
- [x] Full-scale operations generation for 5,000 students and 100 buses.
- [x] OR-Tools route-stop path optimization and pickup-window scheduling.
- [x] Attendance event generation.
- [x] Full-scale attendance generation: 2,000,000 events across 200 weekdays.
- [x] Simulated guardian notifications for absence and missed-pickup events.
- [x] Data validation.
- [x] Controlled anomaly injection.
- [x] Separate anomaly ground truth.
- [x] Starter CSV and JSON export with SHA-256 manifest.
- [x] Full-scale batched CSV and JSONL export for all 13 tables.
- [x] Verification of all 26 full-scale export files.
- [x] Compressed full-scale SQL export.
- [x] SQL restoration, row-count, SQLite integrity, and foreign-key verification.
- [x] Historical capacity and route-disruption event models and services.
- [x] Full-scale capacity-change and route-disruption event history.
- [x] Initial automated event-service tests (9 tests).
- [x] FastAPI application and dashboard summary endpoint.
- [x] Streamlit administration dashboard.
- [x] Executed full-scale route, assignment, attendance, notification, event-history, foreign-key, and SQLite integrity checks.
- [ ] Expanded automated test coverage for generators, validators, and end-to-end workflows.
- [ ] Consolidated automated end-to-end validation suite.
- [ ] Independent full-scale regeneration and checksum comparison.
- [ ] Production notification integration and live operational data.

## 17. Responsible AI Development

AI-assisted development tools may be used during implementation. Generated code and suggestions must be reviewed, tested, and validated.

The project aims to make its data assumptions, limitations, validation results, and development process transparent.

The AI-assisted development activities and verification approach are documented in `docs/AI_USAGE.md`.

The chronological AI prompt history should contain the actual prompts submitted during development. Do not represent reconstructed or generated prompts as original historical prompts.

---

**Repository:** [SchoolRoute-AI](https://github.com/saisanthosharyan/SchoolRoute-AI-)

**Implementation status:** Functional prototype completed; expanded automated testing, independent regeneration evidence, and production integrations remain future work.
