# AI Usage and Prompt History

## 1. Purpose

AI-assisted development was used during the design, implementation, debugging, and documentation of SchoolRoute AI.

The developer remains responsible for reviewing generated code, running it locally, validating database state, and checking the final behavior.

## 2. AI-assisted development activities

AI assistance was used for the following project activities:

- Relational database design and SQLAlchemy model development.
- Synthetic master-data generation and reproducibility.
- Geographic grouping and school-bus assignment logic.
- OR-Tools route-stop optimization and pickup-window scheduling.
- Attendance-event and guardian-notification simulation.
- Historical bus-capacity and route-disruption event services.
- SQL queries for data integrity and operational validation.
- Automated test design and debugging.
- README and database-schema documentation.

## 3. Human review and verification

AI-generated suggestions were not treated as proof of correctness.

The developer executed the project locally and reviewed results, including:

- Database table and record counts.
- Primary-key and foreign-key integrity.
- Bus capacity and accessibility constraints.
- Student assignment consistency.
- Approved stops and pickup-window feasibility.
- Attendance and notification relationships.
- Event-history lifecycle and route status.
- Automated pytest results.
- SQLite database integrity.

The current automated test suite contains nine event-service tests. Additional full-scale database checks were executed separately.

## 4. Prompt history

The complete chronological prompt history must be retained from the original AI conversations and any other AI tools used during development.

This repository document is a project-level AI usage record, not a complete verbatim transcript of every historical prompt.

Append the original prompts below, preserving their wording and chronological order. Do not replace original prompts with reconstructed summaries.

### Prompt log

<!-- APPEND ORIGINAL PROMPTS BELOW THIS LINE -->

## 5. Limitations

- AI-generated code may contain errors and requires testing.
- Synthetic validation does not establish production readiness.
- Route travel times use geographic approximations rather than live road-network data.
- Guardian notifications are simulated and are not delivered to real contacts.
- The developer is responsible for final design decisions, code review, and submission.
