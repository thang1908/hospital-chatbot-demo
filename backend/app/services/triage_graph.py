from __future__ import annotations

import os
import unicodedata
from functools import lru_cache
from textwrap import dedent
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.specialty_knowledge import (
    list_specialty_names,
    normalize_specialty_name,
    specialty_id_by_name,
    specialty_name_by_id,
)
from app.services.tools import _query_slots_from_db, query_available_slots, search_hospital_specialties

try:
    from langchain.agents import create_agent
except ImportError:  # pragma: no cover - keeps the app importable before deps are installed.
    create_agent = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - keeps the app importable before deps are installed.
    ChatOpenAI = None


class TriageState(TypedDict, total=False):
    messages: list[dict[str, str]]
    combined_text: str
    latest_user_text: str
    conversation_text: str
    red_flags: list[str]
    warning_signs: list[str]
    needs_more_info: bool
    specialty_id: str | None
    specialty: str | None
    suggested_specialties: list[str]
    matched_specialties: list[dict]
    confidence: float
    reasoning_summary: str
    follow_up_questions: list[str]
    analysis_source: str
    path: str
    reply: str
    slots: list[dict]
    booking_ready: bool


class SpecialtyEvidence(BaseModel):
    id: str = Field(description="Hospital specialty id from the specialty database.")
    name: str = Field(description="Exact hospital specialty name from the specialty database.")
    description: str = Field(description="Short specialty description from the hospital database.")
    score: float = Field(default=0.0, description="Relevance score returned by the search tool.")
    evidence_terms: list[str] = Field(default_factory=list, description="Matched terms from the search index.")


class TriageAnalysis(BaseModel):
    """Structured appointment-routing analysis for a patient symptom conversation."""

    red_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Clear emergency signs where normal appointment booking should stop now. "
            "Do not include unclear symptoms that still need follow-up questions."
        ),
    )
    warning_signs: list[str] = Field(
        default_factory=list,
        description=(
            "Potentially concerning symptoms that need clarification before routing, "
            "including unclear chest tightness, shortness of breath, dizziness, or blood in stool."
        ),
    )
    needs_more_info: bool = Field(
        default=False,
        description="True when the agent should ask more questions before choosing a bookable specialty.",
    )
    specialty: str | None = Field(
        default=None,
        description="Exact best matching specialty name from the search tool result, or null when not enough information.",
    )
    specialty_id: str | None = Field(
        default=None,
        description="Exact id of the selected specialty from the search tool result.",
    )
    suggested_specialties: list[str] = Field(
        default_factory=list,
        description="One to two likely specialty names from the search tool result.",
    )
    matched_specialties: list[SpecialtyEvidence] = Field(
        default_factory=list,
        description="Specialties considered from the hospital specialty search tool.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence that the selected specialty is appropriate for booking.",
    )
    reasoning_summary: str = Field(
        default="",
        description="A short user-facing explanation, not hidden chain-of-thought.",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Optional focused questions. Use 0 questions when booking can continue; usually ask only 1-2 when clarification is needed.",
    )


VALID_SPECIALTIES = set(list_specialty_names())

TRIAGE_AGENT_SYSTEM_PROMPT = dedent(
    """
    You are an AI routing agent for a hospital appointment booking MVP.
    Your job is appointment routing, not diagnosis, prescriptions, or medical advice.

    Analyze Vietnamese patient messages. They may be written without accents.
    You have access to two tools:
    1. search_hospital_specialties — search the hospital's specialty database.
    2. query_available_slots — query available appointment slots from the database.

    Required workflow:
    - Before choosing any specialty, call search_hospital_specialties with a
      compact symptom query extracted from the conversation.
    - Use only exact specialty names and ids returned by that tool.
    - Include the most relevant tool candidates in matched_specialties.
    - When you have identified the best specialty with confidence (needs_more_info=false),
      ALWAYS call query_available_slots(specialty=<exact_specialty_name>) to fetch
      available slots from the database. Include these in your response so the
      frontend can display them directly in the chat.
    - The latest user message is the most authoritative input. If the latest
      message corrects or retracts earlier symptoms, for example "tôi đùa",
      "thực ra", "không phải", or "chỉ bị", base the analysis on the corrected
      symptoms and do not carry over withdrawn symptoms.
    - Decide whether the information is already enough for routing. Set
      needs_more_info=true when you need clarification before a safe specialty
      suggestion; set specialty=null in that case.
    - After the patient has answered at least one clarifying question, prefer
      choosing the best bookable specialty when the answer is enough to route.
      Do not keep asking follow-up questions unless the missing detail would
      clearly change specialty or urgency.
    - If the tool results are weak or the patient message is vague, lower
      confidence, set needs_more_info=true, and ask only the most useful
      follow-up question(s).
    - follow_up_questions must be written specifically for the latest patient
      message and the uncertainty you found. Ask 0-2 questions, not a fixed
      checklist. If the existing conversation is enough to choose a specialty,
      leave follow_up_questions empty.
      Do not ask about symptoms that the latest user message clearly retracted.

    Safety policy:
    - Set red_flags only for clear emergency signs: severe chest pain, severe
      shortness of breath, fainting, seizures, heavy bleeding, severe abdominal
      pain, stroke-like symptoms, very high fever, or sudden weakness/speech trouble.
    - For abdominal pain, do not set red_flags just because fever is mentioned.
      Use red_flags only when the patient explicitly reports severe/unbearable
      abdominal pain, rigid abdomen, repeated vomiting, fainting, shock-like
      weakness/dizziness, heavy bleeding/blood in stool, or very high fever.
      Otherwise choose the best specialty when enough routing information exists
      and mention when to seek urgent care in reasoning_summary.
    - Do not set red_flags for symptom words alone. If severity is unclear,
      put those symptoms in warning_signs and decide whether 1-2 follow-up
      questions are needed before routing.
    - If you set red_flags, follow_up_questions must be empty because the app
      will stop normal booking.
    - Symptoms such as chest tightness, mild/unclear shortness of breath,
      headache, dizziness, palpitations, or nonspecific discomfort should go in
      warning_signs first unless the user clearly states severity or sudden danger.
    - Isolated blood in stool without heavy bleeding, fainting, severe weakness,
      or shock symptoms should be warning_signs, not red_flags. If unclear,
      ask only the most important 1-2 questions before booking.
    - warning_signs do not automatically block booking. Decide from context
      whether they still require clarification or whether a specialty can be
      recommended now.
    - When red_flags is not empty, do not encourage normal appointment booking.
    - If information is vague or insufficient, set needs_more_info=true, set
      specialty to null when appropriate, and ask concise follow-up questions.
    - If a corrected latest message contains one clear symptom that maps well
      to a specialty and no clear emergency sign, choose exactly one hospital
      specialty with needs_more_info=false.
    - reasoning_summary must be 1-2 short Vietnamese sentences explaining the
      observable basis for the routing decision. Do not reveal hidden chain-of-thought.
    """
).strip()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _combine_messages(messages: list[dict[str, str]]) -> str:
    return " ".join(message["content"] for message in messages if message.get("role") == "user")


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "").strip()
    return ""


def _conversation_transcript(messages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for message in messages[-8:]:
        role = message.get("role", "user")
        content = str(message.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _patient_context(messages: list[dict[str, str]]) -> str:
    user_turns = sum(1 for message in messages if message.get("role") == "user")
    return f"user_turns={user_turns}"


@lru_cache(maxsize=4)
def _build_triage_agent(model_name: str):
    if ChatOpenAI is None or create_agent is None or not os.getenv("OPENAI_API_KEY"):
        return None

    model = ChatOpenAI(
        model=model_name,
        temperature=0,
        timeout=20,
        max_retries=2,
    )
    return create_agent(
        model=model,
        tools=[search_hospital_specialties, query_available_slots],
        system_prompt=TRIAGE_AGENT_SYSTEM_PROMPT,
        response_format=TriageAnalysis,
    )


def _as_dict(analysis: TriageAnalysis | dict) -> dict:
    if isinstance(analysis, BaseModel):
        return analysis.model_dump()
    return dict(analysis)


def _clean_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _clamp_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.25
    return max(0.0, min(1.0, confidence))


def _coerce_score(value: object) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _normalize_specialty(value: object) -> str | None:
    if not value:
        return None
    return normalize_specialty_name(str(value).strip())


def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*first, *second]:
        key = _normalize(item)
        if item and key not in seen:
            merged.append(item)
            seen.add(key)
    return merged


def _clean_matches(values: object) -> list[dict]:
    if not isinstance(values, list):
        return []

    cleaned: list[dict] = []
    for value in values:
        if isinstance(value, BaseModel):
            item = value.model_dump()
        elif isinstance(value, dict):
            item = value
        else:
            continue

        name = _normalize_specialty(item.get("name"))
        specialty_id = str(item.get("id") or "").strip()
        if not name and specialty_id in specialty_name_by_id():
            name = specialty_name_by_id()[specialty_id]
        if not name:
            continue
        if not specialty_id:
            specialty_id = specialty_id_by_name().get(name, "")

        cleaned.append(
            {
                "id": specialty_id,
                "name": name,
                "description": str(item.get("description") or "").strip(),
                "score": _coerce_score(item.get("score")),
                "evidence_terms": _clean_list(item.get("evidence_terms"))[:8],
            }
        )
    return cleaned


def _sanitize_analysis(raw: dict) -> dict:
    red_flags = _clean_list(raw.get("red_flags"))
    warning_signs = _clean_list(raw.get("warning_signs"))
    needs_more_info = bool(raw.get("needs_more_info"))
    specialty_id = str(raw.get("specialty_id") or "").strip() or None
    specialty = specialty_name_by_id().get(specialty_id or "") if specialty_id else None
    specialty = specialty or _normalize_specialty(raw.get("specialty"))
    if specialty and not specialty_id:
        specialty_id = specialty_id_by_name().get(specialty)
    confidence = _clamp_confidence(raw.get("confidence"))

    suggested = []
    for item in _clean_list(raw.get("suggested_specialties")):
        normalized_specialty = normalize_specialty_name(item)
        if normalized_specialty in VALID_SPECIALTIES:
            suggested.append(normalized_specialty)
    if specialty:
        suggested = _merge_unique([specialty], suggested)

    matched_specialties = _clean_matches(raw.get("matched_specialties"))
    follow_up_questions = _clean_list(raw.get("follow_up_questions"))

    if red_flags and (follow_up_questions or needs_more_info):
        warning_signs = _merge_unique(warning_signs, red_flags)
        red_flags = []
        needs_more_info = True

    if red_flags:
        confidence = max(confidence, 0.85)
        needs_more_info = False
    elif follow_up_questions or needs_more_info:
        specialty_id = None
        specialty = None
        needs_more_info = True

    reasoning_summary = str(raw.get("reasoning_summary") or "").strip()

    return {
        "red_flags": red_flags,
        "warning_signs": warning_signs,
        "needs_more_info": needs_more_info,
        "specialty_id": specialty_id,
        "specialty": specialty,
        "suggested_specialties": suggested[:2],
        "matched_specialties": matched_specialties[:5],
        "confidence": confidence,
        "reasoning_summary": reasoning_summary,
        "follow_up_questions": follow_up_questions[:2],
        "analysis_source": raw.get("analysis_source", "agent-tool"),
    }


def _agent_unavailable(reason: str) -> dict:
    return {
        "red_flags": [],
        "warning_signs": [],
        "needs_more_info": True,
        "specialty_id": None,
        "specialty": None,
        "suggested_specialties": [],
        "matched_specialties": [],
        "confidence": 0.0,
        "reasoning_summary": reason,
        "follow_up_questions": [],
        "analysis_source": "agent-unavailable",
    }


def _agent_analyze(state: TriageState) -> dict:
    agent = _build_triage_agent(settings.openai_model)
    if agent is None:
        return _agent_unavailable(
            "AI agent chưa sẵn sàng. Hãy kiểm tra OPENAI_API_KEY, langchain-openai và phiên bản langchain trong backend."
        )

    latest_text = state.get("latest_user_text", "")
    transcript = state.get("conversation_text", "")

    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Patient context: {_patient_context(state.get('messages', []))}\n"
                            f"Latest user message: {latest_text}\n\n"
                            f"Conversation transcript:\n{transcript}\n\n"
                            "Search the hospital specialty database, then return the structured triage analysis."
                        ),
                    }
                ]
            }
        )
    except Exception:
        return _agent_unavailable("AI agent chưa xử lý được yêu cầu hiện tại. Hãy kiểm tra log backend/OpenAI rồi thử lại.")

    structured_response = result.get("structured_response") if isinstance(result, dict) else None
    if structured_response is None:
        return _agent_unavailable("AI agent chưa trả về phân tích có cấu trúc. Hãy thử lại hoặc kiểm tra cấu hình agent.")

    data = _as_dict(structured_response)
    data["analysis_source"] = "agent-tool"
    return _sanitize_analysis(data)


def collect_context(state: TriageState) -> TriageState:
    messages = state["messages"]
    return {
        "combined_text": _combine_messages(messages),
        "latest_user_text": _latest_user_message(messages),
        "conversation_text": _conversation_transcript(messages),
    }


def analyze_symptoms(state: TriageState) -> TriageState:
    return _agent_analyze(state)


def route_case(state: TriageState) -> str:
    if state.get("red_flags"):
        return "red_flag"
    if state.get("needs_more_info") or state.get("follow_up_questions") or not state.get("specialty"):
        return "low_confidence"
    return "happy"


def handle_red_flag(state: TriageState) -> TriageState:
    flags = ", ".join(state.get("red_flags", []))
    reasoning = state.get("reasoning_summary") or "Mô tả có dấu hiệu cần ưu tiên an toàn."
    return {
        "path": "failure",
        "reply": (
            f"{reasoning} "
            f"Tôi phát hiện dấu hiệu cần chú ý: {flags}. "
            "Tôi sẽ không tiếp tục đặt lịch thường. Vui lòng liên hệ cấp cứu hoặc nhân viên bệnh viện để được hỗ trợ ngay."
        ),
        "slots": [],
    }


def handle_low_confidence(state: TriageState) -> TriageState:
    questions = state.get("follow_up_questions") or []
    question_text = ""
    if questions:
        question_text = " Bạn có thể trả lời thêm: " + " ".join(
            f"{index + 1}. {question}" for index, question in enumerate(questions)
        )

    return {
        "path": "low-confidence",
        "reply": (
            f"{state.get('reasoning_summary') or 'Thông tin hiện tại chưa đủ để gợi ý chuyên khoa an toàn.'} "
            f"{question_text}"
        ),
        "slots": [],
    }


def handle_happy_path(state: TriageState) -> TriageState:
    specialty = state.get("specialty") or "Khám nội tổng quát"
    reasoning = state.get("reasoning_summary")
    latest = state.get("latest_user_text", "").lower()

    # Detect user đang hỏi về lịch trống (không phải lần đầu gợi ý chuyên khoa)
    _slot_query_keywords = ["lịch trống", "lich trong", "khung giờ", "khung gio",
                            "ngày nào", "ngay nao", "hôm nào", "hom nao",
                            "còn trống", "con trong", "có lịch", "co lich",
                            "tuần này", "tuan nay", "xem lịch", "xem lich"]
    is_slot_query = any(kw in latest for kw in _slot_query_keywords)

    available_slots = _query_slots_from_db(specialty=specialty)

    if is_slot_query:
        # Trả lời text về lịch trống, không hiện nút đặt lịch
        if available_slots:
            lines = [f"Lịch trống hiện có cho **{specialty}**:"]
            for s in available_slots[:6]:
                doc = f" — {s['doctor']}" if s.get("doctor") else ""
                lines.append(f"• {s['date']} lúc {s['time']}{doc}")
            reply = "\n".join(lines) + "\n\nBạn có muốn đặt một trong các khung giờ trên không?"
        else:
            reply = f"Hiện chưa có lịch trống cho **{specialty}**. Bạn có thể thử lại sau hoặc chọn chuyên khoa khác."
        return {
            "path": "happy",
            "reply": reply,
            "slots": available_slots,
            "booking_ready": False,
        }

    return {
        "path": "happy",
        "reply": (
            f"{reasoning + ' ' if reasoning else ''}"
            f"Dựa trên mô tả hiện tại, tôi gợi ý bạn nên khám **{specialty}**."
        ),
        "slots": available_slots,
        "booking_ready": True,
    }


def build_triage_graph():
    graph = StateGraph(TriageState)
    graph.add_node("collect_context", collect_context)
    graph.add_node("analyze_symptoms", analyze_symptoms)
    graph.add_node("handle_red_flag", handle_red_flag)
    graph.add_node("handle_low_confidence", handle_low_confidence)
    graph.add_node("handle_happy_path", handle_happy_path)

    graph.set_entry_point("collect_context")
    graph.add_edge("collect_context", "analyze_symptoms")
    graph.add_conditional_edges(
        "analyze_symptoms",
        route_case,
        {
            "red_flag": "handle_red_flag",
            "low_confidence": "handle_low_confidence",
            "happy": "handle_happy_path",
        },
    )
    graph.add_edge("handle_red_flag", END)
    graph.add_edge("handle_low_confidence", END)
    graph.add_edge("handle_happy_path", END)
    return graph.compile()


triage_graph = build_triage_graph()
