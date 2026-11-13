from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_full_db
from app.database.models import (
    AddressZone,
    Student,
    GuardianContact,
    Stop,
    Bus,
    Driver,
    Route,
    RouteStop,
    Assignment,
    AttendanceEvent,
    Notification,
    BusCapacityEvent,
    RouteDisruptionEvent,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_full_db)):
    """Return aggregate statistics from the full-scale database."""

    counts = {
        "address_zones": db.query(AddressZone).count(),
        "students": db.query(Student).count(),
        "guardian_contacts": db.query(GuardianContact).count(),
        "stops": db.query(Stop).count(),
        "buses": db.query(Bus).count(),
        "drivers": db.query(Driver).count(),
        "routes": db.query(Route).count(),
        "route_stops": db.query(RouteStop).count(),
        "assignments": db.query(Assignment).count(),
        "attendance_events": db.query(AttendanceEvent).count(),
        "notifications": db.query(Notification).count(),
        "bus_capacity_events": db.query(BusCapacityEvent).count(),
        "route_disruption_events": db.query(RouteDisruptionEvent).count(),
    }

    return {
        "success": True,
        "database": "full-scale",
        "summary": counts,
        "total_records": sum(counts.values()),
    }
