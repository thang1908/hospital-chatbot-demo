from pydantic import BaseModel, ConfigDict, Field


class PatientIn(BaseModel):
    name: str = Field(min_length=2)
    phone: str = Field(min_length=8)
    birth_year: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class TriageRequest(BaseModel):
    patient: PatientIn
    messages: list[ChatMessage]


class SlotOut(BaseModel):
    id: str
    date: str
    time: str
    specialty: str
    doctor: str | None = None


class SpecialtyMatchOut(BaseModel):
    id: str
    name: str
    description: str
    score: float = 0
    evidence_terms: list[str] = Field(default_factory=list)


class TriageResponse(BaseModel):
    path: str
    reply: str
    confidence: float
    specialty_id: str | None = None
    specialty: str | None = None
    suggested_specialties: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    warning_signs: list[str] = Field(default_factory=list)
    needs_more_info: bool = False
    reasoning_summary: str = ""
    follow_up_questions: list[str] = Field(default_factory=list)
    matched_specialties: list[SpecialtyMatchOut] = Field(default_factory=list)
    analysis_source: str = "rules"
    slots: list[SlotOut] = Field(default_factory=list)
    booking_ready: bool = True


class BookingCreate(BaseModel):
    patient: PatientIn
    symptom_summary: str
    specialty: str
    doctor: str | None = None
    appointment_date: str
    appointment_time: str


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_name: str
    phone: str
    birth_year: int | None
    symptom_summary: str
    specialty: str
    doctor: str | None
    appointment_date: str
    appointment_time: str
    status: str
