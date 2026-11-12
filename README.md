# SchoolRoute AI

**AI-assisted school transportation data generation, validation, anomaly detection, and route-planning foundation.**

SchoolRoute AI is a school transportation management and optimization project designed around realistic synthetic operational data. It models students, guardians, school zones, bus stops, buses, drivers, routes, assignments, attendance events, and notifications.

The project focuses on building a reliable data foundation, validating transportation constraints, identifying operational anomalies, and developing toward an optimized school transportation workflow.

> **Project status:** Active development. The database schema, synthetic data generators, baseline operations generator, attendance generation, data export, and anomaly validation are implemented. Full-scale operational processing, optimization integration, API, dashboard, and automated test coverage remain under development.

---

## 1. Objectives

- Generate reproducible synthetic school transportation datasets.
- Maintain relational integrity across transportation entities.
- Model student assignments, buses, drivers, stops, and routes.
- Represent daily pickup and drop-off attendance.
- Validate capacity, accessibility, route timing, and contact constraints.
- Inject controlled operational anomalies.
- Keep anomaly ground-truth labels separate from validation inputs.
- Export structured CSV and JSON datasets with integrity manifests.
- Build toward constraint-aware route optimization.

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
|   |   +-- attendance.py
|   |   +-- anomaly_data.py
|   |   +-- export_data.py
|   +-- services/
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
+-- prompts/
+-- scripts/
|   +-- validate_anomalies.py
+-- tests/
|
+-- .env.example
+-- .gitignore
+-- requirements.txt
```

## 4. Database Design

The relational database currently contains 11 entities.

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

Primary keys, foreign keys, relationships, and validation responsibilities are documented in [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

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

The operational and attendance datasets are separate generation stages. Their full-scale completion is still in progress.

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

Generate attendance events:

```powershell
python -m app.generators.attendance
```

Generate full-scale master data in the separate full-scale database:

```powershell
python -m app.generators.full_master_data
```

**Important:** Generators are staged workflows. Do not run a generator repeatedly against an already-populated database unless its implementation explicitly supports that operation. The master-data generators check for existing data.

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

## 8. Anomaly Detection

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

## 9. Data Export

Run:

```powershell
python -m app.generators.export_data
```

The export generator produces CSV and JSON files for the database tables and a manifest containing:

- Random seed.
- Source database.
- Export formats.
- Row counts.
- SHA-256 file hashes.

Generated exports are stored under `data/exports/` and excluded from Git by default.

## 10. Configuration

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

## 11. Reproducibility and Data Integrity

The project uses a fixed random seed for repeatable synthetic generation.

Export manifests include SHA-256 checksums to support file-integrity verification.

Anomaly ground truth is maintained separately from the anomaly database to avoid using expected labels as validation inputs.

The synthetic dataset is intended for development, testing, and demonstration rather than real-world transportation decisions.

## 12. Current Limitations

The following work remains in progress:

- Full-scale route and assignment generation.
- OR-Tools integration into the end-to-end routing workflow.
- Historical bus-capacity and route-disruption event modeling.
- Full-scale attendance and notification generation.
- Expanded automated tests.
- API endpoints and dashboard implementation.
- End-to-end workflow and performance validation.

The current baseline operations generator is a starter implementation and should not be interpreted as a completed production-grade optimization engine.

## 13. Development Roadmap

- [x] Relational database foundation.
- [x] Eleven core database entities.
- [x] Starter synthetic master data.
- [x] Full-scale synthetic master data.
- [x] Starter operations and assignments.
- [x] Attendance event generation.
- [x] Data validation.
- [x] Controlled anomaly injection.
- [x] Separate anomaly ground truth.
- [x] CSV and JSON export with SHA-256 manifest.
- [ ] Full-scale operations generation.
- [ ] Constraint-based route optimization.
- [ ] Historical operational event modeling.
- [ ] Full-scale attendance and notifications.
- [ ] Automated test suite.
- [ ] API and dashboard.
- [ ] End-to-end validation.

## 14. Responsible AI Development

AI-assisted development tools may be used during implementation. Generated code and suggestions must be reviewed, tested, and validated.

The project aims to make its data assumptions, limitations, validation results, and development process transparent.

---

**Repository:** [SchoolRoute-AI-](https://github.com/saisanthosharyan/SchoolRoute-AI-)

**Status:** Active development.

