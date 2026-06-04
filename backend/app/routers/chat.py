from fastapi import APIRouter

from app.schemas import TriageRequest, TriageResponse
from app.services.triage_graph import triage_graph

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> dict:
    messages = [message.model_dump() for message in request.messages]
    result = triage_graph.invoke({"messages": messages})
    return {
        "path": result.get("path", "low-confidence"),
        "reply": result.get("reply", ""),
        "confidence": result.get("confidence", 0),
        "specialty_id": result.get("specialty_id"),
        "specialty": result.get("specialty"),
        "suggested_specialties": result.get("suggested_specialties", []),
        "red_flags": result.get("red_flags", []),
        "warning_signs": result.get("warning_signs", []),
        "needs_more_info": result.get("needs_more_info", False),
        "reasoning_summary": result.get("reasoning_summary", ""),
        "follow_up_questions": result.get("follow_up_questions", []),
        "matched_specialties": result.get("matched_specialties", []),
        "analysis_source": result.get("analysis_source", "rules"),
        "slots": result.get("slots", []),
        "booking_ready": result.get("booking_ready", True),
    }
