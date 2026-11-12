# SchoolRoute AI

**AI-assisted school transportation data generation, validation, anomaly detection, and route-planning foundation.**

SchoolRoute AI is a school transportation management and optimization project designed around realistic synthetic operational data. It models students, guardians, school zones, bus stops, buses, drivers, routes, assignments, attendance events, and notifications.

The project focuses on building a reliable data foundation, validating transportation constraints, identifying operational anomalies, and developing an optimized school transportation workflow.

> **Project status:** Active development. The 13-table database schema, synthetic master data, full-scale route planning, student assignments, 200-day attendance generation, simulated notifications, operational event history, anomaly validation, CSV/JSON/JSONL exports, and initial automated tests are implemented. Broader automated testing, API, dashboard, and production integrations remain under development.

---

## 1. Objectives

- Generate reproducible synthetic school transportation datasets.
- Maintain relational integrity across transportation entities.
- Model student assignments, buses, drivers, stops, and routes.
- Represent daily pickup and drop-off attendance.
- Validate capacity, accessibility, route timing, and contact constraints.
- Inject controlled operational anomalies.
- Keep anomaly ground-truth labels separate from validation inputs.
- Export structured CSV, JSON, and JSONL datasets with integrity manifests.
- Build constraint-aware route optimization workflows.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data validation/configuration | Pydantic, Pydantic Settings |
| API foundation | FastAPI |
| Synthetic data | Faker |
| Data processing | NumPy, Pandas |
| Route optimization | Google OR-Tools |
| Dashboard foundation | Streamlit |
| Testing | Pytest, HTTPX |

## 3. Architecture

```text
SchoolRoute-AI/
|
+-- app/
|   +-- analytics/
|   +-- api/
|   |   +-- routes/
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
+-- dashboard/
+-- docs/
|   +-- DATA_MODEL.md
|   +-- AI_USAGE.md
+-- prompts/
+-- scripts/
|   +-- validate_anomalies.py
+-- tests/
|   +-- test_event_service.py
|
+-- .env.example
+-- .gitignore
+-- requirements.txt
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

Primary keys, foreign keys, relationships, cardinalities, lifecycle states, and validation responsibilities are documented in [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

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

The full-scale master-data generator has been executed successfully.

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

Generator scripts use dry-run defaults where applicable. Review their implementation before requesting database writes.

All generated people, addresses, and contact information are synthetic and must not be treated as real personal information.

## 6. Data Generation

Activate the virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

Generate full-scale master data in the separate full-scale database:

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

**Important:** Generators are staged workflows. Do not run a generator repeatedly against an already-populated database unless its implementation explicitly supports that operation. Some generators intentionally refuse to run when records already exist.

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

The current automated suite contains nine tests. Full-scale database integrity and operational checks have also been run separately; those checks are not yet all represented as automated pytest tests.

## 9. Anomaly Detection

The project includes controlled anomaly injection into a separate SQLite database.

Run:

```powershell
python -m app.generators.anomaly_data
```

Then run:

```powershell
python scripts/validate_anomalies.py
```

The current anomaly scenarios include:

1. Bus capacity exceeded.
2. Accessibility incompatibility.
3. Impossible route duration.
4. Invalid guardian contact notification.
5. Unapproved student address.

Ground-truth labels are stored separately:

`data/ground_truth/ground_truth.json`

The anomaly generator copies the clean starter database before injecting anomalies, preserving the original database.

A previous anomaly-validation run detected all five expected anomaly categories. The validator reported seven errors because two injected conditions affected more than one record.

## 10. Data Export

The starter exporter produces CSV and JSON files from the starter database:

```powershell
python -m app.generators.export_data
```

The full-scale exporter uses batched reads to handle the large database:

```powershell
python -m app.generators.export_full_data
```

The full-scale exporter generates:

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

Generated exports are stored under `data/exports/` and excluded from Git by default.

## 11. Configuration

Important environment variables:

| Variable | Default |
|---|---|
| APP_NAME | SchoolRoute AI |
| APP_VERSION | 1.0.0 |
| APP_ENV | development |
| DATABASE_URL | sqlite:///./schoolroute.db |
| RANDOM_SEED | 20261022 |

See `.env.example` for the configuration template.

The starter database and full-scale database are separate:

- `schoolroute.db`
- `schoolroute_full.db`

Database files and environment secrets are excluded from version control.

## 12. Reproducibility and Data Integrity

The project uses a fixed random seed for repeatable synthetic generation.

Export manifests include SHA-256 checksums to support file-integrity verification.

Anomaly ground truth is maintained separately from the anomaly database to avoid using expected labels as validation inputs.

The full-scale attendance generator uses deterministic random generation and batched inserts.

The synthetic dataset is intended for development, testing, and demonstration rather than real-world transportation decisions.

## 13. Current Limitations

The following work remains in progress:

- Automated pytest coverage for full-scale generators and end-to-end workflows.
- A reusable full-scale validation command that consolidates all database checks.
- API endpoints and dashboard implementation.
- Real-world traffic data, road-network travel times, and live GPS integration.
- Production notification-provider integration.
- School holiday calendars and more detailed operational scheduling.
- Further route-optimization improvements and performance benchmarking.

The full-scale routing workflow currently uses geographic clustering, approved-stop selection, and an OR-Tools travelling-salesperson path optimization.

Travel times are approximated using straight-line geographic distance and a fixed average speed. This is a synthetic planning model, not a production road-routing engine.

Guardian notifications are simulated; no real SMS, email, or push notification is sent.

The 200-day attendance calendar uses weekdays and does not model school holidays.

## 14. Development Roadmap

- [x] Relational database foundation.
- [x] Thirteen core database entities.
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
- [x] Historical capacity and route-disruption event models and services.
- [x] Full-scale capacity-change and route-disruption event history.
- [x] Initial automated event-service tests (9 tests).
- [x] Full-scale route, assignment, attendance, notification, event-history, foreign-key, and SQLite integrity checks (executed verification).
- [ ] Expanded automated test coverage for generators, validators, and end-to-end workflows.
- [ ] Consolidated automated end-to-end validation suite.
- [ ] API and dashboard.
- [ ] Production notification integration and live operational data.

## 15. Responsible AI Development

AI-assisted development tools may be used during implementation. Generated code and suggestions must be reviewed, tested, and validated.

The project aims to make its data assumptions, limitations, validation results, and development process transparent.

The AI-assisted development activities and verification approach are documented in `docs/AI_USAGE.md`. The chronological prompt history should be maintained using the actual prompts submitted during development.

---

**Repository:** [SchoolRoute-AI-](https://github.com/saisanthosharyan/SchoolRoute-AI-)

**Status:** Active development.