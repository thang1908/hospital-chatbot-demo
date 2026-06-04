from __future__ import annotations

from datetime import date, timedelta

from app.services.specialty_knowledge import list_specialty_names, normalize_text

SPECIALTIES = list_specialty_names()

DOCTORS = [
    {"id": "dr-gastro-1", "name": "BS. Nguyen Minh An", "specialty": "Nội - Tiêu Hóa"},
    {"id": "dr-cardio-1", "name": "BS. Tran Hoang Nam", "specialty": "Nội - Tim Mạch"},
    {"id": "dr-internal-1", "name": "BS. Le Thu Ha", "specialty": "Khám nội tổng quát"},
    {"id": "dr-neuro-1", "name": "BS. Pham Duc Kien", "specialty": "Nội - Thần Kinh"},
    {"id": "dr-bone-1", "name": "BS. Do Quang Huy", "specialty": "Nội - Cơ Xương Khớp"},
    {"id": "dr-derm-1", "name": "BS. Vu Mai Linh", "specialty": "Da Liễu"},
    {"id": "dr-obgyn-1", "name": "BS. Nguyen Thu Trang", "specialty": "Sản - Phụ khoa"},
    {"id": "dr-ent-1", "name": "BS. Hoang Gia Bao", "specialty": "Tai Mũi Họng"},
]

# Ngày động: d1 = ngày mai, d2 = ngày kia
def _d(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()

SLOTS = [
    {"id": "slot-gastro-1", "date": _d(1), "time": "08:00", "specialty": "Nội - Tiêu Hóa", "doctor": "BS. Nguyen Minh An"},
    {"id": "slot-gastro-2", "date": _d(1), "time": "09:30", "specialty": "Nội - Tiêu Hóa", "doctor": "BS. Nguyen Minh An"},
    {"id": "slot-gastro-3", "date": _d(2), "time": "14:00", "specialty": "Nội - Tiêu Hóa", "doctor": "BS. Nguyen Minh An"},
    {"id": "slot-cardio-1", "date": _d(1), "time": "10:00", "specialty": "Nội - Tim Mạch", "doctor": "BS. Tran Hoang Nam"},
    {"id": "slot-cardio-2", "date": _d(2), "time": "15:00", "specialty": "Nội - Tim Mạch", "doctor": "BS. Tran Hoang Nam"},
    {"id": "slot-internal-1", "date": _d(1), "time": "08:30", "specialty": "Khám nội tổng quát", "doctor": "BS. Le Thu Ha"},
    {"id": "slot-internal-2", "date": _d(2), "time": "13:30", "specialty": "Khám nội tổng quát", "doctor": "BS. Le Thu Ha"},
    {"id": "slot-neuro-1", "date": _d(1), "time": "14:30", "specialty": "Nội - Thần Kinh", "doctor": "BS. Pham Duc Kien"},
    {"id": "slot-bone-1", "date": _d(2), "time": "09:00", "specialty": "Nội - Cơ Xương Khớp", "doctor": "BS. Do Quang Huy"},
    {"id": "slot-derm-1", "date": _d(1), "time": "15:30", "specialty": "Da Liễu", "doctor": "BS. Vu Mai Linh"},
    {"id": "slot-obgyn-1", "date": _d(2), "time": "10:30", "specialty": "Sản - Phụ khoa", "doctor": "BS. Nguyen Thu Trang"},
    {"id": "slot-ent-1", "date": _d(1), "time": "13:30", "specialty": "Tai Mũi Họng", "doctor": "BS. Hoang Gia Bao"},
    {"id": "slot-ent-2", "date": _d(1), "time": "15:00", "specialty": "Tai Mũi Họng", "doctor": "BS. Hoang Gia Bao"},
    {"id": "slot-ent-3", "date": _d(2), "time": "08:30", "specialty": "Tai Mũi Họng", "doctor": "BS. Hoang Gia Bao"},
]


def _generic_slots(specialty: str) -> list[dict]:
    slug = normalize_text(specialty).replace(" ", "-") or "specialty"
    return [
        {"id": f"slot-{slug}-fallback-1", "date": _d(1), "time": "11:00", "specialty": specialty, "doctor": None},
        {"id": f"slot-{slug}-fallback-2", "date": _d(2), "time": "08:00", "specialty": specialty, "doctor": None},
        {"id": f"slot-{slug}-fallback-3", "date": _d(2), "time": "16:00", "specialty": specialty, "doctor": None},
    ]


def get_slots(specialty: str | None = None, date: str | None = None) -> list[dict]:
    results = SLOTS
    if specialty:
        results = [slot for slot in results if slot["specialty"] == specialty]
        if not results:
            results = _generic_slots(specialty)
    if date:
        results = [slot for slot in results if slot["date"] == date]
    return results

