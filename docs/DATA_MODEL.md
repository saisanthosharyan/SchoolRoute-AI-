# SchoolRoute AI — Database Schema

## 1. Overview

The database uses SQLite and SQLAlchemy ORM.

The schema currently contains 13 tables covering master data, transportation
operations, attendance, notifications, and historical operational events.

Primary keys identify records. Foreign keys enforce referential integrity.
Operational changes are recorded as separate event records to preserve an
auditable history.

## 2. Tables and relationships

| Table | Primary key | Foreign keys | Purpose |
|---|---|---|---|
| address_zones | zone_id | — | Geographic service zones |
| students | student_id | address_zone_id → address_zones.zone_id | Student master records |
| guardian_contacts | guardian_id | student_id → students.student_id | Student guardian contacts |
| stops | stop_id | address_zone_id → address_zones.zone_id | Approved or unapproved pickup stops |
| buses | bus_id | — | Vehicle master records and current capacity |
| drivers | driver_id | — | Driver master records |
| routes | route_id | bus_id → buses.bus_id; driver_id → drivers.driver_id | Bus routes and lifecycle |
| route_stops | route_stop_id | route_id → routes.route_id; stop_id → stops.stop_id | Ordered stops on each route |
| assignments | assignment_id | student_id → students.student_id; route_id → routes.route_id; stop_id → stops.stop_id | Student-to-route/stop assignments |
| attendance_events | attendance_event_id | student_id → students.student_id; assignment_id → assignments.assignment_id (optional) | Pickup and drop-off event history |
| notifications | notification_id | student_id → students.student_id; guardian_id → guardian_contacts.guardian_id; attendance_event_id → attendance_events.attendance_event_id (optional) | Simulated guardian notifications |
| bus_capacity_events | capacity_event_id | bus_id → buses.bus_id | Historical bus capacity changes |
| route_disruption_events | disruption_event_id | route_id → routes.route_id; affected_stop_id → stops.stop_id (optional) | Route disruption and resolution history |

## 3. Cardinality

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
- One bus can have multiple capacity-change events.
- One route can have multiple disruption events.
- One stop can be referenced by multiple disruption events.

## 4. Optional relationships

- An attendance event may have no assignment reference.
- A notification may have no attendance event reference.
- A route disruption may have no affected stop when the disruption affects the entire route.
- A bus capacity end date may be empty when its current capacity period remains effective.
- A route effective end date may be empty when the route has no scheduled end date.
- A disruption resolution timestamp remains empty while the disruption is active.

## 5. Lifecycle states

### Route

Supported route statuses:

- `draft`
- `active`
- `disrupted`
- `retired`

A route disruption changes an active route to `disrupted`.
The route returns to `active` after all active disruption events for that
route have been resolved, provided its effective period has not ended.

### Assignment

Assignments use lifecycle status values defined by the model, including
active and inactive states. Effective dates determine when an assignment
applies.

### Route disruption event

Supported disruption statuses:

- `active`
- `resolved`
- `cancelled`

Supported disruption types:

- `traffic`
- `weather`
- `vehicle_breakdown`
- `road_closure`
- `driver_unavailable`
- `safety_incident`
- `other`

Supported severity values:

- `low`
- `medium`
- `high`
- `critical`

An active disruption must retain its event record after resolution.
Resolution updates the event status, resolution timestamp, and resolution
notes; it does not delete the event.

### Bus capacity event

A capacity event records:

- Previous capacity.
- New capacity.
- Effective date.
- Reason for the change.
- Recording timestamp.

Capacity history is retained independently of the bus's current capacity.

## 6. Important constraints

- Student IDs: `STU-000001`
- Stop IDs: `STOP-000001`
- Bus IDs: `BUS-000001`
- Route IDs: `ROUTE-2026-000001`
- Assignment IDs: `ASN-<student-id>-2026`
- Notification IDs: `NOT-2026-000001`
- Student grades must be between 1 and 12.
- Bus capacity must be greater than zero.
- Capacity event previous and new capacities must be positive and different.
- Route sequence numbers must be positive and unique within a route.
- Assignment end dates cannot precede their start dates.
- Disruption resolution timestamps cannot precede disruption start timestamps.
- SQLite foreign-key enforcement is enabled.

## 7. Event-service operations

Implemented in `app/services/event_service.py`.

### Change bus capacity

`change_bus_capacity(...)`

- Validates the requested capacity and effective date.
- Requires a non-empty reason.
- Checks that the bus exists.
- Checks active assignments against the proposed capacity.
- Creates a `BusCapacityEvent` record.
- Updates the bus's current capacity information.

The caller owns the database transaction and must commit or roll it back.

### Report route disruption

`report_route_disruption(...)`

- Validates the disruption type and severity.
- Requires a description.
- Checks that the route exists and is active or already disrupted.
- Records a new `RouteDisruptionEvent`.
- Changes the route status to `disrupted`.

Multiple active disruptions can exist on the same route.

### Resolve route disruption

`resolve_route_disruption(...)`

- Requires resolution notes.
- Resolves an existing active disruption.
- Records its resolution timestamp and notes.
- Restores the route only when no other active disruptions remain and the
  route is still within its effective period.

The event history is retained.

## 8. Validation responsibilities

Foreign keys enforce record references, but application-level validation
must additionally verify:

- Assigned stops belong to the corresponding route.
- Student accessibility needs match the assigned bus and stop.
- Route passenger counts do not exceed effective bus capacity.
- Pickup windows and route arrival times are feasible.
- Guardian contacts are valid before notification simulation.
- Effective dates and lifecycle transitions are consistent.
- Capacity changes do not reduce capacity below active assignments.
- Disruption types, severity, statuses, and resolution timestamps are valid.
- Historical event records remain linked to their source entities.

## 9. Implementation status

Implemented:

- 13 SQLAlchemy database models with foreign-key relationships and database constraints.
- Bus capacity-change event model and service operation with historical records.
- Route disruption event model and report/resolve service operations.
- Support for multiple simultaneous route disruptions.
- Full-scale synthetic master data: 5,000 students, 6,239 guardian contacts, 300 approved stops, 100 buses, and 100 drivers.
- Full-scale route planning: 100 routes, 710 route stops, and 5,000 student assignments.
- Geographic student grouping, approved-stop selection, accessibility-aware assignment, OR-Tools stop-path optimization, and pickup-window scheduling.
- Full-scale attendance generation: 2,000,000 attendance events over 200 weekdays.
- Simulated guardian notifications for absence and missed-pickup events.
- Capacity-change and route-disruption event history in the full-scale database.
- Nine automated event-service tests using an isolated in-memory SQLite database.
- Separate full-scale SQL checks for route feasibility, assignment consistency, attendance/notification relationships, foreign keys, and SQLite integrity.

Implementation limitations:

- Geographic travel times use a straight-line distance approximation and fixed average speed, not live road-network data.
- The generated school calendar excludes holiday modeling.
- Guardian notifications are simulated; no external SMS, email, or push provider is connected.
- Full-scale database checks have been executed, but not all are yet automated as pytest tests.
- API endpoints, dashboard, live GPS, and production deployment workflows are not yet implemented.
