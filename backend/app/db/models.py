import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30))
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symptom_summary: Mapped[str] = mapped_column(Text)
    specialty: Mapped[str] = mapped_column(String(80))
    doctor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    appointment_date: Mapped[str] = mapped_column(String(20))
    appointment_time: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SpecialtyInfo(Base):
    __tablename__ = "specialties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Doctor(Base):
    """Bảng bác sĩ — được seed từ mock data khi khởi động."""

    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    specialty_name: Mapped[str] = mapped_column(String(160), index=True)


class AppointmentSlot(Base):
    """Bảng lịch trống — được seed từ mock data khi khởi động."""

    __tablename__ = "appointment_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doctor_id: Mapped[str] = mapped_column(String(36), index=True)
    doctor_name: Mapped[str] = mapped_column(String(120))
    specialty_name: Mapped[str] = mapped_column(String(160), index=True)
    slot_date: Mapped[str] = mapped_column(String(20), index=True)
    slot_time: Mapped[str] = mapped_column(String(10))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
