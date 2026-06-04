"""LangChain tools cho triage agent: tìm chuyên khoa và truy vấn lịch trống."""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.specialty_knowledge import safe_search_specialties


@tool
def search_hospital_specialties(symptom_query: str, limit: int = 6) -> str:
    """Search the hospital specialty database for specialties matching patient symptoms."""
    try:
        with SessionLocal() as db:
            matches = safe_search_specialties(symptom_query, db=db, limit=limit)
    except SQLAlchemyError:
        matches = safe_search_specialties(symptom_query, limit=limit)

    return json.dumps({"candidates": matches}, ensure_ascii=False)


def _query_slots_from_db(specialty: str, date: Optional[str] = None) -> list[dict]:
    """Truy vấn DB để lấy danh sách lịch trống."""
    from app.db.models import AppointmentSlot

    db = SessionLocal()
    try:
        all_slots = (
            db.query(AppointmentSlot)
            .filter(AppointmentSlot.is_available == True)  # noqa: E712
            .all()
        )

        specialty_lower = specialty.lower().strip()
        matching = [
            s for s in all_slots
            if (
                specialty_lower in s.specialty_name.lower()
                or s.specialty_name.lower() in specialty_lower
                or _fuzzy_match(specialty_lower, s.specialty_name.lower())
            )
        ]

        if date:
            matching = [s for s in matching if s.slot_date == date]

        return [
            {
                "id": s.id,
                "specialty": s.specialty_name,
                "doctor": s.doctor_name or None,
                "date": s.slot_date,
                "time": s.slot_time,
            }
            for s in matching
        ]
    finally:
        db.close()


def _fuzzy_match(query: str, target: str) -> bool:
    keywords_map = {
        "tiêu hóa": ["gastro", "tieu hoa", "dạ dày", "da day", "ruột"],
        "tim mạch": ["cardio", "tim", "mach"],
        "thần kinh": ["neuro", "than kinh", "dau dau"],
        "cơ xương khớp": ["bone", "co xuong khop", "khớp", "xuong"],
        "da liễu": ["derm", "da lieu", "da"],
        "sản phụ khoa": ["obgyn", "san phu", "phu khoa", "san"],
        "tai mũi họng": ["ent", "tai", "mui", "hong"],
        "nội tổng quát": ["internal", "tong quat", "noi"],
    }
    for key, synonyms in keywords_map.items():
        if key in target or key in query:
            if any(s in query for s in synonyms) or any(s in target for s in synonyms):
                return True
    return False


@tool
def query_available_slots(specialty: str, date: Optional[str] = None) -> str:
    """
    Truy vấn lịch khám còn trống từ database của bệnh viện.

    Dùng tool này SAU KHI đã xác định được chuyên khoa phù hợp.

    Args:
        specialty: Tên chuyên khoa (ví dụ: "Nội - Tiêu Hóa").
        date: Ngày khám YYYY-MM-DD. Nếu không chỉ định, trả về tất cả ngày trống.
    """
    slots = _query_slots_from_db(specialty=specialty, date=date)

    if not slots:
        return (
            f"Không tìm thấy lịch trống cho chuyên khoa '{specialty}'"
            + (f" vào ngày {date}" if date else "")
            + ". Bệnh nhân có thể thử ngày khác hoặc chọn chuyên khoa tương tự."
        )

    lines = [f"Lịch trống cho {specialty}:"]
    for slot in slots[:6]:
        doc_info = f" — BS. {slot['doctor']}" if slot["doctor"] else ""
        lines.append(f"  • {slot['date']} lúc {slot['time']}{doc_info}")

    return "\n".join(lines)
