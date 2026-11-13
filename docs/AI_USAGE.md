# AI Usage and Prompt History

## 1. Purpose

AI-assisted development was used during the design, implementation, debugging, testing, and documentation of SchoolRoute AI.

The developer remains responsible for reviewing generated code, running it locally, validating database state, and checking the final behavior.

## 2. AI-assisted development activities

AI assistance supported the following activities:

- Relational database design and SQLAlchemy model development.
- Synthetic master-data generation and reproducibility.
- Geographic grouping and school-bus assignment logic.
- OR-Tools route-stop optimization and pickup-window scheduling.
- Attendance-event and guardian-notification simulation.
- Historical bus-capacity and route-disruption event services.
- SQL queries for data integrity and operational validation.
- Automated test design, implementation, and debugging.
- FastAPI endpoint and Streamlit dashboard development.
- SQL export, restoration verification, and documentation.

## 3. Human review and verification

AI-generated suggestions were not treated as proof of correctness.

The developer executed the project locally and reviewed:

- Database table and record counts.
- Primary-key and foreign-key integrity.
- Bus capacity and accessibility constraints.
- Student assignment consistency.
- Approved stops and pickup-window feasibility.
- Attendance and notification relationships.
- Event-history lifecycle and route status.
- Automated pytest results.
- SQLite database integrity and SQL restoration.

The automated pytest suite contains 19 passing tests:

- 10 data-validator tests.
- 9 event-service tests.

The tests use isolated in-memory SQLite databases. Additional full-scale database checks were executed separately and are not all represented as automated pytest tests.

The starter and full-scale databases were also validated separately. The latest recorded runs passed 2,450 and 2,065,978 checks respectively, with zero errors and zero warnings.

## 4. Prompt history

AI tools were used throughout development. However, a complete verbatim chronological archive of all prompts from the original AI conversations and other AI tools has not yet been reconstructed.

No reconstructed prompts are presented as original historical prompts. The repository therefore does not claim to contain a complete prompt transcript.

Where original prompts are recovered, they should be appended below in their original wording and chronological order.

### Prompt log

*Complete historical prompt archive: not yet available.*

## 5. Limitations

- AI-generated code may contain errors and requires testing and human review.
- Synthetic validation does not establish production readiness.
- Route travel times use geographic approximations rather than live road-network data.
- Guardian notifications are simulated and are not delivered to real contacts.
- Automated tests cover validator rules and event-service operations, but broader generator, API, dashboard, and end-to-end integration coverage remains incomplete.
- Independent full-scale regeneration and checksum comparison remain future verification work.
- The developer is responsible for final design decisions, code review, and submission.
