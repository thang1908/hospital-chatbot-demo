from app.db import models  # noqa: F401
from app.db.session import Base, SessionLocal, engine
from app.services.specialty_knowledge import seed_specialties


def seed_doctors_and_slots(db) -> None:
    """Seed bảng doctors và appointment_slots từ mock data nếu còn trống."""
    from app.db.models import AppointmentSlot, Doctor
    from app.services.mock_catalog import DOCTORS, SLOTS

    if db.query(Doctor).count() > 0:
        return  # Đã seed rồi, bỏ qua

    for doc in DOCTORS:
        db.add(Doctor(
            id=doc["id"],
            name=doc["name"],
            specialty_name=doc["specialty"],
        ))

    for slot in SLOTS:
        # Tìm doctor_id khớp với doctor name
        doctor_id = next(
            (d["id"] for d in DOCTORS if d["name"] == slot.get("doctor")),
            "unknown",
        )
        db.add(AppointmentSlot(
            id=slot["id"],
            doctor_id=doctor_id,
            doctor_name=slot.get("doctor") or "",
            specialty_name=slot["specialty"],
            slot_date=slot["date"],
            slot_time=slot["time"],
            is_available=True,
        ))

    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_specialties(db)
        seed_doctors_and_slots(db)

