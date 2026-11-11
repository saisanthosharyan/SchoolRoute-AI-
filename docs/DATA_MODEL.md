# SchoolRoute AI — Database Schema

## Overview

The database uses SQLite and SQLAlchemy ORM.
Primary keys identify records. Foreign keys enforce referential integrity.
Historical operational changes will be represented as separate event records
rather than silently overwriting previous records.

## Tables and relationships

| Table | Primary key | Foreign keys | Purpose |
|---|---|---|---|
| address_zones | zone_id | — | Geographic service zones |
| students | student_id | address_zone_id → address_zones.zone_id | Student master records |
| guardian_contacts | guardian_id | student_id → students.student_id | Student guardian contacts |
| stops | stop_id | address_zone_id → address_zones.zone_id | Approved or unapproved pickup stops |
| buses | bus_id | — | Vehicle master records and capacity |
| drivers | driver_id | — | Driver master records |
| routes | route_id | bus_id → buses.bus_id; driver_id → drivers.driver_id | Bus routes and their lifecycle |
| route_stops | route_stop_id | route_id → routes.route_id; stop_id → stops.stop_id | Ordered stops on each route |
| assignments | assignment_id | student_id → students.student_id; route_id → routes.route_id; stop_id → stops.stop_id | Student-to-route/stop assignments |
| attendance_events | attendance_event_id | student_id → students.student_id; assignment_id → assignments.assignment_id (optional) | Pickup and drop-off events |
| notifications | notification_id | student_id → students.student_id; guardian_id → guardian_contacts.guardian_id; attendance_event_id → attendance_events.attendance_event_id (optional) | Simulated guardian notifications |

## Cardinality

- One address zone can contain many students.
- One address zone can contain many stops.
- One student can have multiple guardian contacts.
- One bus can serve multiple routes over time.
- One driver can operate multiple routes over time.
- One route has multiple ordered route stops.
- One stop can appear on multiple routes.
- One student can have one annual assignment under the current uniqueness constraint.
- One assignment can have multiple attendance events.
- One student can have multiple attendance events.
- One guardian can receive multiple notifications.
- One attendance event can be associated with multiple notifications.

## Optional relationships

- An attendance event may have no assignment reference.
- A notification may have no attendance event reference.
- A bus capacity end date may be empty when the capacity remains effective.

## Important constraints

- Student IDs: STU-000001
- Stop IDs: STOP-000001
- Bus IDs: BUS-000001
- Route IDs: ROUTE-2026-000001
- Assignment IDs: ASN-<student-id>-2026
- Notification IDs: NOT-2026-000001
- Student grades must be between 1 and 12.
- Bus capacity must be greater than zero.
- Route sequence numbers must be positive and unique within a route.
- Assignment end dates cannot precede their start dates.
- SQLite foreign-key enforcement is enabled.

## Validation responsibilities

Foreign keys enforce record references, but application-level validation
must additionally verify:

- Assigned stops belong to the corresponding route.
- Student accessibility needs match the assigned bus.
- Route passenger counts do not exceed effective bus capacity.
- Pickup windows and route arrival times are feasible.
- Guardian contacts are valid before notification simulation.
- Effective dates and lifecycle transitions are consistent.

## Planned extensions

The initial schema contains 11 core tables. Additional event-history tables
will be introduced for bus capacity changes and route disruptions so that
historical changes remain auditable.
