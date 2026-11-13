# SchoolRoute AI — Database Schema and Data Dictionary

## 1. Overview

SchoolRoute AI uses SQLite with SQLAlchemy ORM.

The schema contains 13 tables covering geographic master data, students,
guardian contacts, transport resources, routes, assignments, attendance,
notifications, and historical operational events.

The database uses primary keys, foreign keys, unique constraints, and
check constraints. Application-level validation adds business rules that
are not enforced directly by the database.

All generated personal names, addresses, phone numbers, email addresses,
vehicle registrations, and licence numbers are synthetic.

### Data type conventions

The types below describe the SQLAlchemy model declarations:

- `String(n)`: variable-length string with declared maximum length.
- `Integer`: integer value.
- `Float`: floating-point numeric value.
- `Boolean`: Boolean value.
- `Date`: calendar date.
- `DateTime(timezone=True)`: timezone-aware datetime declaration.
- `Text`: text without a declared application-level length limit.

`NOT NULL` means the field is required by the database. `NULL` means
the field is optional.

Defaults declared through SQLAlchemy's Python-side `default` argument
are applied by SQLAlchemy when inserting records. They are not necessarily
database-server defaults.

## 2. Tables and relationships

| Table | Primary key | Foreign keys | Purpose |
|---|---|---|---|
| address_zones | zone_id | — | Geographic service zones |
| students | student_id | address_zone_id → address_zones.zone_id | Student master records |
| guardian_contacts | guardian_id | student_id → students.student_id | Guardian contact records |
| stops | stop_id | address_zone_id → address_zones.zone_id | Pickup locations |
| buses | bus_id | — | Vehicle records and current capacity |
| drivers | driver_id | — | Driver records |
| routes | route_id | bus_id → buses.bus_id; driver_id → drivers.driver_id | Route and resource assignments |
| route_stops | route_stop_id | route_id → routes.route_id; stop_id → stops.stop_id | Ordered route stops |
| assignments | assignment_id | student_id → students.student_id; route_id → routes.route_id; stop_id → stops.stop_id | Student transport assignments |
| attendance_events | attendance_event_id | student_id → students.student_id; assignment_id → assignments.assignment_id (optional) | Pickup and drop-off history |
| notifications | notification_id | student_id → students.student_id; guardian_id → guardian_contacts.guardian_id; attendance_event_id → attendance_events.attendance_event_id (optional) | Simulated guardian notifications |
| bus_capacity_events | capacity_event_id | bus_id → buses.bus_id | Capacity-change history |
| route_disruption_events | disruption_event_id | route_id → routes.route_id; affected_stop_id → stops.stop_id (optional) | Disruption and resolution history |

All declared foreign keys use `ON DELETE RESTRICT`.

## 3. Field-level data dictionary

### 3.1 address_zones

Purpose: Defines geographic service zones.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| zone_id | String(30) | Yes | Primary key | Unique zone identifier |
| zone_name | String(100) | Yes | — | Zone name |
| city | String(100) | Yes | — | City |
| postal_code | String(10) | Yes | — | Postal code or synthetic code |
| latitude | Float | Yes | — | Zone latitude, decimal degrees |
| longitude | Float | Yes | — | Zone longitude, decimal degrees |
| is_active | Boolean | Yes | `True` | Whether the zone is active |

Relationships: One zone can contain multiple students and multiple stops.

Database constraints: Primary key on `zone_id`.

### 3.2 students

Purpose: Stores student master records and transport requirements.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| student_id | String(20) | Yes | Primary key | Unique student identifier |
| first_name | String(80) | Yes | — | Student first name |
| last_name | String(80) | Yes | — | Student last name |
| grade | Integer | Yes | 1–12 | Student grade |
| address_zone_id | String(30) | Yes | FK to address_zones | Student service zone |
| synthetic_address | String(250) | Yes | — | Synthetic student address |
| latitude | Float | Yes | — | Student latitude, decimal degrees |
| longitude | Float | Yes | — | Student longitude, decimal degrees |
| requires_accessible_vehicle | Boolean | Yes | `False` | Whether accessible transport is required |
| address_is_approved | Boolean | Yes | `True` | Whether the address is approved |
| enrollment_status | String(20) | Yes | `active`, `inactive`, `graduated`, `suspended`; default `active` | Enrollment lifecycle status |
| created_at | DateTime(timezone=True) | Yes | `utc_now` | Record creation timestamp |

Database constraints:
- `grade` must be between 1 and 12.
- `enrollment_status` must be one of the four listed values.
- Foreign key to `address_zones.zone_id`.
- Index on `address_zone_id`.

Relationships: A student can have multiple guardian contacts, assignments,
and attendance events.

### 3.3 guardian_contacts

Purpose: Stores guardian contact details and notification preferences.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| guardian_id | String(20) | Yes | Primary key | Unique guardian contact identifier |
| student_id | String(20) | Yes | FK to students | Associated student |
| guardian_name | String(120) | Yes | — | Synthetic guardian name |
| synthetic_phone | String(25) | Yes | — | Synthetic phone contact |
| synthetic_email | String(150) | Yes | — | Synthetic email contact |
| relationship_type | String(30) | Yes | No database enum constraint | Relationship to student |
| preferred_channel | String(20) | Yes | `sms`, `email`, `push`; default `sms` | Preferred notification channel |
| is_valid | Boolean | Yes | `True` | Whether the contact is considered valid |
| is_primary | Boolean | Yes | `False` | Whether this is the primary guardian contact |

Database constraints:
- `preferred_channel` must be `sms`, `email`, or `push`.
- Foreign key to `students.student_id`.
- Index on `student_id`.

Relationship: One student can have multiple guardian contacts.
One guardian contact can be associated with multiple notifications.

### 3.4 stops

Purpose: Defines pickup locations and their accessibility and time windows.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| stop_id | String(20) | Yes | Primary key | Unique stop identifier |
| stop_name | String(120) | Yes | — | Stop name |
| address_zone_id | String(30) | Yes | FK to address_zones | Stop service zone |
| latitude | Float | Yes | — | Stop latitude, decimal degrees |
| longitude | Float | Yes | — | Stop longitude, decimal degrees |
| pickup_window_start | String(5) | Yes | Expected `HH:MM` | Pickup window start |
| pickup_window_end | String(5) | Yes | Expected `HH:MM` | Pickup window end |
| is_approved | Boolean | Yes | `True` | Whether the stop is approved |
| is_accessible | Boolean | Yes | `False` | Whether the stop supports accessibility needs |

Database constraints:
- Foreign key to `address_zones.zone_id`.
- Index on `address_zone_id`.
- No database check constraint validates coordinate ranges, time format,
  or pickup-window ordering.

Relationships: A stop can appear on multiple routes, assignments, and
disruption events.

### 3.5 buses

Purpose: Stores vehicle details and its current capacity information.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| bus_id | String(20) | Yes | Primary key | Unique bus identifier |
| registration_number | String(30) | Yes | Unique | Synthetic vehicle registration |
| capacity | Integer | Yes | Greater than zero | Current recorded passenger capacity |
| is_accessible | Boolean | Yes | `False` | Whether the bus supports accessible transport |
| operational_status | String(20) | Yes | `active`, `maintenance`, `retired`; default `active` | Vehicle operational status |
| capacity_effective_from | Date | Yes | — | Start date of the recorded capacity period |
| capacity_effective_to | Date | No | `NULL` | Optional end date of the recorded capacity period |

Database constraints:
- Unique registration number.
- Capacity must be greater than zero.
- Operational status must be `active`, `maintenance`, or `retired`.

Relationship: One bus can be associated with multiple routes and capacity
events.

Capacity history is also recorded in `bus_capacity_events`. The bus row
stores current capacity information; it does not independently preserve
a complete sequence of historical capacity periods.

### 3.6 drivers

Purpose: Stores driver information and licence validity.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| driver_id | String(20) | Yes | Primary key | Unique driver identifier |
| driver_name | String(120) | Yes | — | Synthetic driver name |
| synthetic_license_number | String(40) | Yes | Unique | Synthetic licence identifier |
| license_valid_until | Date | Yes | — | Licence expiry date |
| is_active | Boolean | Yes | `True` | Whether the driver is active |

Database constraints:
- Unique synthetic licence number.
- No database constraint automatically checks licence expiry or active
  status when a route is assigned.

Relationship: One driver can be associated with multiple routes.

### 3.7 routes

Purpose: Stores route definitions, assigned transport resources, and
route lifecycle information.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| route_id | String(30) | Yes | Primary key | Unique route identifier |
| bus_id | String(20) | Yes | FK to buses | Assigned bus |
| driver_id | String(20) | Yes | FK to drivers | Assigned driver |
| route_name | String(120) | Yes | — | Route display name |
| school_year | Integer | Yes | — | School year |
| estimated_duration_minutes | Integer | Yes | Greater than zero | Estimated route duration, minutes |
| total_distance_km | Float | Yes | Zero or greater | Route distance, kilometres |
| route_status | String(20) | Yes | `draft`, `active`, `disrupted`, `retired`; default `draft` | Route lifecycle status |
| effective_from | Date | Yes | — | Route effective start date |
| effective_to | Date | No | `NULL` | Optional route effective end date |

Database constraints:
- Route status must be one of the four listed values.
- Estimated duration must be greater than zero.
- Total distance must be zero or greater.
- Foreign keys to buses and drivers.
- Index on `bus_id`.

Relationships: One route has multiple route stops, assignments, and
disruption events.

### 3.8 route_stops

Purpose: Connects routes to stops and defines their sequence.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| route_stop_id | String(40) | Yes | Primary key | Unique route-stop record |
| route_id | String(30) | Yes | FK to routes | Associated route |
| stop_id | String(20) | Yes | FK to stops | Associated stop |
| sequence_number | Integer | Yes | Greater than zero | Stop order within route |
| estimated_arrival | String(5) | Yes | Expected `HH:MM` | Estimated arrival time |
| travel_time_from_previous_minutes | Integer | Yes | Zero or greater; default `0` | Travel time from previous stop, minutes |

Database constraints:
- Unique `(route_id, sequence_number)`.
- Unique `(route_id, stop_id)`.
- Sequence number must be greater than zero.
- Travel time must be zero or greater.
- Foreign keys to routes and stops.

Relationship: A route has multiple ordered route-stop records. A stop can
be included in multiple routes.

### 3.9 assignments

Purpose: Connects students to their assigned route and pickup stop.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| assignment_id | String(50) | Yes | Primary key | Unique assignment identifier |
| student_id | String(20) | Yes | FK to students | Assigned student |
| route_id | String(30) | Yes | FK to routes | Assigned route |
| stop_id | String(20) | Yes | FK to stops | Assigned pickup stop |
| school_year | Integer | Yes | — | School year |
| effective_from | Date | Yes | — | Assignment start date |
| effective_to | Date | No | `NULL` | Optional assignment end date |
| assignment_status | String(20) | Yes | `active`, `suspended`, `cancelled`, `completed`; default `active` | Assignment lifecycle status |

Database constraints:
- Unique `(student_id, school_year)`.
- Assignment status must be one of the four listed values.
- End date must be empty or greater than or equal to start date.
- Foreign keys to students, routes, and stops.
- Index on `route_id`.

Important: The uniqueness constraint applies regardless of assignment
status. A cancelled or completed assignment still occupies the
`(student_id, school_year)` unique key.

The database does not directly enforce that the assigned stop belongs
to the assigned route. This is checked by application-level validation.

Relationship: One assignment can have multiple attendance events.

### 3.10 attendance_events

Purpose: Records pickup and drop-off attendance events.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| attendance_event_id | String(40) | Yes | Primary key | Unique attendance event identifier |
| student_id | String(20) | Yes | FK to students | Associated student |
| assignment_id | String(50) | No | FK to assignments; `NULL` allowed | Associated assignment |
| service_date | Date | Yes | — | Date of transport service |
| event_type | String(20) | Yes | `pickup`, `dropoff` | Attendance event type |
| event_status | String(20) | Yes | `present`, `absent`, `missed_pickup`, `completed`, `not_applicable` | Attendance outcome |
| event_timestamp | DateTime(timezone=True) | Yes | `utc_now` | Event timestamp |
| notes | Text | No | `NULL` | Optional event notes |

Database constraints:
- Event type must be `pickup` or `dropoff`.
- Event status must be one of the five listed values.
- Foreign key to students.
- Optional foreign key to assignments.
- Indexes on `service_date` and `(student_id, service_date)`.

The database does not enforce compatibility between event type and
event status. For example, it does not independently prevent a pickup
event from being recorded with `completed`.

Application-level validation checks assignment/student consistency.

Relationship: One attendance event can be associated with multiple
notifications.

### 3.11 notifications

Purpose: Stores simulated guardian notification attempts.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| notification_id | String(30) | Yes | Primary key | Unique notification identifier |
| student_id | String(20) | Yes | FK to students | Associated student |
| guardian_id | String(20) | Yes | FK to guardian_contacts | Recipient guardian |
| attendance_event_id | String(40) | No | FK to attendance_events; `NULL` allowed | Associated attendance event |
| channel | String(20) | Yes | `sms`, `email`, `push` | Notification channel |
| message_type | String(40) | Yes | No database enum constraint | Notification purpose |
| notification_status | String(20) | Yes | `pending`, `sent`, `failed`; default `pending` | Notification lifecycle status |
| synthetic_recipient | String(150) | Yes | — | Synthetic recipient address or identifier |
| created_at | DateTime(timezone=True) | Yes | `utc_now` | Creation timestamp |
| sent_at | DateTime(timezone=True) | No | `NULL` | Simulated send timestamp |
| failure_reason | Text | No | `NULL` | Optional failure explanation |

Database constraints:
- Channel must be `sms`, `email`, or `push`.
- Notification status must be `pending`, `sent`, or `failed`.
- Foreign keys to students and guardian contacts.
- Optional foreign key to attendance events.
- Index on `student_id`.

The database does not directly enforce that the guardian and attendance
event belong to the same student as the notification. Application-level
validation checks these relationships.

No database check constraint enforces consistency between notification
status, `sent_at`, and `failure_reason`.

Notifications in the generated datasets are simulations. No external
SMS, email, or push provider is contacted.

### 3.12 bus_capacity_events

Purpose: Preserves bus capacity-change events.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| capacity_event_id | String(40) | Yes | Primary key | Unique capacity event identifier |
| bus_id | String(20) | Yes | FK to buses | Associated bus |
| previous_capacity | Integer | Yes | Greater than zero | Capacity before the change |
| new_capacity | Integer | Yes | Greater than zero and different from previous capacity | Capacity after the change |
| effective_from | Date | Yes | — | Effective date of the change |
| recorded_at | DateTime(timezone=True) | Yes | `utc_now` | Event recording timestamp |
| reason | String(250) | Yes | — | Reason for capacity change |
| changed_by | String(100) | Yes | `system` | Actor recorded for the change |

Database constraints:
- Previous capacity must be greater than zero.
- New capacity must be greater than zero.
- Previous and new capacity must differ.
- Foreign key to buses.
- Index on `(bus_id, effective_from)`.

The event table preserves the recorded previous and new capacity values.
The current bus record is updated separately by the event service.

### 3.13 route_disruption_events

Purpose: Records route disruptions and their resolution history.

| Field | Type | Required | Default / allowed values | Description |
|---|---|---|---|---|
| disruption_event_id | String(40) | Yes | Primary key | Unique disruption identifier |
| route_id | String(30) | Yes | FK to routes | Associated route |
| affected_stop_id | String(20) | No | FK to stops; `NULL` allowed | Optional affected stop |
| disruption_type | String(30) | Yes | `traffic`, `weather`, `vehicle_breakdown`, `road_closure`, `driver_unavailable`, `safety_incident`, `other` | Disruption category |
| severity | String(20) | Yes | `low`, `medium`, `high`, `critical` | Disruption severity |
| description | Text | Yes | — | Disruption description |
| started_at | DateTime(timezone=True) | Yes | `utc_now` | Disruption start timestamp |
| resolved_at | DateTime(timezone=True) | No | `NULL` | Optional resolution timestamp |
| status | String(20) | Yes | `active`, `resolved`, `cancelled`; default `active` | Disruption lifecycle status |
| resolution_notes | Text | No | `NULL` | Optional resolution notes |

Database constraints:
- Disruption type must be one of the seven listed values.
- Severity must be one of the four listed values.
- Status must be `active`, `resolved`, or `cancelled`.
- Resolution timestamp must be empty or greater than or equal to
  the start timestamp.
- Foreign key to routes.
- Optional foreign key to stops.
- Indexes on `(route_id, started_at)` and `status`.

Relationship: One route can have multiple disruption events. A stop can
be referenced by multiple disruption events.

## 4. Cardinality and relationship summary

- One address zone can contain many students.
- One address zone can contain many stops.
- One student can have multiple guardian contacts.
- One bus can serve multiple routes over time.
- One driver can operate multiple routes over time.
- One route can contain multiple ordered route stops.
- One stop can appear on multiple routes.
- One student can have at most one assignment per school year under
  the current unique constraint.
- One assignment can have multiple attendance events.
- One student can have multiple attendance events.
- One guardian can receive multiple notifications.
- One attendance event can be associated with multiple notifications.
- One bus can have multiple capacity-change events.
- One route can have multiple disruption events.
- One stop can be referenced by multiple disruption events.

All foreign-key relationships use restrictive deletion behaviour.
Referenced records cannot be deleted while dependent records remain.

## 5. Lifecycle states and operational rules

### Student enrollment

Allowed values:
- `active`
- `inactive`
- `graduated`
- `suspended`

### Bus operational status

Allowed values:
- `active`
- `maintenance`
- `retired`

### Route

Allowed values:
- `draft`
- `active`
- `disrupted`
- `retired`

A route disruption changes an active route to `disrupted`.
The event service restores the route to `active` after all active
disruption events have been resolved, provided the route is still
within its effective period.

### Assignment

Allowed values:
- `active`
- `suspended`
- `cancelled`
- `completed`

Effective dates represent the intended assignment period. The current
database uniqueness constraint permits only one assignment record per
student per school year, regardless of status.

### Attendance

Event types:
- `pickup`
- `dropoff`

Event statuses:
- `present`
- `absent`
- `missed_pickup`
- `completed`
- `not_applicable`

The database validates the allowed event types and statuses individually,
but does not enforce which status combinations are logically compatible
with each event type. The DataValidator checks these combinations.

### Notification

Channels:
- `sms`
- `email`
- `push`

Statuses:
- `pending`
- `sent`
- `failed`

Generated notifications are simulated records and do not represent
confirmed delivery through an external messaging provider.

### Route disruption event

Disruption statuses:
- `active`
- `resolved`
- `cancelled`

Disruption types:
- `traffic`
- `weather`
- `vehicle_breakdown`
- `road_closure`
- `driver_unavailable`
- `safety_incident`
- `other`

Severity values:
- `low`
- `medium`
- `high`
- `critical`

An active disruption retains its event record after resolution.
Resolution updates the event status, timestamp, and notes rather than
deleting the record.

### Bus capacity event

A capacity event records:
- Previous capacity.
- New capacity.
- Effective date.
- Reason for the change.
- Recording timestamp.
- Actor recorded as responsible for the change.

The event history is stored independently of the current bus capacity.

## 6. Key database constraints

The following constraints are defined in the SQLAlchemy models:

| Entity | Constraint |
|---|---|
| students | Grade between 1 and 12 |
| students | Enrollment status restricted to four defined values |
| guardian_contacts | Preferred channel restricted to sms, email, push |
| buses | Registration number unique |
| buses | Capacity greater than zero |
| buses | Operational status restricted to active, maintenance, retired |
| drivers | Synthetic licence number unique |
| routes | Route status restricted to four defined values |
| routes | Estimated duration greater than zero |
| routes | Total distance greater than or equal to zero |
| route_stops | Route and sequence number unique together |
| route_stops | Route and stop unique together |
| route_stops | Sequence number greater than zero |
| route_stops | Travel time from previous stop greater than or equal to zero |
| assignments | Student and school year unique together |
| assignments | Status restricted to active, suspended, cancelled, completed |
| assignments | End date empty or greater than or equal to start date |
| attendance_events | Event type restricted to pickup and dropoff |
| attendance_events | Event status restricted to five defined values |
| notifications | Channel restricted to sms, email, push |
| notifications | Status restricted to pending, sent, failed |
| bus_capacity_events | Previous and new capacities positive and different |
| route_disruption_events | Disruption type, severity, and status restricted to defined values |
| route_disruption_events | Resolution timestamp empty or not earlier than start timestamp |

Foreign keys are declared with `ON DELETE RESTRICT`.

### Important rules not enforced directly by database constraints

The following rules require application-level validation or service logic:

- Assigned stops must belong to their assigned routes.
- Student accessibility requirements must match bus and stop capabilities.
- Active passenger counts must not exceed applicable bus capacity.
- Driver licence validity and driver active status must be checked when
  assigning operational work.
- Bus operational status must be considered when selecting a vehicle.
- Student and stop coordinates should be within valid geographic ranges.
- Pickup-window values should have valid time formats and ordering.
- Guardian relationship types and notification message types do not have
  database enum constraints.
- Guardian and student ownership must match in notification records.
- Attendance event and student ownership must match in notification records.
- Attendance assignment and student ownership must match.
- Notification lifecycle timestamps and failure reasons require
  application-level consistency checks.
- Effective dates must be considered when evaluating historical assignments
  and capacity.

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
- Requires the caller to commit or roll back the transaction.

The capacity event preserves the previous and new values. The bus record
does not retain a complete historical sequence of capacity periods.
Future-dated changes should not be interpreted as a fully implemented
capacity-scheduling system.

### Report route disruption

`report_route_disruption(...)`

- Validates disruption type and severity.
- Requires a description.
- Checks that the route exists and is active or already disrupted.
- Records a `RouteDisruptionEvent`.
- Changes the route status to `disrupted`.

Multiple active disruptions can exist on the same route.

### Resolve route disruption

`resolve_route_disruption(...)`

- Requires resolution notes.
- Resolves an existing active disruption.
- Records the resolution timestamp and notes.
- Restores the route only when no other active disruptions remain and
  the route is still within its effective period.

Event records are retained.

## 8. Validation responsibilities

The `DataValidator` performs application-level checks in addition to
database constraints.

Validation areas include:

- Foreign-key references.
- Assignment-to-route-stop consistency.
- Assignment date validity.
- Active assignment counts and bus capacity.
- Accessibility requirements for buses and stops.
- Student address and pickup-stop approval.
- Route stop sequence and route timing.
- Attendance event and assignment consistency.
- Attendance event type and status combinations.
- Notification guardian, student, and attendance relationships.
- Notification contact validity and lifecycle fields.
- Bus capacity event values.
- Route disruption status, dates, and resolution details.

### Validation limitations

- Capacity validation does not fully reconstruct historical capacity
  periods and compare every assignment against the capacity effective
  on each service date.
- Not every possible business rule is covered by the validator.
- Automated tests cover selected valid and invalid scenarios, not every
  validation branch.
- Database constraints and application-level validation provide
  different layers of protection; passing one does not prove every
  possible business rule is satisfied.

## 9. Implementation status

Implemented:

- 13 SQLAlchemy database models.
- Primary keys, foreign keys, unique constraints, check constraints,
  and indexes.
- Bus capacity-change event model and service operation.
- Route disruption event model and report/resolve service operations.
- Support for multiple simultaneous route disruptions.
- Full-scale synthetic master data: 5,000 students, 6,239 guardian
  contacts, 300 approved stops, 100 buses, and 100 drivers.
- Full-scale route planning: 100 routes, 710 route stops, and
  5,000 student assignments.
- Geographic student grouping, approved-stop selection,
  accessibility-aware assignment, OR-Tools stop-path optimization,
  and pickup-window scheduling.
- Full-scale attendance generation: 2,000,000 attendance events
  over 200 weekdays.
- Simulated guardian notifications for absence and missed-pickup events.
- Capacity-change and route-disruption event history in the database.
- 10 automated data-validator tests using isolated in-memory SQLite.
- 9 automated event-service tests using isolated in-memory SQLite.
- 19 passing automated pytest tests.
- Separate full-scale SQL checks for route feasibility, assignment
  consistency, attendance/notification relationships, foreign keys,
  and SQLite integrity.
- FastAPI health and dashboard-summary endpoints.
- Streamlit administration dashboard for operational overview,
  master data, routes, students, attendance, and alerts.

## 10. Known limitations

- Geographic travel times use straight-line distance approximation and
  fixed average speed, not live road-network or traffic data.
- The generated school calendar excludes holiday modeling.
- Guardian notifications are simulated; no external SMS, email, or
  push provider is connected.
- Full-scale database checks have been executed, but not all are
  represented as automated pytest tests.
- Historical capacity periods are not fully reconstructed by the
  current capacity validator.
- Broader API, dashboard, generator, and end-to-end integration tests
  remain future work.
- Live GPS and production deployment workflows are not implemented.
- The full-scale generation workflow is composed of separate generator
  steps; it is not a single fully automated regeneration pipeline.
- Deterministic identifiers and seeded random inputs support
  reproducibility, but complete independent end-to-end regeneration
  has not been established.

## 11. Synthetic data and privacy

All generated records are synthetic demonstration data.

The project does not use real student or guardian personal information.
Synthetic phone numbers, email addresses, addresses, registrations,
and licence identifiers must not be interpreted as real contact or
identity information.
