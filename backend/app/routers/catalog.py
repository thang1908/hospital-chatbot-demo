from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.specialty_knowledge import list_specialties

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
def read_catalog(db: Session = Depends(get_db)) -> dict:
    from app.db.models import Doctor
    from app.services.mock_catalog import SPECIALTIES

    doctors = [
        {"id": d.id, "name": d.name, "specialty": d.specialty_name}
        for d in db.query(Doctor).all()
    ]
    return {
        "specialties": SPECIALTIES,
        "doctors": doctors,
    }


@router.get("/slots")
def read_slots(
    specialty: str | None = None,
    date: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.db.models import AppointmentSlot
    from app.services.mock_catalog import get_slots as mock_get_slots

    query = db.query(AppointmentSlot).filter(AppointmentSlot.is_available == True)  # noqa: E712

    if specialty:
        specialty_lower = specialty.lower().strip()
        all_slots = query.all()
        matched = [
            s for s in all_slots
            if specialty_lower in s.specialty_name.lower()
            or s.specialty_name.lower() in specialty_lower
        ]
    else:
        matched = query.all()

    if date:
        matched = [s for s in matched if s.slot_date == date]

    if matched:
        return [
            {
                "id": s.id,
                "specialty": s.specialty_name,
                "doctor": s.doctor_name or None,
                "date": s.slot_date,
                "time": s.slot_time,
            }
            for s in matched
        ]

    # Fallback về mock data (luôn có ngày động từ hôm nay)
    return mock_get_slots(specialty=specialty, date=date)


@router.get("/doctors")
def read_doctors(
    specialty: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.db.models import Doctor

    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty_name.ilike(f"%{specialty}%"))

    return [
        {"id": d.id, "name": d.name, "specialty": d.specialty_name}
        for d in query.all()
    ]


@router.get("/specialties")
def read_specialties(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "description": item["description"],
        }
        for item in list_specialties(db)
    ]
