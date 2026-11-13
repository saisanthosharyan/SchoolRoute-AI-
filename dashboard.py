import streamlit as st
import pandas as pd
from sqlalchemy import func, or_

from app.database.connection import FullSessionLocal
from app.database.models import (
    AddressZone, Student, GuardianContact, Stop, Bus, Driver,
    Route, RouteStop, Assignment, AttendanceEvent, Notification,
    BusCapacityEvent, RouteDisruptionEvent
)

st.set_page_config(
    page_title="SchoolRoute AI | Admin",
    page_icon="🚌",
    layout="wide"
)

def get_db():
    return FullSessionLocal()

def get_counts():
    db = get_db()
    try:
        models = {
            "Address Zones": AddressZone,
            "Students": Student,
            "Guardians": GuardianContact,
            "Stops": Stop,
            "Buses": Bus,
            "Drivers": Driver,
            "Routes": Route,
            "Route Stops": RouteStop,
            "Assignments": Assignment,
            "Attendance Events": AttendanceEvent,
            "Notifications": Notification,
            "Capacity Events": BusCapacityEvent,
            "Disruption Events": RouteDisruptionEvent,
        }
        return {name: db.query(model).count() for name, model in models.items()}
    finally:
        db.close()

def show_overview():
    st.header("Operational Overview")
    counts = get_counts()

    columns = st.columns(4)
    for col, label in zip(columns, ["Students", "Buses", "Routes", "Assignments"]):
        col.metric(label, f'{counts[label]:,}')

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Database Records")
        df = pd.DataFrame(
            list(counts.items()),
            columns=["Record Type", "Records"]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.subheader("System Health")
        st.metric("Total Records", f'{sum(counts.values()):,}')
        st.metric("Attendance Events", f'{counts["Attendance Events"]:,}')
        st.metric("Notifications", f'{counts["Notifications"]:,}')

        db = get_db()
        try:
            active_disruptions = db.query(RouteDisruptionEvent).filter(
                RouteDisruptionEvent.status == "active"
            ).count()
            st.metric("Active Route Disruptions", active_disruptions)
        finally:
            db.close()

def show_routes():
    st.header("Route Management")
    db = get_db()
    try:
        rows = (
            db.query(Route, Bus, Driver)
            .join(Bus, Route.bus_id == Bus.bus_id)
            .join(Driver, Route.driver_id == Driver.driver_id)
            .order_by(Route.route_id)
            .limit(200)
            .all()
        )

        data = []
        for route, bus, driver in rows:
            stop_count = db.query(RouteStop).filter(
                RouteStop.route_id == route.route_id
            ).count()

            data.append({
                "Route ID": route.route_id,
                "Route Name": route.route_name,
                "Bus": bus.registration_number,
                "Capacity": bus.capacity,
                "Driver": driver.driver_name,
                "Stops": stop_count,
                "Duration (min)": route.estimated_duration_minutes,
                "Distance (km)": route.total_distance_km,
                "Status": str(route.route_status),
            })

        st.metric("Routes displayed", len(data))
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    finally:
        db.close()

def show_students():
    st.header("Student Directory")
    search = st.text_input("Search by student ID or name")

    db = get_db()
    try:
        query = db.query(Student)

        if search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.student_id.ilike(term),
                    Student.first_name.ilike(term),
                    Student.last_name.ilike(term),
                )
            )

        students = query.order_by(Student.student_id).limit(100).all()

        data = []
        for student in students:
            assignment = db.query(Assignment).filter(
                Assignment.student_id == student.student_id,
                Assignment.assignment_status == "active"
            ).first()

            data.append({
                "Student ID": student.student_id,
                "Name": f"{student.first_name} {student.last_name}",
                "Grade": student.grade,
                "Zone": student.address_zone_id,
                "Accessible Vehicle Required": student.requires_accessible_vehicle,
                "Enrollment": str(student.enrollment_status),
                "Assignment": assignment.assignment_id if assignment else "Unassigned",
                "Route": assignment.route_id if assignment else "—",
            })

        st.caption(f"Showing up to 100 matching students. Found: {len(data)}")
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    finally:
        db.close()

def show_attendance():
    st.header("Attendance Analytics")
    db = get_db()
    try:
        date_range = db.query(
            func.min(AttendanceEvent.service_date),
            func.max(AttendanceEvent.service_date)
        ).first()

        if not date_range or not date_range[0]:
            st.info("No attendance data available.")
            return

        selected_date = st.date_input(
            "Select school date",
            value=date_range[0],
            min_value=date_range[0],
            max_value=date_range[1]
        )

        events = db.query(
            AttendanceEvent.event_type,
            AttendanceEvent.event_status,
            func.count(AttendanceEvent.attendance_event_id)
        ).filter(
            AttendanceEvent.service_date == selected_date
        ).group_by(
            AttendanceEvent.event_type,
            AttendanceEvent.event_status
        ).all()

        if not events:
            st.warning("No attendance records found for this date.")
            return

        total = sum(row[2] for row in events)
        st.metric("Attendance Events on Selected Date", f"{total:,}")

        df = pd.DataFrame(
            events,
            columns=["Event Type", "Event Status", "Count"]
        )
        st.subheader("Attendance Breakdown")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Recent Attendance Records")
        recent = db.query(AttendanceEvent).filter(
            AttendanceEvent.service_date == selected_date
        ).order_by(
            AttendanceEvent.event_timestamp.desc()
        ).limit(100).all()

        recent_df = pd.DataFrame([{
            "Event ID": e.attendance_event_id,
            "Student ID": e.student_id,
            "Type": str(e.event_type),
            "Status": str(e.event_status),
            "Timestamp": e.event_timestamp,
            "Notes": e.notes,
        } for e in recent])

        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    finally:
        db.close()

def show_alerts():
    st.header("Operational Alerts")
    db = get_db()
    try:
        st.subheader("Route Disruptions")
        disruptions = db.query(RouteDisruptionEvent).order_by(
            RouteDisruptionEvent.started_at.desc()
        ).limit(100).all()

        disruption_df = pd.DataFrame([{
            "Event ID": d.disruption_event_id,
            "Route": d.route_id,
            "Type": str(d.disruption_type),
            "Severity": str(d.severity),
            "Status": str(d.status),
            "Started": d.started_at,
            "Resolved": d.resolved_at,
            "Description": d.description,
        } for d in disruptions])

        if not disruption_df.empty:
            st.dataframe(disruption_df, use_container_width=True, hide_index=True)
        else:
            st.info("No route disruptions recorded.")

        st.divider()
        st.subheader("Bus Capacity History")
        capacity_events = db.query(BusCapacityEvent).order_by(
            BusCapacityEvent.recorded_at.desc()
        ).limit(100).all()

        capacity_df = pd.DataFrame([{
            "Event ID": e.capacity_event_id,
            "Bus": e.bus_id,
            "Previous Capacity": e.previous_capacity,
            "New Capacity": e.new_capacity,
            "Effective From": e.effective_from,
            "Reason": e.reason,
        } for e in capacity_events])

        if not capacity_df.empty:
            st.dataframe(capacity_df, use_container_width=True, hide_index=True)
        else:
            st.info("No capacity changes recorded.")

        st.divider()
        st.subheader("Recent Notification History")
        notifications = db.query(Notification).order_by(
            Notification.created_at.desc()
        ).limit(50).all()

        notification_df = pd.DataFrame([{
            "Notification ID": n.notification_id,
            "Student ID": n.student_id,
            "Channel": str(n.channel),
            "Message Type": str(n.message_type),
            "Status": str(n.notification_status),
            "Created": n.created_at,
            "Sent": n.sent_at,
        } for n in notifications])

        if not notification_df.empty:
            st.dataframe(notification_df, use_container_width=True, hide_index=True)
        else:
            st.info("No notifications recorded.")

    finally:
        db.close()

st.title("🚌 SchoolRoute AI")
st.caption("School Transportation Operations Platform")

with st.sidebar:
    st.title("SchoolRoute AI")
    st.caption("Administration Panel")
    page = st.radio(
        "Navigation",
        ["Overview", "Routes", "Students", "Attendance", "Alerts"]
    )
    st.divider()
    st.caption("Full-scale synthetic dataset")
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

if page == "Overview":
    show_overview()
elif page == "Routes":
    show_routes()
elif page == "Students":
    show_students()
elif page == "Attendance":
    show_attendance()
elif page == "Alerts":
    show_alerts()

st.divider()
st.caption("SchoolRoute AI | Local demonstration dashboard | Synthetic data only")
