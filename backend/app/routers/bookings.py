from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Booking
from app.db.session import get_db
from app.schemas import BookingCreate, BookingOut

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> Booking:
    booking = Booking(
        patient_name=payload.patient.name,
        phone=payload.patient.phone,
        birth_year=payload.patient.birth_year,
        symptom_summary=payload.symptom_summary,
        specialty=payload.specialty,
        doctor=payload.doctor,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingOut])
def list_bookings(db: Session = Depends(get_db)) -> list[Booking]:
    return db.query(Booking).order_by(Booking.created_at.desc()).limit(20).all()
