from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import SpecialtyInfo

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "chuyenkhoa.json"

STOP_WORDS = {
    "ban",
    "benh",
    "cac",
    "can",
    "co",
    "cua",
    "duoc",
    "gap",
    "hay",
    "hoac",
    "kham",
    "la",
    "lien",
    "mot",
    "muon",
    "nguoi",
    "nhieu",
    "sau",
    "toi",
    "trieu",
    "trong",
    "va",
    "ve",
    "voi",
}

SPECIALTY_HINTS = {
    "da lieu": "ngua mun phong nuoc phat ban noi ban man do me day di ung da ngoai da",
    "ho tro sinh san": "vo sinh mong con iui ivf bao ton sinh san tien hon nhan thai nghe phu khoa hiem muon nam khoa sinh san",
    "di ung mien dich": "di ung man do me day lupus benh he thong phat ban ngua",
    "noi co xuong khop": "dau xuong dau khop sung khop dau lung dau vai dau goi co cung te tay chan",
    "noi chong doc": "con trung can dong vat can ngo doc thuoc ran can kiem tra suc khoe",
    "noi ho hap": "ho khan ho dom kho tho kho khe viem phoi benh phoi hut thuoc la hen",
    "noi huyet hoc": "met moi da xanh xuat huyet bam tim thieu mau chay mau noi not duoi da",
    "noi hoi suc tich cuc": "kiem tra suc khoe dinh ky noi khoa tong quat",
    "noi noi tiet": "sut can run tay chan va mo hoi hoi hop tieu duong tuyen giap noi tiet",
    "noi than kinh": "dau dau chong mat te tay chan run tay mat ngu yeu tay chan tai bien",
    "noi tam than": "mat ngu so hai lo lang tram cam stress khong kiem soat hanh vi",
    "kham noi tong quat": "met moi sot ho cam khong ro tong quat kiem tra suc khoe dau nhuc",
    "noi tieu hoa": "dau bung dau thuong vi day hoi kho tieu tieu chay buon non non oi hoi oi chua roi loan tieu hoa ia mau di ngoai ra mau dai tien ra mau phan co mau",
    "noi tim mach": "dau nguc hoi hop nhip tim nhanh cham mach khong deu huyet ap cao tim mach kho tho khi van dong",
    "noi than tiet nieu": "tieu buot tieu rat tieu nhieu nuoc tieu duc dai mau dau that lung soi than",
    "noi truyen nhiem": "sot truyen nhiem viem gan nhiem trung phat ban sot cao",
    "noi ung buou": "khoi u ung thu hach sut can bat thuong chan doan som",
    "san phu khoa": "rong kinh mat kinh tre kinh mang thai thai dinh ky dau bung duoi khi hu tuyen vu phu khoa",
    "rang ham mat": "dau rang sau rang rang lung lay viem loi ham mat",
    "chuyen khoa mat": "nhin mo choi com ngua chay nuoc mat dau nhuc mat do mat",
    "ngoai chinh hinh cot song": "chan thuong cot song dau cot song dau lung thoat vi dia dem gu veo cot song",
    "ngoai long nguc": "lom long nguc benh long nguc trung that dau nguc ngoai khoa",
    "ngoai than kinh": "u than kinh phinh mach nao chan thuong so nao ngoai than kinh",
    "ngoai tiet nieu": "tien liet tuyen soi than soi nieu quan phau thuat tiet nieu",
    "ngoai tieu hoa gan mat tuy": "u vung bung soi tui mat viem tui mat gan mat tuy ngoai tieu hoa",
    "phuc hoi chuc nang": "phuc hoi chuc nang sau chan thuong liet nua nguoi tap phuc hoi",
    "tao hinh tham my": "di tat bam sinh sut moi ho ham ech seo vet cat vet rach nang mui tham my",
    "y hoc co truyen": "y hoc co truyen dong y phuc hoi dau moi co the tinh than",
    "tai mui hong": "dau hong dau dau ho chong mat ngu ngay hat hoi ngua mui ngat mui chay nuoc mui u tai nghe kem khan tieng",
    "noi dot quy": "dot quy dau dau yeu liet tay chan meo mieng ngon ngu bat thuong chong mat nhin mo te bi",
    "ngoai tong hop": "phau thuat ngoai khoa cot song long nguc chan doan ngoai tong hop",
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in normalize_text(text).split()
        if len(token) > 1 and token not in STOP_WORDS
    }


def _build_search_text(name: str, description: str) -> str:
    normalized_name = normalize_text(name)
    hints = SPECIALTY_HINTS.get(normalized_name, "")
    return normalize_text(f"{name} {description} {hints}")


@lru_cache(maxsize=1)
def load_specialty_seed_data() -> list[dict[str, str]]:
    raw_items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    specialties: list[dict[str, str]] = []
    for item in raw_items:
        specialty_id = str(item["id"]).strip()
        name = str(item["specialtyName"]).strip()
        description = str(item["specialtyDescription"]).strip()
        specialties.append(
            {
                "id": specialty_id,
                "name": name,
                "description": description,
                "search_text": _build_search_text(name, description),
            }
        )
    return specialties


def seed_specialties(db: Session) -> None:
    for item in load_specialty_seed_data():
        specialty = db.get(SpecialtyInfo, item["id"])
        if specialty is None:
            db.add(SpecialtyInfo(**item))
            continue

        specialty.name = item["name"]
        specialty.description = item["description"]
        specialty.search_text = item["search_text"]
    db.commit()


def list_specialties(db: Session | None = None) -> list[dict[str, str]]:
    if db is None:
        return load_specialty_seed_data()

    rows = db.query(SpecialtyInfo).order_by(SpecialtyInfo.name.asc()).all()
    if not rows:
        return load_specialty_seed_data()

    return [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "search_text": row.search_text,
        }
        for row in rows
    ]


def list_specialty_names() -> list[str]:
    return [item["name"] for item in load_specialty_seed_data()]


@lru_cache(maxsize=1)
def specialty_name_by_normalized() -> dict[str, str]:
    return {normalize_text(item["name"]): item["name"] for item in load_specialty_seed_data()}


@lru_cache(maxsize=1)
def specialty_name_by_id() -> dict[str, str]:
    return {item["id"]: item["name"] for item in load_specialty_seed_data()}


@lru_cache(maxsize=1)
def specialty_id_by_name() -> dict[str, str]:
    return {item["name"]: item["id"] for item in load_specialty_seed_data()}


def normalize_specialty_name(name: str | None) -> str | None:
    if not name:
        return None
    return specialty_name_by_normalized().get(normalize_text(name))


def _score_specialty(query: str, query_tokens: set[str], specialty: dict[str, str]) -> tuple[float, list[str]]:
    search_text = specialty["search_text"]
    specialty_tokens = set(search_text.split())
    matched_tokens = sorted(query_tokens & specialty_tokens)

    score = float(len(matched_tokens))
    normalized_query = normalize_text(query)
    normalized_name = normalize_text(specialty["name"])

    if normalized_name and normalized_name in normalized_query:
        score += 8
    if normalized_query and normalized_query in search_text:
        score += 4

    for token in query_tokens:
        if len(token) >= 4 and token in search_text and token not in matched_tokens:
            matched_tokens.append(token)
            score += 0.5

    return score, sorted(set(matched_tokens))


def search_specialties(query: str, db: Session | None = None, limit: int = 6) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 12))
    specialties = list_specialties(db)
    query_tokens = tokenize(query)

    scored: list[dict[str, Any]] = []
    for specialty in specialties:
        score, evidence_terms = _score_specialty(query, query_tokens, specialty)
        scored.append(
            {
                "id": specialty["id"],
                "name": specialty["name"],
                "description": specialty["description"],
                "score": round(score, 2),
                "evidence_terms": evidence_terms[:8],
            }
        )

    scored.sort(key=lambda item: (item["score"], item["name"]), reverse=True)
    matches = [item for item in scored if item["score"] > 0]
    if matches:
        return matches[:limit]

    fallback_names = {"Khám nội tổng quát", "Nội - Truyền Nhiễm", "Nội - Thần Kinh"}
    fallback = [item for item in scored if item["name"] in fallback_names]
    return fallback[:limit] or scored[:limit]


def safe_search_specialties(query: str, db: Session | None = None, limit: int = 6) -> list[dict[str, Any]]:
    try:
        return search_specialties(query=query, db=db, limit=limit)
    except (OSError, json.JSONDecodeError, SQLAlchemyError):
        return search_specialties(query=query, db=None, limit=limit)
