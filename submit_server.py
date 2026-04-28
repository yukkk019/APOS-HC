"""
ローカル確認用: POST /save と POST /submit を 8000 番で受け付けます。

起動例:
  pip install -r requirements.txt
  uvicorn submit_server:app --reload --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, Query, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Literal
import sqlite3
from pathlib import Path
from datetime import datetime
import json
import logging
import os
import re
import time
from uuid import uuid4

app = FastAPI()
DB_PATH = Path(__file__).with_name("apos_hc.db")
os.environ.setdefault("APOS_HC_DB_PATH", str(DB_PATH.resolve()))
UPLOADS_DIR = Path(__file__).with_name("uploads")
ALLOWED_UPLOAD_CATEGORIES = {"genogram", "room", "medicine", "pain"}
DESKTOP_DIR = Path(__file__).resolve().parent.parent
FORMS_DIR = DESKTOP_DIR / "analysis" / "backend" / "app" / "templates" / "forms"
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
STATIC_DIR = DESKTOP_DIR / "analysis" / "backend" / "app" / "static"
NEWNEED_STATIC_DIR = DESKTOP_DIR / "analysis" / "backend" / "app" / "newneed" / "static"
_REPO_NEWNEED_STATIC_DIR = Path(__file__).resolve().parent / "newneed" / "static"
DB_CONNECT_TIMEOUT_SEC = 15
DB_BUSY_TIMEOUT_MS = 15000
DB_LOCK_RETRY_ATTEMPTS = 5
DB_LOCK_RETRY_SLEEP_SEC = 0.2

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
for _cat in ALLOWED_UPLOAD_CATEGORIES:
    (UPLOADS_DIR / _cat).mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
_effective_newneed_static = NEWNEED_STATIC_DIR if NEWNEED_STATIC_DIR.is_dir() else _REPO_NEWNEED_STATIC_DIR
if _effective_newneed_static.is_dir():
    app.mount("/api/newneed/static", StaticFiles(directory=str(_effective_newneed_static)), name="newneed_static")

try:
    from newneed.api_router import router as _newneed_api_router

    app.include_router(_newneed_api_router, prefix="/api/newneed", tags=["newneed"])
except Exception as exc:
    logging.getLogger(__name__).warning("newneed API をマウントできませんでした: %s", exc)


class FormData(BaseModel):
    # 画面から送られてくるデータの形
    userId: str
    assessment_round: Literal[1, 2, 3]
    answers: dict


def get_by_path(obj: dict, path: str):
    cur = obj
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def split_date_ymd(value: str):
    if not value or not isinstance(value, str):
        return (None, None, None)
    parts = value.split("-")
    if len(parts) != 3:
        return (None, None, None)
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return (None, None, None)


def to_int_or_none(value):
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=DB_CONNECT_TIMEOUT_SEC)
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
    return conn


def run_db_write_with_retry(write_func):
    for attempt in range(DB_LOCK_RETRY_ATTEMPTS):
        try:
            with get_db_connection() as conn:
                return write_func(conn)
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == DB_LOCK_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(DB_LOCK_RETRY_SLEEP_SEC * (attempt + 1))


def quote_ident(name: str) -> str:
    return "\"" + str(name).replace("\"", "\"\"") + "\""


def normalize_text(value):
    text = str(value or "").strip()
    return text or None


def _strip_brackets(key: str) -> str:
    return key[:-2] if isinstance(key, str) and key.endswith("[]") else str(key)


def _to_snake(name: str) -> str:
    text = _strip_brackets(name).replace("-", "_")
    out = []
    for i, ch in enumerate(text):
        if ch.isupper() and i > 0 and text[i - 1] != "_":
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _to_camel(name: str) -> str:
    snake = _to_snake(name)
    parts = [p for p in snake.split("_") if p != ""]
    if not parts:
        return ""
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


class FlexDict(dict):
    """
    Flat/structured key mismatch absorber.
    - supports snake/camel aliases
    - supports [] suffix aliases
    - supports prefixed flat keys via namespace views
    """

    def __init__(self, data=None, prefixes=None):
        super().__init__()
        self._data = data if isinstance(data, dict) else {}
        self._prefixes = list(prefixes or [])

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def _wrap(self, value, prefixes=None):
        if isinstance(value, dict) and not isinstance(value, FlexDict):
            return FlexDict(value, prefixes=prefixes or self._prefixes)
        return value

    def _direct_candidates(self, key: str):
        bare = _strip_brackets(key)
        snake = _to_snake(bare)
        camel = _to_camel(bare)
        out = [bare]
        if key != bare:
            out.append(key)
        if snake not in out:
            out.append(snake)
        if camel and camel not in out:
            out.append(camel)
        return out, snake

    def get(self, key, default=None):
        if not isinstance(key, str):
            return self._wrap(self._data.get(key, default))

        candidates, leaf_snake = self._direct_candidates(key)

        # 1) direct and alias lookup
        for cand in candidates:
            if cand in self._data:
                val = self._data[cand]
                inferred = _to_snake(cand)
                return self._wrap(val, prefixes=self._prefixes + [inferred])

        # 2) prefix-aware lookup
        for prefix in reversed(self._prefixes):
            pref_key = f"{prefix}_{leaf_snake}"
            if pref_key in self._data:
                return self._wrap(self._data[pref_key], prefixes=self._prefixes)

        # 3) global suffix fallback (handles keys like public_medical_detail1d_reason)
        suffix = f"_{leaf_snake}"
        suffix_hits = [k for k in self._data.keys() if isinstance(k, str) and k.endswith(suffix)]
        if len(suffix_hits) == 1:
            return self._wrap(self._data[suffix_hits[0]], prefixes=self._prefixes)

        # 4) namespace inference for nested object access on flat keys
        namespace_candidates = [leaf_snake] + [f"{prefix}_{leaf_snake}" for prefix in self._prefixes]
        for ns in namespace_candidates:
            if any(isinstance(k, str) and (k.startswith(ns + "_") or (ns and k.startswith(ns) and k != ns)) for k in self._data.keys()):
                return FlexDict(self._data, prefixes=self._prefixes + [ns])

        return default


def _normalize_checkbox_bracket_keys(obj):
    if isinstance(obj, dict):
        normalized = {}
        for key, value in obj.items():
            normalized_value = _normalize_checkbox_bracket_keys(value)
            normalized[key] = normalized_value
            if isinstance(key, str) and key.endswith("[]"):
                bare_key = key[:-2]
                if bare_key and bare_key not in normalized:
                    normalized[bare_key] = normalized_value
        return normalized
    if isinstance(obj, list):
        return [_normalize_checkbox_bracket_keys(v) for v in obj]
    return obj


def onehot_equals(value, expected):
    return 1 if value == expected else 0


def onehot_in(values, expected):
    if not isinstance(values, list):
        return 0
    return 1 if expected in values else 0


def ensure_form_payloads_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS form_payloads (
            user_id TEXT NOT NULL,
            assessment_round INTEGER NOT NULL,
            form_num INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, assessment_round, form_num)
        )
        """
    )


def ensure_form4_columns(conn: sqlite3.Connection):
    columns = [
        ("has_caregiver1", "INTEGER"),
        ("has_caregiver0", "INTEGER"),
        ("care_burden_feeling_0", "INTEGER"),
        ("care_burden_feeling_1", "INTEGER"),
        ("care_burden_feeling_2", "INTEGER"),
        ("care_burden_feeling_3", "INTEGER"),
        ("care_burden_feeling_4", "INTEGER"),
        ("care_burden_health_0", "INTEGER"),
        ("care_burden_health_1", "INTEGER"),
        ("care_burden_health_2", "INTEGER"),
        ("care_burden_health_3", "INTEGER"),
        ("care_burden_health_4", "INTEGER"),
        ("care_burden_life_0", "INTEGER"),
        ("care_burden_life_1", "INTEGER"),
        ("care_burden_life_2", "INTEGER"),
        ("care_burden_life_3", "INTEGER"),
        ("care_burden_life_4", "INTEGER"),
        ("care_burden_work_0", "INTEGER"),
        ("care_burden_work_1", "INTEGER"),
        ("care_burden_work_2", "INTEGER"),
        ("care_burden_work_3", "INTEGER"),
        ("care_burden_work_4", "INTEGER"),
        ("care_burden_impact_0", "INTEGER"),
        ("care_burden_impact_1", "INTEGER"),
        ("care_burden_impact_2", "INTEGER"),
        ("care_burden_impact_3", "INTEGER"),
        ("care_burden_impact_4", "INTEGER"),
        ("care_period_years", "INTEGER"),
        ("care_period_months", "INTEGER"),
        ("care_intention_0", "INTEGER"),
        ("care_intention_1", "INTEGER"),
        ("care_intention_2", "INTEGER"),
        ("care_intention_3", "INTEGER"),
        ("care_intention_4", "INTEGER"),
        ("care_intention_5", "INTEGER"),
        ("abuse_injury_0", "INTEGER"),
        ("abuse_injury_1", "INTEGER"),
        ("abuse_injury_2", "INTEGER"),
        ("abuse_injury_3", "INTEGER"),
        ("abuse_injury_4", "INTEGER"),
        ("neglect_hygiene_0", "INTEGER"),
        ("neglect_hygiene_1", "INTEGER"),
        ("neglect_hygiene_2", "INTEGER"),
        ("neglect_hygiene_3", "INTEGER"),
        ("neglect_hygiene_4", "INTEGER"),
        ("psychological_abuse_0", "INTEGER"),
        ("psychological_abuse_1", "INTEGER"),
        ("psychological_abuse_2", "INTEGER"),
        ("psychological_abuse_3", "INTEGER"),
        ("psychological_abuse_4", "INTEGER"),
        ("neglect_care_0", "INTEGER"),
        ("neglect_care_1", "INTEGER"),
        ("neglect_care_2", "INTEGER"),
        ("neglect_care_3", "INTEGER"),
        ("neglect_care_4", "INTEGER"),
        ("sexual_abuse_0", "INTEGER"),
        ("sexual_abuse_1", "INTEGER"),
        ("sexual_abuse_2", "INTEGER"),
        ("sexual_abuse_3", "INTEGER"),
        ("sexual_abuse_4", "INTEGER"),
        ("financial_abuse_0", "INTEGER"),
        ("financial_abuse_1", "INTEGER"),
        ("financial_abuse_2", "INTEGER"),
        ("financial_abuse_3", "INTEGER"),
        ("financial_abuse_4", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page4_to_form4_columns(page4: dict) -> dict:
    caregiver_presence = (page4.get("caregiverPresence") or page4 or {}) or {}
    care_burden = (page4.get("careBurden") or page4 or {}) or {}
    care_reality = (page4.get("careReality") or page4 or {}) or {}

    has_caregiver = str(caregiver_presence.get("hasCaregiver") or "")
    burden_feeling = str(care_burden.get("feeling") or "")
    burden_health = str(care_burden.get("health") or "")
    burden_life = str(care_burden.get("life") or "")
    burden_work = str(care_burden.get("work") or "")
    burden_impact = str(care_burden.get("impact") or "")
    burden_intention = str(care_burden.get("intention") or "")
    period = (care_burden.get("period") or page4 or {}) or {}

    abuse_injury = str(care_reality.get("abuseInjury") or "")
    neglect_hygiene = str(care_reality.get("neglectHygiene") or "")
    psychological_abuse = str(care_reality.get("psychologicalAbuse") or "")
    neglect_care = str(care_reality.get("neglectCare") or "")
    sexual_abuse = str(care_reality.get("sexualAbuse") or "")
    financial_abuse = str(care_reality.get("financialAbuse") or "")

    return {
        "has_caregiver1": onehot_equals(has_caregiver, "1"),
        "has_caregiver0": onehot_equals(has_caregiver, "0"),
        "care_burden_feeling_0": onehot_equals(burden_feeling, "0"),
        "care_burden_feeling_1": onehot_equals(burden_feeling, "1"),
        "care_burden_feeling_2": onehot_equals(burden_feeling, "2"),
        "care_burden_feeling_3": onehot_equals(burden_feeling, "3"),
        "care_burden_feeling_4": onehot_equals(burden_feeling, "4"),
        "care_burden_health_0": onehot_equals(burden_health, "0"),
        "care_burden_health_1": onehot_equals(burden_health, "1"),
        "care_burden_health_2": onehot_equals(burden_health, "2"),
        "care_burden_health_3": onehot_equals(burden_health, "3"),
        "care_burden_health_4": onehot_equals(burden_health, "4"),
        "care_burden_life_0": onehot_equals(burden_life, "0"),
        "care_burden_life_1": onehot_equals(burden_life, "1"),
        "care_burden_life_2": onehot_equals(burden_life, "2"),
        "care_burden_life_3": onehot_equals(burden_life, "3"),
        "care_burden_life_4": onehot_equals(burden_life, "4"),
        "care_burden_work_0": onehot_equals(burden_work, "0"),
        "care_burden_work_1": onehot_equals(burden_work, "1"),
        "care_burden_work_2": onehot_equals(burden_work, "2"),
        "care_burden_work_3": onehot_equals(burden_work, "3"),
        "care_burden_work_4": onehot_equals(burden_work, "4"),
        "care_burden_impact_0": onehot_equals(burden_impact, "0"),
        "care_burden_impact_1": onehot_equals(burden_impact, "1"),
        "care_burden_impact_2": onehot_equals(burden_impact, "2"),
        "care_burden_impact_3": onehot_equals(burden_impact, "3"),
        "care_burden_impact_4": onehot_equals(burden_impact, "4"),
        "care_period_years": to_int_or_none(period.get("years")),
        "care_period_months": to_int_or_none(period.get("months")),
        "care_intention_0": onehot_equals(burden_intention, "0"),
        "care_intention_1": onehot_equals(burden_intention, "1"),
        "care_intention_2": onehot_equals(burden_intention, "2"),
        "care_intention_3": onehot_equals(burden_intention, "3"),
        "care_intention_4": onehot_equals(burden_intention, "4"),
        "care_intention_5": onehot_equals(burden_intention, "5"),
        "abuse_injury_0": onehot_equals(abuse_injury, "0"),
        "abuse_injury_1": onehot_equals(abuse_injury, "1"),
        "abuse_injury_2": onehot_equals(abuse_injury, "2"),
        "abuse_injury_3": onehot_equals(abuse_injury, "3"),
        "abuse_injury_4": onehot_equals(abuse_injury, "4"),
        "neglect_hygiene_0": onehot_equals(neglect_hygiene, "0"),
        "neglect_hygiene_1": onehot_equals(neglect_hygiene, "1"),
        "neglect_hygiene_2": onehot_equals(neglect_hygiene, "2"),
        "neglect_hygiene_3": onehot_equals(neglect_hygiene, "3"),
        "neglect_hygiene_4": onehot_equals(neglect_hygiene, "4"),
        "psychological_abuse_0": onehot_equals(psychological_abuse, "0"),
        "psychological_abuse_1": onehot_equals(psychological_abuse, "1"),
        "psychological_abuse_2": onehot_equals(psychological_abuse, "2"),
        "psychological_abuse_3": onehot_equals(psychological_abuse, "3"),
        "psychological_abuse_4": onehot_equals(psychological_abuse, "4"),
        "neglect_care_0": onehot_equals(neglect_care, "0"),
        "neglect_care_1": onehot_equals(neglect_care, "1"),
        "neglect_care_2": onehot_equals(neglect_care, "2"),
        "neglect_care_3": onehot_equals(neglect_care, "3"),
        "neglect_care_4": onehot_equals(neglect_care, "4"),
        "sexual_abuse_0": onehot_equals(sexual_abuse, "0"),
        "sexual_abuse_1": onehot_equals(sexual_abuse, "1"),
        "sexual_abuse_2": onehot_equals(sexual_abuse, "2"),
        "sexual_abuse_3": onehot_equals(sexual_abuse, "3"),
        "sexual_abuse_4": onehot_equals(sexual_abuse, "4"),
        "financial_abuse_0": onehot_equals(financial_abuse, "0"),
        "financial_abuse_1": onehot_equals(financial_abuse, "1"),
        "financial_abuse_2": onehot_equals(financial_abuse, "2"),
        "financial_abuse_3": onehot_equals(financial_abuse, "3"),
        "financial_abuse_4": onehot_equals(financial_abuse, "4"),
    }



def ensure_form5_columns(conn: sqlite3.Connection):
    columns = [
        ("social_participation_1_a", "INTEGER"),
        ("social_participation_1_b", "INTEGER"),
        ("social_participation_1_c", "INTEGER"),
        ("social_participation_1_d", "INTEGER"),
        ("enjoyment_1_あり", "INTEGER"),
        ("enjoyment_1_なし", "INTEGER"),
        ("enjoyment_1_text_none", "TEXT"),
        ("enjoyment_2_あり", "INTEGER"),
        ("enjoyment_2_なし", "INTEGER"),
        ("enjoyment_2_text_none", "TEXT"),
        ("enjoyment_3_あり", "INTEGER"),
        ("enjoyment_3_なし", "INTEGER"),
        ("enjoyment_3_text_none", "TEXT"),
        ("enjoyment_reason", "TEXT"),
        ("relationship_status_0", "INTEGER"),
        ("relationship_status_1", "INTEGER"),
        ("relationship_status_2", "INTEGER"),
        ("relationship_status_3", "INTEGER"),
        ("consultation_status_0", "INTEGER"),
        ("consultation_status_1", "INTEGER"),
        ("supporter_family", "INTEGER"),
        ("supporter_friend", "INTEGER"),
        ("supporter_minsei", "INTEGER"),
        ("supporter_center", "INTEGER"),
        ("supporter_service_staff", "INTEGER"),
        ("supporter_neighbor", "INTEGER"),
        ("supporter_volunteer", "INTEGER"),
        ("supporter_guardian", "INTEGER"),
        ("supporter_delivery", "INTEGER"),
        ("supporter_public", "INTEGER"),
        ("supporter_religious", "INTEGER"),
        ("supporter_other_flag", "INTEGER"),
        ("supporter_other", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page5_to_form5_columns(page5: dict) -> dict:
    social = (page5.get("socialParticipation") or page5 or {}) or {}
    enjoyment = (social.get("enjoyment") or page5 or {}) or {}
    rc = (page5.get("relationshipConsultation") or page5 or {}) or {}
    supporters = (rc.get("supporters") or page5 or {}) or {}

    motivation = str(social.get("motivation") or page5.get("social_participation_1") or "")
    community = str(enjoyment.get("community") or page5.get("enjoyment_1") or "")
    individual = str(enjoyment.get("individual") or page5.get("enjoyment_2") or "")
    family = str(enjoyment.get("family") or page5.get("enjoyment_3") or "")

    relationship_status = str(rc.get("relationshipStatus") or page5.get("relationship_status") or "")
    consultation_status = str(rc.get("consultationStatus") or page5.get("consultation_status") or "")

    supporter_list = supporters.get("supporterList")
    if not isinstance(supporter_list, list):
        supporter_list = page5.get("supporter")
    if not isinstance(supporter_list, list):
        supporter_list = [] if supporter_list in (None, "", []) else [supporter_list]

    return {
        "social_participation_1_a": onehot_equals(
            motivation,
            "週に3回以上は外出し家族や友人・支援・ネットワークなどと継続に連絡が取れている（デイケア・デイサービス、買物、近隣や親戚や知人等の付き合い、通勤、散歩、行楽、電話、ネット、手紙を含む）",
        ),
        "social_participation_1_b": onehot_equals(motivation, "週に1〜2回は外出したり、家族や知人と連絡を取り社会参加している"),
        "social_participation_1_c": onehot_equals(motivation, "月に数回外出するがそれ以外の時は1人でいる、家族や知人に会うのは月に何回かである。月に1〜2回"),
        "social_participation_1_d": onehot_equals(motivation, "親戚や近隣・社会交流・社会的接触を全くしていない、デイケア等にも行っていない、昨年より外出が減った"),
        "enjoyment_1_あり": onehot_equals(community, "あり"),
        "enjoyment_1_なし": onehot_equals(community, "なし"),
        "enjoyment_1_text_none": normalize_text(enjoyment.get("communityNote") or page5.get("enjoyment_1_text_none")),
        "enjoyment_2_あり": onehot_equals(individual, "あり"),
        "enjoyment_2_なし": onehot_equals(individual, "なし"),
        "enjoyment_2_text_none": normalize_text(enjoyment.get("individualNote") or page5.get("enjoyment_2_text_none")),
        "enjoyment_3_あり": onehot_equals(family, "あり"),
        "enjoyment_3_なし": onehot_equals(family, "なし"),
        "enjoyment_3_text_none": normalize_text(enjoyment.get("familyNote") or page5.get("enjoyment_3_text_none")),
        "enjoyment_reason": normalize_text(social.get("reason") or page5.get("enjoyment_reason")),
        "relationship_status_0": onehot_equals(relationship_status, "1"),
        "relationship_status_1": onehot_equals(relationship_status, "2"),
        "relationship_status_2": onehot_equals(relationship_status, "3"),
        "relationship_status_3": onehot_equals(relationship_status, "4"),
        "consultation_status_0": onehot_equals(consultation_status, "1"),
        "consultation_status_1": onehot_equals(consultation_status, "2"),
        "supporter_family": onehot_in(supporter_list, "家族（身内・親族）"),
        "supporter_friend": onehot_in(supporter_list, "友人の支援者"),
        "supporter_minsei": onehot_in(supporter_list, "民生委員"),
        "supporter_center": onehot_in(supporter_list, "地域包括支援センターや地域活動支援センター"),
        "supporter_service_staff": onehot_in(supporter_list, "介護保険サービスの担当者"),
        "supporter_neighbor": onehot_in(supporter_list, "住民の役員・近隣者"),
        "supporter_volunteer": onehot_in(supporter_list, "ボランティア"),
        "supporter_guardian": onehot_in(supporter_list, "成年後見人"),
        "supporter_delivery": onehot_in(supporter_list, "宅配業者"),
        "supporter_public": onehot_in(supporter_list, "郵便局・消防署・農協"),
        "supporter_religious": onehot_in(supporter_list, "信仰関係者"),
        "supporter_other_flag": onehot_in(supporter_list, "その他"),
        "supporter_other": normalize_text(supporters.get("supporterOther") or page5.get("supporter_other")),
    }



def ensure_form6_columns(conn: sqlite3.Connection):
    columns = [
        ("alcohol_problem_0", "INTEGER"),
        ("alcohol_problem_1", "INTEGER"),
        ("alcohol_problem_2", "INTEGER"),
        ("alcohol_problem_3", "INTEGER"),
        ("who_alcohol_criteria_1", "INTEGER"),
        ("who_alcohol_criteria_2", "INTEGER"),
        ("who_alcohol_criteria_3", "INTEGER"),
        ("who_alcohol_criteria_4", "INTEGER"),
        ("who_alcohol_criteria_5", "INTEGER"),
        ("who_alcohol_criteria_6", "INTEGER"),
        ("who_alcohol_criteria_7", "INTEGER"),
        ("who_alcohol_criteria_8", "INTEGER"),
        ("who_alcohol_result_0", "INTEGER"),
        ("who_alcohol_result_1", "INTEGER"),
        ("who_alcohol_result_2", "INTEGER"),
        ("smoking_habit_0", "INTEGER"),
        ("smoking_habit_1", "INTEGER"),
        ("smoking_amount", "INTEGER"),
        ("smoking_years", "INTEGER"),
        ("brinkman_index", "INTEGER"),
        ("family_impact", "TEXT"),
        ("sleep_quality_0", "INTEGER"),
        ("sleep_quality_1", "INTEGER"),
        ("sleep_quality_2", "INTEGER"),
        ("sleep_quality_3", "INTEGER"),
        ("fatigue_0", "INTEGER"),
        ("fatigue_1", "INTEGER"),
        ("fatigue_detail_だるい", "INTEGER"),
        ("fatigue_detail_疲れやすい", "INTEGER"),
        ("fatigue_detail_疲れが残ってる", "INTEGER"),
        ("fatigue_detail_慢性的に疲れている", "INTEGER"),
        ("allergy_0", "INTEGER"),
        ("allergy_1", "INTEGER"),
        ("allergy_detail_食物", "INTEGER"),
        ("allergy_detail_薬", "INTEGER"),
        ("allergy_detail_植物花粉", "INTEGER"),
        ("allergy_detail_金属", "INTEGER"),
        ("allergy_detail_ハウスダスト", "INTEGER"),
        ("allergy_detail_衣類", "INTEGER"),
        ("allergy_detail_その他", "INTEGER"),
        ("allergy_other", "TEXT"),
        ("physical_activity_0", "INTEGER"),
        ("physical_activity_1", "INTEGER"),
        ("physical_activity_detail", "TEXT"),
        ("disease_within_year_0", "INTEGER"),
        ("disease_within_year_1", "INTEGER"),
        ("disease_type_a", "INTEGER"),
        ("disease_type_b", "INTEGER"),
        ("disease_type_c", "INTEGER"),
        ("disease_type_d", "INTEGER"),
        ("disease_type_e", "INTEGER"),
        ("disease_type_f", "INTEGER"),
        ("disease_type_g", "INTEGER"),
        ("disease_type_h", "INTEGER"),
        ("disease_type_i", "INTEGER"),
        ("disease_type_j", "INTEGER"),
        ("disease_type_other", "TEXT"),
        ("vaccination_status_0", "INTEGER"),
        ("vaccination_status_1", "INTEGER"),
        ("vaccination_a", "INTEGER"),
        ("vaccination_b", "INTEGER"),
        ("vaccination_c", "INTEGER"),
        ("vaccination_d", "INTEGER"),
        ("vaccination_e", "INTEGER"),
        ("vaccination_f", "INTEGER"),
        ("vaccination_h", "INTEGER"),
        ("vaccination_other", "TEXT"),
        ("vaccination_none_reason", "TEXT"),
        ("infection_control_0", "INTEGER"),
        ("infection_control_1", "INTEGER"),
        ("infection_control_2", "INTEGER"),
        ("infection_control_3", "INTEGER"),
        ("infection_control_4", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page6_to_form6_columns(page6: dict) -> dict:
    lh = (page6.get("lifestyleHealth") or page6 or {}) or {}
    ap = str(lh.get("alcoholProblem") or page6.get("alcohol_problem") or "")

    who_criteria = lh.get("whoAlcoholCriteria")
    if not isinstance(who_criteria, list):
        who_criteria = page6.get("who_alcohol_criteria")
    if not isinstance(who_criteria, list):
        who_criteria = [] if who_criteria in (None, "", []) else [who_criteria]
    who_result = str(lh.get("whoAlcoholResult") or page6.get("who_alcohol_result") or "")

    smoking = (lh.get("smoking") or page6 or {}) or {}
    smoking_habit = str(smoking.get("habit") or page6.get("smoking_habit") or "")
    brinkman = (smoking.get("brinkman") or page6 or {}) or {}

    sleep_quality = str(lh.get("sleepQuality") or page6.get("sleep_quality") or "")

    fatigue = (lh.get("fatigue") or page6 or {}) or {}
    fatigue_exists = str(fatigue.get("exists") or page6.get("fatigue") or "")
    fatigue_detail = str(fatigue.get("detail") or page6.get("fatigue_detail") or "")

    allergy = (lh.get("allergy") or page6 or {}) or {}
    allergy_exists = str(allergy.get("exists") or page6.get("allergy") or "")
    allergy_details = allergy.get("details")
    if not isinstance(allergy_details, list):
        allergy_details = page6.get("allergy_detail")
    if not isinstance(allergy_details, list):
        allergy_details = [] if allergy_details in (None, "", []) else [allergy_details]

    physical = (lh.get("physicalActivity") or page6 or {}) or {}
    physical_status = str(physical.get("status") or page6.get("physical_activity") or "")

    ip = (page6.get("infectionPrevention") or page6 or {}) or {}
    dwy = (ip.get("diseaseWithinYear") or page6 or {}) or {}
    dwy_exists = str(dwy.get("exists") or page6.get("disease_within_year") or "")
    dwy_detail = (dwy.get("detail") or page6 or {}) or {}
    disease_types = dwy_detail.get("types")
    if not isinstance(disease_types, list):
        disease_types = page6.get("disease_type")
    if not isinstance(disease_types, list):
        disease_types = [] if disease_types in (None, "", []) else [disease_types]

    vac = (ip.get("vaccination") or page6 or {}) or {}
    vac_status = str(vac.get("status") or page6.get("vaccination_status") or "")
    vac_received = (vac.get("received") or page6 or {}) or {}
    vaccines = vac_received.get("vaccines")
    if not isinstance(vaccines, list):
        vaccines = page6.get("vaccination")
    if not isinstance(vaccines, list):
        vaccines = [] if vaccines in (None, "", []) else [vaccines]

    infection_control = str(ip.get("infectionControl") or page6.get("infection_control") or "")

    return {
        "alcohol_problem_0": onehot_equals(ap, "0"),
        "alcohol_problem_1": onehot_equals(ap, "1"),
        "alcohol_problem_2": onehot_equals(ap, "2"),
        "alcohol_problem_3": onehot_equals(ap, "3"),
        "who_alcohol_criteria_1": onehot_in(who_criteria, "1"),
        "who_alcohol_criteria_2": onehot_in(who_criteria, "2"),
        "who_alcohol_criteria_3": onehot_in(who_criteria, "3"),
        "who_alcohol_criteria_4": onehot_in(who_criteria, "4"),
        "who_alcohol_criteria_5": onehot_in(who_criteria, "5"),
        "who_alcohol_criteria_6": onehot_in(who_criteria, "6"),
        "who_alcohol_criteria_7": 0,
        "who_alcohol_criteria_8": 0,
        "who_alcohol_result_0": onehot_equals(who_result, "0"),
        "who_alcohol_result_1": onehot_equals(who_result, "1"),
        "who_alcohol_result_2": onehot_equals(who_result, "2"),
        "smoking_habit_0": onehot_equals(smoking_habit, "0"),
        "smoking_habit_1": onehot_equals(smoking_habit, "1"),
        "smoking_amount": to_int_or_none(brinkman.get("amount")) if to_int_or_none(brinkman.get("amount")) is not None else to_int_or_none(page6.get("smoking_amount")),
        "smoking_years": to_int_or_none(brinkman.get("years")) if to_int_or_none(brinkman.get("years")) is not None else to_int_or_none(page6.get("smoking_years")),
        "brinkman_index": to_int_or_none(brinkman.get("index")) if to_int_or_none(brinkman.get("index")) is not None else to_int_or_none(page6.get("brinkman_index")),
        "family_impact": normalize_text(smoking.get("familyImpact") or page6.get("family_impact")),
        "sleep_quality_0": onehot_equals(sleep_quality, "0"),
        "sleep_quality_1": onehot_equals(sleep_quality, "1"),
        "sleep_quality_2": onehot_equals(sleep_quality, "2"),
        "sleep_quality_3": onehot_equals(sleep_quality, "3"),
        "fatigue_0": onehot_equals(fatigue_exists, "0"),
        "fatigue_1": onehot_equals(fatigue_exists, "1"),
        "fatigue_detail_だるい": onehot_equals(fatigue_detail, "だるい"),
        "fatigue_detail_疲れやすい": onehot_equals(fatigue_detail, "疲れやすい"),
        "fatigue_detail_疲れが残ってる": onehot_equals(fatigue_detail, "疲れが残ってる"),
        "fatigue_detail_慢性的に疲れている": onehot_equals(fatigue_detail, "慢性的に疲れている"),
        "allergy_0": onehot_equals(allergy_exists, "0"),
        "allergy_1": onehot_equals(allergy_exists, "1"),
        "allergy_detail_食物": onehot_in(allergy_details, "食物"),
        "allergy_detail_薬": onehot_in(allergy_details, "薬"),
        "allergy_detail_植物花粉": onehot_in(allergy_details, "植物花粉"),
        "allergy_detail_金属": onehot_in(allergy_details, "金属"),
        "allergy_detail_ハウスダスト": onehot_in(allergy_details, "ハウスダスト"),
        "allergy_detail_衣類": onehot_in(allergy_details, "衣類"),
        "allergy_detail_その他": onehot_in(allergy_details, "その他"),
        "allergy_other": normalize_text(allergy.get("otherText") or page6.get("allergy_other")),
        "physical_activity_0": onehot_equals(physical_status, "0"),
        "physical_activity_1": onehot_equals(physical_status, "1"),
        "physical_activity_detail": normalize_text(physical.get("detail") or page6.get("physical_activity_detail")),
        "disease_within_year_0": onehot_equals(dwy_exists, "0"),
        "disease_within_year_1": onehot_equals(dwy_exists, "1"),
        "disease_type_a": onehot_in(disease_types, "a.肺炎"),
        "disease_type_b": onehot_in(disease_types, "b.鼻咽炎"),
        "disease_type_c": onehot_in(disease_types, "c.インフルエンザ"),
        "disease_type_d": onehot_in(disease_types, "d.新型コロナ"),
        "disease_type_e": onehot_in(disease_types, "e.エイズ"),
        "disease_type_f": onehot_in(disease_types, "f.ウイルス性肝炎"),
        "disease_type_g": onehot_in(disease_types, "g.動物（ヒトやペンダー）に咬まれた"),
        "disease_type_h": onehot_in(disease_types, "h.虫刺咬"),
        "disease_type_i": onehot_in(disease_types, "i.蜂毒"),
        "disease_type_j": onehot_in(disease_types, "j.その他"),
        "disease_type_other": normalize_text(dwy_detail.get("otherText") or page6.get("disease_type_other")),
        "vaccination_status_0": onehot_equals(vac_status, "0"),
        "vaccination_status_1": onehot_equals(vac_status, "1"),
        "vaccination_a": onehot_in(vaccines, "a.肺炎球菌"),
        "vaccination_b": onehot_in(vaccines, "b.インフルエンザ"),
        "vaccination_c": onehot_in(vaccines, "c.新型コロナ"),
        "vaccination_d": onehot_in(vaccines, "d.三種混合"),
        "vaccination_e": onehot_in(vaccines, "e.帯状疱疹ワクチン"),
        "vaccination_f": onehot_in(vaccines, "f.B型肝炎ワクチン"),
        "vaccination_h": onehot_in(vaccines, "h.その他"),
        "vaccination_other": normalize_text(vac_received.get("otherText") or page6.get("vaccination_other")),
        "vaccination_none_reason": normalize_text(vac.get("noneReason") or page6.get("vaccination_none_reason")),
        "infection_control_0": onehot_equals(infection_control, "0"),
        "infection_control_1": onehot_equals(infection_control, "1"),
        "infection_control_2": onehot_equals(infection_control, "2"),
        "infection_control_3": onehot_equals(infection_control, "3"),
        "infection_control_4": onehot_equals(infection_control, "4"),
    }



def ensure_form7_columns(conn: sqlite3.Connection):
    columns = [
        ("bmi_category_0", "INTEGER"),
        ("bmi_category_1", "INTEGER"),
        ("bmi_category_2", "INTEGER"),
        ("bmi_category_3", "INTEGER"),
        ("bmi_category_4", "INTEGER"),
        ("bmi_category_5", "INTEGER"),
        ("bmi_category_6", "INTEGER"),
        ("bmi_category_7", "INTEGER"),
        ("bmi_category_8", "INTEGER"),
        ("height", "REAL"),
        ("weight", "REAL"),
        ("bmi_value", "REAL"),
        ("weight_change_0", "INTEGER"),
        ("weight_change_1", "INTEGER"),
        ("weight_change_2", "INTEGER"),
        ("weight_change_3", "INTEGER"),
        ("nutrition_self_management_0", "INTEGER"),
        ("nutrition_self_management_1", "INTEGER"),
        ("nutrition_self_management_2", "INTEGER"),
        ("nutrition_self_management_3", "INTEGER"),
        ("nutrition_self_management_4", "INTEGER"),
        ("dietary_therapy_0", "INTEGER"),
        ("dietary_therapy_1", "INTEGER"),
        ("dietary_therapy_detail", "TEXT"),
        ("food_form_0", "INTEGER"),
        ("food_form_1", "INTEGER"),
        ("food_form_2", "INTEGER"),
        ("food_form_3", "INTEGER"),
        ("food_form_4", "INTEGER"),
        ("food_form_5", "INTEGER"),
        ("food_form_6", "INTEGER"),
        ("meal_frequency_0", "INTEGER"),
        ("meal_frequency_1", "INTEGER"),
        ("meal_frequency_2", "INTEGER"),
        ("meal_frequency_3", "INTEGER"),
        ("meal_with_others_0", "INTEGER"),
        ("meal_with_others_1", "INTEGER"),
        ("meal_with_others_2", "INTEGER"),
        ("water_intake_0", "INTEGER"),
        ("water_intake_1", "INTEGER"),
        ("water_intake_2", "INTEGER"),
        ("water_intake_3", "INTEGER"),
        ("swallowing_0", "INTEGER"),
        ("swallowing_1", "INTEGER"),
        ("swallowing_2", "INTEGER"),
        ("swallowing_3", "INTEGER"),
        ("swallowing_4", "INTEGER"),
        ("oral_teeth_gum_0", "INTEGER"),
        ("oral_teeth_gum_1", "INTEGER"),
        ("oral_teeth_gum_2", "INTEGER"),
        ("oral_denture_condition_0", "INTEGER"),
        ("oral_denture_condition_1", "INTEGER"),
        ("oral_denture_condition_2", "INTEGER"),
        ("oral_saliva_flow_0", "INTEGER"),
        ("oral_saliva_flow_1", "INTEGER"),
        ("oral_saliva_flow_2", "INTEGER"),
        ("oral_dryness_0", "INTEGER"),
        ("oral_dryness_1", "INTEGER"),
        ("oral_dryness_2", "INTEGER"),
        ("oral_saliva_0", "INTEGER"),
        ("oral_saliva_1", "INTEGER"),
        ("oral_saliva_2", "INTEGER"),
        ("oral_tongue_0", "INTEGER"),
        ("oral_tongue_1", "INTEGER"),
        ("oral_tongue_2", "INTEGER"),
        ("oral_tongue_surface_0", "INTEGER"),
        ("oral_tongue_surface_1", "INTEGER"),
        ("oral_tongue_surface_2", "INTEGER"),
        ("oral_mucosa_0", "INTEGER"),
        ("oral_mucosa_1", "INTEGER"),
        ("oral_gum_0", "INTEGER"),
        ("oral_gum_1", "INTEGER"),
        ("oral_gum_2", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def to_float_or_none(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _oral_score(oral_rows, item_name):
    if not isinstance(oral_rows, list):
        return ""
    for row in oral_rows:
        if isinstance(row, dict) and str(row.get("item") or "").strip() == item_name:
            return str(row.get("score") or "")
    return ""


def map_page7_to_form7_columns(page7: dict) -> dict:
    lh = (page7.get("lifestyleHealth") or page7 or {}) or {}

    bmi = (lh.get("bmi") or page7 or {}) or {}
    bmi_cat = str(bmi.get("category") or page7.get("bmi_category") or "")
    weight_change = str(bmi.get("weightChange") or page7.get("weight_change") or "")

    nutrition = str(lh.get("nutritionSelfManagement") or page7.get("nutrition_self_management") or "")
    dietary = (lh.get("dietaryTherapy") or page7 or {}) or {}
    dietary_status = str(dietary.get("status") or page7.get("dietary_therapy") or "")

    food_form = str(lh.get("foodForm") or page7.get("food_form") or "")
    meal_freq = str(lh.get("mealFrequency") or page7.get("meal_frequency") or "")
    meal_with_others = str(lh.get("mealWithOthers") or page7.get("meal_with_others") or "")
    water_intake = str(lh.get("waterIntake") or page7.get("water_intake") or "")
    swallowing = str(lh.get("swallowing") or page7.get("swallowing") or "")

    oral_rows = lh.get("oralAssessment")

    open_score = _oral_score(oral_rows, "開口") or str(page7.get("oral_teeth_gum") or "")
    breath_score = _oral_score(oral_rows, "口臭") or str(page7.get("oral_saliva_flow") or "")
    drool_score = _oral_score(oral_rows, "よだれ") or str(page7.get("oral_dryness") or "")
    drysaliva_score = _oral_score(oral_rows, "口腔乾燥度・唾液") or str(page7.get("oral_saliva") or "")
    denture_score = _oral_score(oral_rows, "歯・義歯") or str(page7.get("oral_denture_condition") or "")
    tongue_score = _oral_score(oral_rows, "粘膜全体") or str(page7.get("oral_tongue") or "")
    tongue_surface_score = _oral_score(oral_rows, "舌") or str(page7.get("oral_tongue_surface") or "")
    mucosa_score = _oral_score(oral_rows, "口腔") or str(page7.get("oral_mucosa") or "")
    gum_score = _oral_score(oral_rows, "歯肉") or str(page7.get("oral_gum") or "")

    return {
        "bmi_category_0": onehot_equals(bmi_cat, "0"),
        "bmi_category_1": onehot_equals(bmi_cat, "1"),
        "bmi_category_2": onehot_equals(bmi_cat, "2"),
        "bmi_category_3": onehot_equals(bmi_cat, "3"),
        "bmi_category_4": onehot_equals(bmi_cat, "4"),
        "bmi_category_5": onehot_equals(bmi_cat, "5"),
        "bmi_category_6": onehot_equals(bmi_cat, "6"),
        "bmi_category_7": onehot_equals(bmi_cat, "7"),
        "bmi_category_8": onehot_equals(bmi_cat, "8"),
        "height": to_float_or_none(bmi.get("height")) if to_float_or_none(bmi.get("height")) is not None else to_float_or_none(page7.get("height")),
        "weight": to_float_or_none(bmi.get("weight")) if to_float_or_none(bmi.get("weight")) is not None else to_float_or_none(page7.get("weight")),
        "bmi_value": to_float_or_none(bmi.get("bmiValue")) if to_float_or_none(bmi.get("bmiValue")) is not None else to_float_or_none(page7.get("bmi_value")),
        "weight_change_0": onehot_equals(weight_change, "0"),
        "weight_change_1": onehot_equals(weight_change, "1"),
        "weight_change_2": onehot_equals(weight_change, "2"),
        "weight_change_3": onehot_equals(weight_change, "3"),
        "nutrition_self_management_0": onehot_equals(nutrition, "0"),
        "nutrition_self_management_1": onehot_equals(nutrition, "1"),
        "nutrition_self_management_2": onehot_equals(nutrition, "2"),
        "nutrition_self_management_3": onehot_equals(nutrition, "3"),
        "nutrition_self_management_4": onehot_equals(nutrition, "4"),
        "dietary_therapy_0": onehot_equals(dietary_status, "0"),
        "dietary_therapy_1": onehot_equals(dietary_status, "1"),
        "dietary_therapy_detail": normalize_text(dietary.get("detail") or page7.get("dietary_therapy_detail")),
        "food_form_0": onehot_equals(food_form, "0"),
        "food_form_1": onehot_equals(food_form, "1"),
        "food_form_2": onehot_equals(food_form, "2"),
        "food_form_3": onehot_equals(food_form, "3"),
        "food_form_4": onehot_equals(food_form, "4"),
        "food_form_5": onehot_equals(food_form, "5"),
        "food_form_6": onehot_equals(food_form, "6"),
        "meal_frequency_0": onehot_equals(meal_freq, "0"),
        "meal_frequency_1": onehot_equals(meal_freq, "1"),
        "meal_frequency_2": onehot_equals(meal_freq, "2"),
        "meal_frequency_3": onehot_equals(meal_freq, "3"),
        "meal_with_others_0": onehot_equals(meal_with_others, "0"),
        "meal_with_others_1": onehot_equals(meal_with_others, "1"),
        "meal_with_others_2": onehot_equals(meal_with_others, "2"),
        "water_intake_0": onehot_equals(water_intake, "0"),
        "water_intake_1": onehot_equals(water_intake, "1"),
        "water_intake_2": onehot_equals(water_intake, "2"),
        "water_intake_3": onehot_equals(water_intake, "3"),
        "swallowing_0": 1 if swallowing in ("swallowing_0", "0") else 0,
        "swallowing_1": 1 if swallowing in ("swallowing_1", "1") else 0,
        "swallowing_2": 1 if swallowing in ("swallowing_2", "2") else 0,
        "swallowing_3": 1 if swallowing in ("swallowing_3", "3") else 0,
        "swallowing_4": 1 if swallowing in ("swallowing_4", "4") else 0,
        "oral_teeth_gum_0": onehot_equals(open_score, "0"),
        "oral_teeth_gum_1": onehot_equals(open_score, "1"),
        "oral_teeth_gum_2": onehot_equals(open_score, "2"),
        "oral_denture_condition_0": onehot_equals(denture_score, "0"),
        "oral_denture_condition_1": onehot_equals(denture_score, "1"),
        "oral_denture_condition_2": onehot_equals(denture_score, "2"),
        "oral_saliva_flow_0": onehot_equals(breath_score, "0"),
        "oral_saliva_flow_1": onehot_equals(breath_score, "1"),
        "oral_saliva_flow_2": onehot_equals(breath_score, "2"),
        "oral_dryness_0": onehot_equals(drool_score, "0"),
        "oral_dryness_1": onehot_equals(drool_score, "1"),
        "oral_dryness_2": onehot_equals(drool_score, "2"),
        "oral_saliva_0": onehot_equals(drysaliva_score, "0"),
        "oral_saliva_1": onehot_equals(drysaliva_score, "1"),
        "oral_saliva_2": onehot_equals(drysaliva_score, "2"),
        "oral_tongue_0": onehot_equals(tongue_score, "0"),
        "oral_tongue_1": onehot_equals(tongue_score, "1"),
        "oral_tongue_2": onehot_equals(tongue_score, "2"),
        "oral_tongue_surface_0": onehot_equals(tongue_surface_score, "0"),
        "oral_tongue_surface_1": onehot_equals(tongue_surface_score, "1"),
        "oral_tongue_surface_2": onehot_equals(tongue_surface_score, "2"),
        "oral_mucosa_0": onehot_equals(mucosa_score, "0"),
        "oral_mucosa_1": onehot_equals(mucosa_score, "1"),
        "oral_gum_0": onehot_equals(gum_score, "0"),
        "oral_gum_1": onehot_equals(gum_score, "1"),
        "oral_gum_2": onehot_equals(gum_score, "2"),
    }


def ensure_form8_columns(conn: sqlite3.Connection):
    columns = [
        ("urination_status_0", "INTEGER"),
        ("urination_status_1", "INTEGER"),
        ("urination_0", "INTEGER"),
        ("urination_1", "INTEGER"),
        ("urination_frequency_0", "INTEGER"),
        ("urination_frequency_1", "INTEGER"),
        ("urination_frequency_2", "INTEGER"),
        ("urination_frequency_3", "INTEGER"),
        ("urination_control_0", "INTEGER"),
        ("urination_control_1", "INTEGER"),
        ("urination_control_2", "INTEGER"),
        ("urination_control_3", "INTEGER"),
        ("defecation_status_0", "INTEGER"),
        ("defecation_status_a", "INTEGER"),
        ("defecation_status_b", "INTEGER"),
        ("defecation_status_c", "INTEGER"),
        ("defecation_status_d", "INTEGER"),
        ("defecation_status_e", "INTEGER"),
        ("defecation_frequency_0", "INTEGER"),
        ("defecation_frequency_1", "INTEGER"),
        ("defecation_frequency_2", "INTEGER"),
        ("defecation_control_0", "INTEGER"),
        ("defecation_control_1", "INTEGER"),
        ("defecation_control_2", "INTEGER"),
        ("defecation_control_3", "INTEGER"),
        ("defecation_control_4", "INTEGER"),
        ("defecation_method_0", "INTEGER"),
        ("defecation_method_1", "INTEGER"),
        ("defecation_method_2", "INTEGER"),
        ("defecation_method_3", "INTEGER"),
        ("defecation_method_4", "INTEGER"),
        ("excretion_method_A", "INTEGER"),
        ("excretion_method_B", "INTEGER"),
        ("excretion_method_C", "INTEGER"),
        ("excretion_method_D", "INTEGER"),
        ("excretion_method_E", "INTEGER"),
        ("excretion_method_F", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page8_to_form8_columns(page8: dict) -> dict:
    ex = (page8.get("excretion") or page8 or {}) or {}
    u = (ex.get("urination") or page8 or {}) or {}
    d = (ex.get("defecation") or page8 or {}) or {}

    u_status = str(u.get("status") or page8.get("urination_status") or "")
    u_urge = str(u.get("urge") or page8.get("urination") or "")
    u_freq = str(u.get("frequency") or page8.get("urination_frequency") or "")
    u_ctrl = str(u.get("control") or page8.get("urination_control") or "")

    d_status = str(d.get("status") or page8.get("defecation_status") or "")
    d_freq = str(d.get("frequency") or page8.get("defecation_frequency") or "")
    d_ctrl = str(d.get("control") or page8.get("defecation_control") or "")
    d_method = str(d.get("adjustMethod") or page8.get("defecation_method") or "")

    methods = ex.get("excretionMethod")
    if not isinstance(methods, list):
        methods = page8.get("excretion_method")
    if not isinstance(methods, list):
        methods = [] if methods in (None, "", []) else [methods]

    return {
        "urination_status_0": onehot_equals(u_status, "normal"),
        "urination_status_1": onehot_equals(u_status, "abnormal"),
        "urination_0": onehot_equals(u_urge, "no"),
        "urination_1": onehot_equals(u_urge, "yes"),
        "urination_frequency_0": onehot_equals(u_freq, "4-7"),
        "urination_frequency_1": onehot_equals(u_freq, "1-2"),
        "urination_frequency_2": onehot_equals(u_freq, "none"),
        "urination_frequency_3": 0,
        "urination_control_0": onehot_equals(u_ctrl, "0"),
        "urination_control_1": onehot_equals(u_ctrl, "1"),
        "urination_control_2": onehot_equals(u_ctrl, "2"),
        "urination_control_3": onehot_equals(u_ctrl, "3"),
        "defecation_status_0": onehot_equals(d_status, "0"),
        "defecation_status_a": onehot_equals(d_status, "a"),
        "defecation_status_b": onehot_equals(d_status, "b"),
        "defecation_status_c": onehot_equals(d_status, "c"),
        "defecation_status_d": onehot_equals(d_status, "d"),
        "defecation_status_e": onehot_equals(d_status, "e"),
        "defecation_frequency_0": onehot_equals(d_freq, "0"),
        "defecation_frequency_1": onehot_equals(d_freq, "1"),
        "defecation_frequency_2": onehot_equals(d_freq, "2"),
        "defecation_control_0": onehot_equals(d_ctrl, "0"),
        "defecation_control_1": onehot_equals(d_ctrl, "1"),
        "defecation_control_2": onehot_equals(d_ctrl, "2"),
        "defecation_control_3": onehot_equals(d_ctrl, "3"),
        "defecation_control_4": onehot_equals(d_ctrl, "4"),
        "defecation_method_0": onehot_equals(d_method, "0"),
        "defecation_method_1": onehot_equals(d_method, "1"),
        "defecation_method_2": onehot_equals(d_method, "2"),
        "defecation_method_3": onehot_equals(d_method, "3"),
        "defecation_method_4": onehot_equals(d_method, "4"),
        "excretion_method_A": onehot_in(methods, "A"),
        "excretion_method_B": onehot_in(methods, "B"),
        "excretion_method_C": onehot_in(methods, "C"),
        "excretion_method_D": onehot_in(methods, "D"),
        "excretion_method_E": onehot_in(methods, "E"),
        "excretion_method_F": onehot_in(methods, "F"),
    }
def ensure_form9_columns(conn: sqlite3.Connection):
    columns = [
        ("basic1_eating_0", "INTEGER"),
        ("basic1_eating_1", "INTEGER"),
        ("basic1_eating_2", "INTEGER"),
        ("basic1_eating_3", "INTEGER"),
        ("basic1_eating_4", "INTEGER"),
        ("basic1_eating_5", "INTEGER"),
        ("basic1_eating_note", "TEXT"),
        ("basic1_face_hair_0", "INTEGER"),
        ("basic1_face_hair_1", "INTEGER"),
        ("basic1_face_hair_2", "INTEGER"),
        ("basic1_face_hair_3", "INTEGER"),
        ("basic1_face_hair_4", "INTEGER"),
        ("basic1_face_hair_5", "INTEGER"),
        ("basic1_face_hair_note", "TEXT"),
        ("basic1_wipe_0", "INTEGER"),
        ("basic1_wipe_1", "INTEGER"),
        ("basic1_wipe_2", "INTEGER"),
        ("basic1_wipe_3", "INTEGER"),
        ("basic1_wipe_4", "INTEGER"),
        ("basic1_wipe_5", "INTEGER"),
        ("basic1_wipe_note", "TEXT"),
        ("basic1_upper_clothes_0", "INTEGER"),
        ("basic1_upper_clothes_1", "INTEGER"),
        ("basic1_upper_clothes_2", "INTEGER"),
        ("basic1_upper_clothes_3", "INTEGER"),
        ("basic1_upper_clothes_4", "INTEGER"),
        ("basic1_upper_clothes_5", "INTEGER"),
        ("basic1_upper_clothes_note", "TEXT"),
        ("basic1_lower_clothes_0", "INTEGER"),
        ("basic1_lower_clothes_1", "INTEGER"),
        ("basic1_lower_clothes_2", "INTEGER"),
        ("basic1_lower_clothes_3", "INTEGER"),
        ("basic1_lower_clothes_4", "INTEGER"),
        ("basic1_lower_clothes_5", "INTEGER"),
        ("basic1_lower_clothes_note", "TEXT"),
        ("basic1_toilet_0", "INTEGER"),
        ("basic1_toilet_1", "INTEGER"),
        ("basic1_toilet_2", "INTEGER"),
        ("basic1_toilet_3", "INTEGER"),
        ("basic1_toilet_4", "INTEGER"),
        ("basic1_toilet_5", "INTEGER"),
        ("basic1_toilet_note", "TEXT"),
        ("basic1_bath_0", "INTEGER"),
        ("basic1_bath_1", "INTEGER"),
        ("basic1_bath_2", "INTEGER"),
        ("basic1_bath_3", "INTEGER"),
        ("basic1_bath_4", "INTEGER"),
        ("basic1_bath_5", "INTEGER"),
        ("basic1_bath_note", "TEXT"),
        ("basic2_stand_0", "INTEGER"),
        ("basic2_stand_1", "INTEGER"),
        ("basic2_stand_2", "INTEGER"),
        ("basic2_stand_3", "INTEGER"),
        ("basic2_stand_4", "INTEGER"),
        ("basic2_stand_5", "INTEGER"),
        ("basic2_stand_note", "TEXT"),
        ("basic2_getup_0", "INTEGER"),
        ("basic2_getup_1", "INTEGER"),
        ("basic2_getup_2", "INTEGER"),
        ("basic2_getup_3", "INTEGER"),
        ("basic2_getup_4", "INTEGER"),
        ("basic2_getup_5", "INTEGER"),
        ("basic2_getup_note", "TEXT"),
        ("basic2_sit_0", "INTEGER"),
        ("basic2_sit_1", "INTEGER"),
        ("basic2_sit_2", "INTEGER"),
        ("basic2_sit_3", "INTEGER"),
        ("basic2_sit_4", "INTEGER"),
        ("basic2_sit_5", "INTEGER"),
        ("basic2_sit_note", "TEXT"),
        ("basic2_bed_chair_stand_0", "INTEGER"),
        ("basic2_bed_chair_stand_1", "INTEGER"),
        ("basic2_bed_chair_stand_2", "INTEGER"),
        ("basic2_bed_chair_stand_3", "INTEGER"),
        ("basic2_bed_chair_stand_4", "INTEGER"),
        ("basic2_bed_chair_stand_5", "INTEGER"),
        ("basic2_bed_chair_stand_note", "TEXT"),
        ("basic2_both_leg_stand_0", "INTEGER"),
        ("basic2_both_leg_stand_1", "INTEGER"),
        ("basic2_both_leg_stand_2", "INTEGER"),
        ("basic2_both_leg_stand_3", "INTEGER"),
        ("basic2_both_leg_stand_4", "INTEGER"),
        ("basic2_both_leg_stand_5", "INTEGER"),
        ("basic2_both_leg_stand_note", "TEXT"),
        ("basic3_transfer_0", "INTEGER"),
        ("basic3_transfer_1", "INTEGER"),
        ("basic3_transfer_2", "INTEGER"),
        ("basic3_transfer_3", "INTEGER"),
        ("basic3_transfer_4", "INTEGER"),
        ("basic3_transfer_5", "INTEGER"),
        ("basic3_transfer_note", "TEXT"),
        ("basic3_bath_inout_0", "INTEGER"),
        ("basic3_bath_inout_1", "INTEGER"),
        ("basic3_bath_inout_2", "INTEGER"),
        ("basic3_bath_inout_3", "INTEGER"),
        ("basic3_bath_inout_4", "INTEGER"),
        ("basic3_bath_inout_5", "INTEGER"),
        ("basic3_bath_inout_note", "TEXT"),
        ("basic3_walk_home_0", "INTEGER"),
        ("basic3_walk_home_1", "INTEGER"),
        ("basic3_walk_home_2", "INTEGER"),
        ("basic3_walk_home_3", "INTEGER"),
        ("basic3_walk_home_4", "INTEGER"),
        ("basic3_walk_home_5", "INTEGER"),
        ("basic3_walk_home_note", "TEXT"),
        ("basic3_walk_out_0", "INTEGER"),
        ("basic3_walk_out_1", "INTEGER"),
        ("basic3_walk_out_2", "INTEGER"),
        ("basic3_walk_out_3", "INTEGER"),
        ("basic3_walk_out_4", "INTEGER"),
        ("basic3_walk_out_5", "INTEGER"),
        ("basic3_walk_out_note", "TEXT"),
        ("iadl_phone_0", "INTEGER"),
        ("iadl_phone_1", "INTEGER"),
        ("iadl_phone_2", "INTEGER"),
        ("iadl_phone_3", "INTEGER"),
        ("iadl_phone_note", "TEXT"),
        ("iadl_shopping_0", "INTEGER"),
        ("iadl_shopping_1", "INTEGER"),
        ("iadl_shopping_2", "INTEGER"),
        ("iadl_shopping_3", "INTEGER"),
        ("iadl_shopping_note", "TEXT"),
        ("iadl_housework_0", "INTEGER"),
        ("iadl_housework_1", "INTEGER"),
        ("iadl_housework_2", "INTEGER"),
        ("iadl_housework_3", "INTEGER"),
        ("iadl_housework_note", "TEXT"),
        ("iadl_toilet_0", "INTEGER"),
        ("iadl_toilet_1", "INTEGER"),
        ("iadl_toilet_2", "INTEGER"),
        ("iadl_toilet_3", "INTEGER"),
        ("iadl_toilet_note", "TEXT"),
        ("iadl_clean_0", "INTEGER"),
        ("iadl_clean_1", "INTEGER"),
        ("iadl_clean_2", "INTEGER"),
        ("iadl_clean_3", "INTEGER"),
        ("iadl_clean_note", "TEXT"),
        ("iadl_move_0", "INTEGER"),
        ("iadl_move_1", "INTEGER"),
        ("iadl_move_2", "INTEGER"),
        ("iadl_move_3", "INTEGER"),
        ("iadl_move_4", "INTEGER"),
        ("iadl_move_note", "TEXT"),
        ("iadl_money_0", "INTEGER"),
        ("iadl_money_1", "INTEGER"),
        ("iadl_money_2", "INTEGER"),
        ("iadl_money_3", "INTEGER"),
        ("iadl_money_note", "TEXT"),
        ("iadl_medicine_0", "INTEGER"),
        ("iadl_medicine_1", "INTEGER"),
        ("iadl_medicine_2", "INTEGER"),
        ("iadl_medicine_3", "INTEGER"),
        ("iadl_medicine_note", "TEXT"),
        ("iadl_decision_0", "INTEGER"),
        ("iadl_decision_1", "INTEGER"),
        ("iadl_decision_2", "INTEGER"),
        ("iadl_decision_3", "INTEGER"),
        ("iadl_decision_note", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)

def map_page9_to_form9_columns(page9: dict) -> dict:
    dlf = (page9.get("dailyLifeFunction") or page9 or {}) or {}
    adl = dlf.get("adl")
    if not isinstance(adl, list):
        adl = []
    iadl = dlf.get("iadl")
    if not isinstance(iadl, list):
        iadl = []

    def find_adl_row(sub: str) -> dict:
        for row in adl:
            if isinstance(row, dict) and sub in str(row.get("item") or ""):
                return row
        return {}

    def find_iadl_row(sub: str) -> dict:
        for row in iadl:
            if isinstance(row, dict) and sub in str(row.get("item") or ""):
                return row
        return {}

    out: dict = {}
    adl_specs = [
        ("① 食事", "basic1_eating"),
        ("② 洗顔", "basic1_face_hair"),
        ("③ 手足", "basic1_wipe"),
        ("④ 上着", "basic1_upper_clothes"),
        ("⑤ パンツ", "basic1_lower_clothes"),
        ("⑥ トイレ後", "basic1_toilet"),
        ("⑦ 入浴", "basic1_bath"),
        ("⑧ 寝返り", "basic2_stand"),
        ("⑨ 起き上がり", "basic2_getup"),
        ("⑩ 座位", "basic2_sit"),
        ("⑪ ベッド・椅子", "basic2_bed_chair_stand"),
        ("⑫ 両足", "basic2_both_leg_stand"),
        ("⑬ ベッドから", "basic3_transfer"),
        ("⑭ 浴槽", "basic3_bath_inout"),
        ("⑮ 家の中", "basic3_walk_home"),
        ("⑯ 外で", "basic3_walk_out"),
    ]
    for sub, prefix in adl_specs:
        row = find_adl_row(sub)
        sc = str(row.get("score") or "")
        for i in range(6):
            out[f"{prefix}_{i}"] = onehot_equals(sc, str(i))
        out[f"{prefix}_note"] = normalize_text(row.get("note"))

    iadl_specs = [
        ("1. 電話", "iadl_phone", 3),
        ("2. 日用品", "iadl_shopping", 3),
        ("3. 食事の支度", "iadl_housework", 3),
        ("4. 掃除", "iadl_toilet", 3),
        ("5. 洗濯", "iadl_clean", 3),
        ("6. 移動", "iadl_move", 4),
        ("7. 金銭", "iadl_money", 3),
        ("8. 薬", "iadl_medicine", 3),
        ("9. 冷暖房", "iadl_decision", 3),
    ]
    for sub, prefix, mx in iadl_specs:
        row = find_iadl_row(sub)
        sc = str(row.get("score") or "")
        for i in range(mx + 1):
            out[f"{prefix}_{i}"] = onehot_equals(sc, str(i))
        out[f"{prefix}_note"] = normalize_text(row.get("note"))

    # form9.html はフラット項目（basic*/iadl*）で送るため、行配列が無い場合は直接上書き
    for _, prefix in adl_specs:
        direct_score = str(page9.get(prefix) or "")
        if direct_score != "":
            for i in range(6):
                out[f"{prefix}_{i}"] = onehot_equals(direct_score, str(i))
        direct_note = normalize_text(page9.get(f"{prefix}_note"))
        if direct_note is not None:
            out[f"{prefix}_note"] = direct_note

    for _, prefix, mx in iadl_specs:
        direct_score = str(page9.get(prefix) or "")
        if direct_score != "":
            for i in range(mx + 1):
                out[f"{prefix}_{i}"] = onehot_equals(direct_score, str(i))
        direct_note = normalize_text(page9.get(f"{prefix}_note"))
        if direct_note is not None:
            out[f"{prefix}_note"] = direct_note
    return out

def ensure_form10_columns(conn: sqlite3.Connection):
    columns = [
        ("nutrition_self_management_a", "INTEGER"),
        ("nutrition_self_management_b", "INTEGER"),
        ("nutrition_self_management_c", "INTEGER"),
        ("nutrition_self_management_d", "INTEGER"),
        ("nutrition_self_management_e", "INTEGER"),
        ("nutrition_self_management_f", "INTEGER"),
        ("nutrition_self_management_g", "INTEGER"),
        ("nutrition_self_management_h", "INTEGER"),
        ("nutrition_self_management_i", "INTEGER"),
        ("nutrition_self_management_other", "TEXT"),
        ("communication_level_0", "INTEGER"),
        ("communication_level_1", "INTEGER"),
        ("communication_level_2", "INTEGER"),
        ("communication_level_3", "INTEGER"),
        ("conversation_level_0", "INTEGER"),
        ("conversation_level_1", "INTEGER"),
        ("conversation_level_2", "INTEGER"),
        ("conversation_level_3", "INTEGER"),
        ("hearing_level_0", "INTEGER"),
        ("hearing_level_1", "INTEGER"),
        ("hearing_level_2", "INTEGER"),
        ("hearing_level_3", "INTEGER"),
        ("hearing_level_4", "INTEGER"),
        ("daily_communication_0", "INTEGER"),
        ("daily_communication_1", "INTEGER"),
        ("daily_communication_2", "INTEGER"),
        ("daily_communication_3", "INTEGER"),
        ("daily_judgement_0", "INTEGER"),
        ("daily_judgement_1", "INTEGER"),
        ("daily_judgement_2", "INTEGER"),
        ("daily_judgement_3", "INTEGER"),
        ("delirium_signs_exist_0", "INTEGER"),
        ("delirium_signs_exist_1", "INTEGER"),
        ("delirium_signs_a", "INTEGER"),
        ("delirium_signs_b", "INTEGER"),
        ("delirium_signs_c", "INTEGER"),
        ("delirium_signs_d", "INTEGER"),
        ("delirium_signs_e", "INTEGER"),
        ("visual_ability_0", "INTEGER"),
        ("visual_ability_1", "INTEGER"),
        ("visual_ability_2", "INTEGER"),
        ("visual_ability_3", "INTEGER"),
        ("visual_condition_0", "INTEGER"),
        ("visual_condition_1", "INTEGER"),
        ("visual_condition_a", "INTEGER"),
        ("visual_condition_b", "INTEGER"),
        ("visual_condition_c", "INTEGER"),
        ("visual_condition_d", "INTEGER"),
        ("visual_condition_e", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)

def map_page10_to_form10_columns(page10: dict) -> dict:
    chv = (page10.get("communicationHearingVision") or page10 or {}) or {}
    methods = chv.get("communicationMethod")
    if not isinstance(methods, list):
        methods = page10.get("nutrition_self_management")
    if not isinstance(methods, list):
        methods = [] if methods in (None, "", []) else [methods]

    dc = (page10.get("dailyCommunication") or page10 or {}) or {}
    delirium = (dc.get("delirium") or page10 or {}) or {}
    signs = delirium.get("signs")
    if not isinstance(signs, list):
        signs = page10.get("delirium_signs")
    if not isinstance(signs, list):
        signs = [] if signs in (None, "", []) else [signs]

    vis = (page10.get("vision") or page10 or {}) or {}
    cond_detail = vis.get("conditionDetail")
    if not isinstance(cond_detail, list):
        cond_detail = page10.get("visual_condition_detail")
    if not isinstance(cond_detail, list):
        cond_detail = [] if cond_detail in (None, "", []) else [cond_detail]

    out = {}
    for letter in "abcdefghi":
        out[f"nutrition_self_management_{letter}"] = onehot_in(methods, letter)
    out["nutrition_self_management_other"] = normalize_text(chv.get("communicationMethodOther") or page10.get("nutrition_self_management_other"))

    cl = str(chv.get("communicationLevel") or page10.get("communication_level") or "")
    for i in range(4):
        out[f"communication_level_{i}"] = onehot_equals(cl, str(i))

    conv = str(chv.get("conversationLevel") or page10.get("conversation_level") or "")
    for i in range(4):
        out[f"conversation_level_{i}"] = onehot_equals(conv, str(i))

    hl = str(chv.get("hearingLevel") or page10.get("hearing_level") or "")
    for i in range(5):
        out[f"hearing_level_{i}"] = onehot_equals(hl, str(i))

    dcomm = str(dc.get("dailyCommunication") or page10.get("daily_communication") or "")
    for i in range(4):
        out[f"daily_communication_{i}"] = onehot_equals(dcomm, str(i))

    dj = str(dc.get("dailyJudgement") or page10.get("daily_judgement") or "")
    for i in range(4):
        out[f"daily_judgement_{i}"] = onehot_equals(dj, str(i))

    dex = str(delirium.get("exists") or page10.get("delirium_signs_exist") or "")
    out["delirium_signs_exist_0"] = onehot_equals(dex, "0")
    out["delirium_signs_exist_1"] = onehot_equals(dex, "1")
    for letter in "abcde":
        out[f"delirium_signs_{letter}"] = onehot_in(signs, letter)

    va = str(vis.get("ability") or page10.get("visual_ability") or "")
    for i in range(4):
        out[f"visual_ability_{i}"] = onehot_equals(va, str(i))

    vc = str(vis.get("condition") or page10.get("visual_condition") or "")
    out["visual_condition_0"] = onehot_equals(vc, "0")
    out["visual_condition_1"] = onehot_equals(vc, "1")
    for letter in "abcde":
        out[f"visual_condition_{letter}"] = onehot_in(cond_detail, letter)

    return out

def ensure_form11_columns(conn: sqlite3.Connection):
    columns = [
        ("m11_nutrition_self_a", "INTEGER"),
        ("m11_nutrition_self_b", "INTEGER"),
        ("m11_nutrition_self_c", "INTEGER"),
        ("m11_nutrition_self_d", "INTEGER"),
        ("m11_nutrition_self_e", "INTEGER"),
        ("m11_nutrition_self_f", "INTEGER"),
        ("m11_nutrition_self_g", "INTEGER"),
        ("m11_nutrition_self_h", "INTEGER"),
        ("emotion_level_0", "INTEGER"),
        ("emotion_level_1", "INTEGER"),
        ("emotion_level_2", "INTEGER"),
        ("emotion_level_3", "INTEGER"),
        ("emotion_level_4", "INTEGER"),
        ("m_health_1_1", "INTEGER"),
        ("m_health_1_2", "INTEGER"),
        ("m_health_2_1", "INTEGER"),
        ("m_health_2_2", "INTEGER"),
        ("m_health_3_1", "INTEGER"),
        ("m_health_3_2", "INTEGER"),
        ("m_health_4_1", "INTEGER"),
        ("m_health_4_2", "INTEGER"),
        ("m_health_5_1", "INTEGER"),
        ("m_health_5_2", "INTEGER"),
        ("m_health_6_1", "INTEGER"),
        ("m_health_6_2", "INTEGER"),
        ("m_health_7_1", "INTEGER"),
        ("m_health_7_2", "INTEGER"),
        ("m_health_8_1", "INTEGER"),
        ("m_health_8_2", "INTEGER"),
        ("m_health_8_detail", "TEXT"),
        ("a_positive_count", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page11_to_form11_columns(page11: dict) -> dict:
    cog = (page11.get("cognitiveStatus") or page11 or {}) or {}
    rank = str(cog.get("independenceRank") or page11.get("nutrition_self_management") or "")

    hl = (page11.get("healthLiteracy") or page11 or {}) or {}
    el = str(hl.get("emotionLevel") or page11.get("emotion_level") or "")

    dep = (page11.get("depressiveState") or page11 or {}) or {}

    out: dict = {}
    for letter in "abcdefgh":
        out[f"m11_nutrition_self_{letter}"] = onehot_equals(rank, f"nutrition_self_management_{letter}")
    for i in range(5):
        out[f"emotion_level_{i}"] = onehot_equals(el, str(i))
    for n in range(1, 9):
        qv = str(dep.get(f"q{n}") or page11.get(f"m_health_{n}") or "")
        out[f"m_health_{n}_1"] = onehot_equals(qv, f"m_health_{n}_1")
        out[f"m_health_{n}_2"] = onehot_equals(qv, f"m_health_{n}_2")
    out["m_health_8_detail"] = normalize_text(dep.get("q8Detail") or page11.get("m_health_8_detail"))
    out["a_positive_count"] = to_int_or_none(dep.get("aPositiveCount")) if to_int_or_none(dep.get("aPositiveCount")) is not None else to_int_or_none(page11.get("a_positive_count"))
    return out


def ensure_form12_columns(conn: sqlite3.Connection):
    columns = [
        ("has_psy_0", "INTEGER"),
        ("has_psy_1", "INTEGER"),
        ("information_provider_1", "INTEGER"),
        ("information_provider_2", "INTEGER"),
        ("information_provider_3", "INTEGER"),
        ("information_provider_4", "INTEGER"),
        ("information_provider_5", "INTEGER"),
        ("information_provider_6", "INTEGER"),
        ("information_provider_other", "TEXT"),
        ("npiq_delusion_0", "INTEGER"),
        ("npiq_delusion_1", "INTEGER"),
        ("npiq_delusion_2", "INTEGER"),
        ("npiq_delusion_3", "INTEGER"),
        ("npiq_hallucination_0", "INTEGER"),
        ("npiq_hallucination_1", "INTEGER"),
        ("npiq_hallucination_2", "INTEGER"),
        ("npiq_hallucination_3", "INTEGER"),
        ("npiq_agitation_0", "INTEGER"),
        ("npiq_agitation_1", "INTEGER"),
        ("npiq_agitation_2", "INTEGER"),
        ("npiq_agitation_3", "INTEGER"),
        ("npiq_depression_0", "INTEGER"),
        ("npiq_depression_1", "INTEGER"),
        ("npiq_depression_2", "INTEGER"),
        ("npiq_depression_3", "INTEGER"),
        ("npiq_anxiety_0", "INTEGER"),
        ("npiq_anxiety_1", "INTEGER"),
        ("npiq_anxiety_2", "INTEGER"),
        ("npiq_anxiety_3", "INTEGER"),
        ("npiq_euphoria_0", "INTEGER"),
        ("npiq_euphoria_1", "INTEGER"),
        ("npiq_euphoria_2", "INTEGER"),
        ("npiq_euphoria_3", "INTEGER"),
        ("npiq_apathy_0", "INTEGER"),
        ("npiq_apathy_1", "INTEGER"),
        ("npiq_apathy_2", "INTEGER"),
        ("npiq_apathy_3", "INTEGER"),
        ("npiq_disinhibition_0", "INTEGER"),
        ("npiq_disinhibition_1", "INTEGER"),
        ("npiq_disinhibition_2", "INTEGER"),
        ("npiq_disinhibition_3", "INTEGER"),
        ("npiq_irritability_0", "INTEGER"),
        ("npiq_irritability_1", "INTEGER"),
        ("npiq_irritability_2", "INTEGER"),
        ("npiq_irritability_3", "INTEGER"),
        ("npiq_abnormal_behavior_0", "INTEGER"),
        ("npiq_abnormal_behavior_1", "INTEGER"),
        ("npiq_abnormal_behavior_2", "INTEGER"),
        ("npiq_abnormal_behavior_3", "INTEGER"),
        ("npiq_night_behavior_0", "INTEGER"),
        ("npiq_night_behavior_1", "INTEGER"),
        ("npiq_night_behavior_2", "INTEGER"),
        ("npiq_night_behavior_3", "INTEGER"),
        ("npiq_eating_behavior_0", "INTEGER"),
        ("npiq_eating_behavior_1", "INTEGER"),
        ("npiq_eating_behavior_2", "INTEGER"),
        ("npiq_eating_behavior_3", "INTEGER"),
        ("npiq_total_score", "INTEGER"),
        ("npiq_score_note", "TEXT"),
        ("npiq_behavior_detail", "TEXT"),
        ("gaf_score", "INTEGER"),
        ("gaf_note", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page12_to_form12_columns(page12: dict) -> dict:
    psy = (page12.get("psyScreening") or page12 or {}) or {}
    npiq = (page12.get("npiq") or page12 or {}) or {}

    has_psy = str(psy.get("has_psy") or "")
    provider = str(npiq.get("information_provider") or "")

    out = {
        "has_psy_0": onehot_equals(has_psy, "0"),
        "has_psy_1": onehot_equals(has_psy, "1"),
        "information_provider_1": onehot_equals(provider, "1"),
        "information_provider_2": onehot_equals(provider, "2"),
        "information_provider_3": onehot_equals(provider, "3"),
        "information_provider_4": onehot_equals(provider, "4"),
        "information_provider_5": onehot_equals(provider, "5"),
        "information_provider_6": onehot_equals(provider, "6"),
        "information_provider_other": normalize_text(npiq.get("information_provider_other")),
        "npiq_total_score": to_int_or_none(npiq.get("npiq_total_score")),
        "npiq_score_note": normalize_text(npiq.get("npiq_score_note")),
        "npiq_behavior_detail": normalize_text(npiq.get("npiq_score_note")),
        "gaf_score": None,
        "gaf_note": None,
    }

    for key in [
        "npiq_delusion","npiq_hallucination","npiq_agitation","npiq_depression","npiq_anxiety","npiq_euphoria",
        "npiq_apathy","npiq_disinhibition","npiq_irritability","npiq_abnormal_behavior","npiq_night_behavior","npiq_eating_behavior"
    ]:
        v = str(npiq.get(key) or "")
        for i in range(4):
            out[f"{key}_{i}"] = onehot_equals(v, str(i))

    return out


def ensure_form13_columns(conn: sqlite3.Connection):
    columns = [
        ("gaf_score", "INTEGER"),
        ("gaf_note", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page13_to_form13_columns(page13: dict) -> dict:
    gaf = (page13.get("gaf") or page13 or {}) or {}
    return {
        "gaf_score": to_int_or_none(gaf.get("gaf_score")),
        "gaf_note": normalize_text(gaf.get("gaf_note")),
    }


def ensure_form14_columns(conn: sqlite3.Connection):
    columns = [
        ("frailty_exist_0", "INTEGER"),
        ("frailty_exist_1", "INTEGER"),
        ("frailty_detail_1", "INTEGER"),
        ("frailty_detail_2", "INTEGER"),
        ("frailty_detail_3", "INTEGER"),
        ("frailty_detail_4", "INTEGER"),
        ("frailty_other", "TEXT"),
        ("dementia_exist_0", "INTEGER"),
        ("dementia_exist_1", "INTEGER"),
        ("dementia_detail_1", "INTEGER"),
        ("dementia_detail_2", "INTEGER"),
        ("dementia_detail_3", "INTEGER"),
        ("dementia_detail_4", "INTEGER"),
        ("dementia_other", "TEXT"),
        ("cancer_exist_0", "INTEGER"),
        ("cancer_exist_1", "INTEGER"),
        ("cancer_detail_1", "INTEGER"),
        ("cancer_detail_2", "INTEGER"),
        ("cancer_detail_3", "INTEGER"),
        ("cancer_detail_4", "INTEGER"),
        ("cancer_detail_5", "INTEGER"),
        ("cancer_detail_6", "INTEGER"),
        ("cancer_detail_7", "INTEGER"),
        ("cancer_other", "TEXT"),
        ("circulatory_exist_0", "INTEGER"),
        ("circulatory_exist_1", "INTEGER"),
        ("circulatory_freewrite_input", "TEXT"),
        ("bone_exist_0", "INTEGER"),
        ("bone_exist_1", "INTEGER"),
        ("bone_detail_1", "INTEGER"),
        ("bone_detail_2", "INTEGER"),
        ("bone_detail_3", "INTEGER"),
        ("bone_detail_4", "INTEGER"),
        ("bone_detail_5", "INTEGER"),
        ("bone_detail_6", "INTEGER"),
        ("bone_other", "TEXT"),
        ("leg_circulation_exist_0", "INTEGER"),
        ("leg_circulation_exist_1", "INTEGER"),
        ("leg_circulation_freewrite_input", "TEXT"),
        ("doctor_diagnosis_note", "TEXT"),
        ("other_hospital_1", "TEXT"),
        ("diagnosis_1", "TEXT"),
        ("treatment_content_1", "TEXT"),
        ("remarks_1", "TEXT"),
        ("other_hospital_2", "TEXT"),
        ("diagnosis_2", "TEXT"),
        ("treatment_content_2", "TEXT"),
        ("remarks_2", "TEXT"),
        ("other_hospital_3", "TEXT"),
        ("diagnosis_3", "TEXT"),
        ("treatment_content_3", "TEXT"),
        ("remarks_3", "TEXT"),
        ("yes_no_select_0", "INTEGER"),
        ("yes_no_select_1", "INTEGER"),
        ("no_reason_a", "INTEGER"),
        ("no_reason_b", "INTEGER"),
        ("no_reason_c", "INTEGER"),
        ("no_reason_d", "INTEGER"),
        ("no_reason_e", "INTEGER"),
        ("no_reason_f", "INTEGER"),
        ("nutrition_exist_0", "INTEGER"),
        ("nutrition_exist_1", "INTEGER"),
        ("injection_exist_0", "INTEGER"),
        ("injection_exist_1", "INTEGER"),
        ("catheter_exist_0", "INTEGER"),
        ("catheter_exist_1", "INTEGER"),
        ("tracheotomy_exist_0", "INTEGER"),
        ("tracheotomy_exist_1", "INTEGER"),
        ("respiration_exist_0", "INTEGER"),
        ("respiration_exist_1", "INTEGER"),
        ("dialysis_exist_0", "INTEGER"),
        ("dialysis_exist_1", "INTEGER"),
        ("stoma_exist_0", "INTEGER"),
        ("stoma_exist_1", "INTEGER"),
        ("wound_exist_0", "INTEGER"),
        ("wound_exist_1", "INTEGER"),
        ("pain_management_exist_0", "INTEGER"),
        ("pain_management_exist_1", "INTEGER"),
        ("self_measurement_exist_0", "INTEGER"),
        ("self_measurement_exist_1", "INTEGER"),
        ("oral_care_exist_0", "INTEGER"),
        ("oral_care_exist_1", "INTEGER"),
        ("drug_management_exist_0", "INTEGER"),
        ("drug_management_exist_1", "INTEGER"),
        ("rehab_equipment_exist_0", "INTEGER"),
        ("rehab_equipment_exist_1", "INTEGER"),
        ("rehab_aids_exist_0", "INTEGER"),
        ("rehab_aids_exist_1", "INTEGER"),
        ("nutrition_type_central_venous", "INTEGER"),
        ("nutrition_type_nasal", "INTEGER"),
        ("nutrition_type_peg", "INTEGER"),
        ("injection_type_subcutaneous_infusion", "INTEGER"),
        ("injection_type_blood_transfusion", "INTEGER"),
        ("injection_type_insulin_self_injection", "INTEGER"),
        ("injection_type_intravenous_injection", "INTEGER"),
        ("injection_type_drip_infusion", "INTEGER"),
        ("injection_type_subcutaneous_im_non_insulin", "INTEGER"),
        ("catheter_type_indwelling_bladder_catheter", "INTEGER"),
        ("catheter_type_condom_catheter", "INTEGER"),
        ("catheter_type_self_catheterization", "INTEGER"),
        ("catheter_type_renal_catheter", "INTEGER"),
        ("catheter_type_bladder_drainage", "INTEGER"),
        ("catheter_type_liver_catheter", "INTEGER"),
        ("tracheotomy_type_suction", "INTEGER"),
        ("tracheotomy_type_inhalation", "INTEGER"),
        ("respiration_type_suction", "INTEGER"),
        ("respiration_type_inhalation", "INTEGER"),
        ("respiration_type_home_oxygen", "INTEGER"),
        ("respiration_type_ventilator", "INTEGER"),
        ("dialysis_type_capd_apd", "INTEGER"),
        ("dialysis_type_hemodialysis", "INTEGER"),
        ("stoma_type_artificial_anus", "INTEGER"),
        ("stoma_type_artificial_bladder", "INTEGER"),
        ("wound_type_pressure_ulcer", "INTEGER"),
        ("wound_type_wound", "INTEGER"),
        ("pain_management_subcutaneous_injection", "INTEGER"),
        ("pain_management_epidural_injection", "INTEGER"),
        ("pain_management_oral_medication", "INTEGER"),
        ("pain_management_patch_or_mucosal", "INTEGER"),
        ("narcotic_use_yes", "INTEGER"),
        ("narcotic_use_no", "INTEGER"),
        ("self_measurement_blood_glucose", "INTEGER"),
        ("self_measurement_continuous_monitor", "INTEGER"),
        ("oral_visit_clinic", "INTEGER"),
        ("oral_visit_home_visit", "INTEGER"),
        ("oral_visit_dental_hygienist_visit", "INTEGER"),
        ("drug_management_oral_medication", "INTEGER"),
        ("drug_management_suppository", "INTEGER"),
        ("drug_management_eye_drops", "INTEGER"),
        ("drug_management_external_medicine", "INTEGER"),
        ("drug_management_injection", "INTEGER"),
        ("rehab_equipment_description", "TEXT"),
        ("rehab_aids_description", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page14_to_form14_columns(page14: dict) -> dict:
    ds = (page14.get("diseaseStatus") or page14 or {}) or {}
    frailty = (ds.get("frailty") or page14 or {}) or {}
    dementia = (ds.get("dementia") or page14 or {}) or {}
    cancer = (ds.get("cancer") or page14 or {}) or {}
    circulatory = (ds.get("circulatory") or page14 or {}) or {}
    bone = (ds.get("bone") or page14 or {}) or {}
    other_disease = (ds.get("otherDisease") or page14 or {}) or {}

    dp = (page14.get("doctorPlan") or page14 or {}) or {}
    hospitals = dp.get("other_hospitals")
    if not isinstance(hospitals, list):
        hospitals = []

    vb = (page14.get("visitingBehavior") or page14 or {}) or {}
    no_reason = vb.get("no_reason")
    if not isinstance(no_reason, list):
        no_reason = [] if no_reason in (None, "", []) else [no_reason]

    mc = (page14.get("medicalCare") or page14 or {}) or {}
    def as_list(v):
        if isinstance(v, list):
            return v
        return [] if v in (None, "", []) else [v]

    nutrition_type = as_list(mc.get("nutrition_type"))
    injection_type = as_list(mc.get("injection_type"))
    catheter_type = as_list(mc.get("catheter_type"))
    tracheotomy_type = as_list(mc.get("tracheotomy_type"))
    respiration_type = as_list(mc.get("respiration_type"))
    dialysis_type = as_list(mc.get("dialysis_type"))
    stoma_type = as_list(mc.get("stoma_type"))
    wound_type = as_list(mc.get("wound_type"))
    pain_management = as_list(mc.get("pain_management"))
    self_measurement = as_list(mc.get("self_measurement"))
    oral_visit = as_list(mc.get("oral_visit"))
    drug_management = as_list(mc.get("drug_management"))

    out = {
        "frailty_exist_0": onehot_equals(str(frailty.get("frailty_exist") or ""), "0"),
        "frailty_exist_1": onehot_equals(str(frailty.get("frailty_exist") or ""), "1"),
        "frailty_other": normalize_text(frailty.get("frailty_other")),
        "dementia_exist_0": onehot_equals(str(dementia.get("dementia_exist") or ""), "0"),
        "dementia_exist_1": onehot_equals(str(dementia.get("dementia_exist") or ""), "1"),
        "dementia_other": normalize_text(dementia.get("dementia_other")),
        "cancer_exist_0": onehot_equals(str(cancer.get("cancer_exist") or ""), "0"),
        "cancer_exist_1": onehot_equals(str(cancer.get("cancer_exist") or ""), "1"),
        "cancer_other": normalize_text(cancer.get("cancer_other")),
        "circulatory_exist_0": onehot_equals(str(circulatory.get("circulatory_exist") or ""), "0"),
        "circulatory_exist_1": onehot_equals(str(circulatory.get("circulatory_exist") or ""), "1"),
        "circulatory_freewrite_input": normalize_text(circulatory.get("circulatory_freewrite_input")),
        "bone_exist_0": onehot_equals(str(bone.get("bone_exist") or ""), "0"),
        "bone_exist_1": onehot_equals(str(bone.get("bone_exist") or ""), "1"),
        "bone_other": normalize_text(bone.get("bone_other")),
        "leg_circulation_exist_0": onehot_equals(str(other_disease.get("leg_circulation_exist") or ""), "0"),
        "leg_circulation_exist_1": onehot_equals(str(other_disease.get("leg_circulation_exist") or ""), "1"),
        "leg_circulation_freewrite_input": normalize_text(other_disease.get("leg_circulation_freewrite_input") or other_disease.get("leg_circulation_other")),
        "doctor_diagnosis_note": normalize_text(dp.get("doctor_diagnosis_note")),
        "yes_no_select_0": onehot_equals(str(vb.get("yes_no_select") or ""), "yes"),
        "yes_no_select_1": onehot_equals(str(vb.get("yes_no_select") or ""), "no"),
        "nutrition_exist_0": onehot_equals(str(mc.get("nutrition_exist") or ""), "0"),
        "nutrition_exist_1": onehot_equals(str(mc.get("nutrition_exist") or ""), "1"),
        "injection_exist_0": onehot_equals(str(mc.get("injection_exist") or ""), "0"),
        "injection_exist_1": onehot_equals(str(mc.get("injection_exist") or ""), "1"),
        "catheter_exist_0": onehot_equals(str(mc.get("catheter_exist") or ""), "0"),
        "catheter_exist_1": onehot_equals(str(mc.get("catheter_exist") or ""), "1"),
        "tracheotomy_exist_0": onehot_equals(str(mc.get("tracheotomy_exist") or ""), "0"),
        "tracheotomy_exist_1": onehot_equals(str(mc.get("tracheotomy_exist") or ""), "1"),
        "respiration_exist_0": onehot_equals(str(mc.get("respiration_exist") or ""), "0"),
        "respiration_exist_1": onehot_equals(str(mc.get("respiration_exist") or ""), "1"),
        "dialysis_exist_0": onehot_equals(str(mc.get("dialysis_exist") or ""), "0"),
        "dialysis_exist_1": onehot_equals(str(mc.get("dialysis_exist") or ""), "1"),
        "stoma_exist_0": onehot_equals(str(mc.get("stoma_exist") or ""), "0"),
        "stoma_exist_1": onehot_equals(str(mc.get("stoma_exist") or ""), "1"),
        "wound_exist_0": onehot_equals(str(mc.get("wound_exist") or ""), "0"),
        "wound_exist_1": onehot_equals(str(mc.get("wound_exist") or ""), "1"),
        "pain_management_exist_0": onehot_equals(str(mc.get("pain_management_exist") or ""), "0"),
        "pain_management_exist_1": onehot_equals(str(mc.get("pain_management_exist") or ""), "1"),
        "self_measurement_exist_0": onehot_equals(str(mc.get("self_measurement_exist") or ""), "0"),
        "self_measurement_exist_1": onehot_equals(str(mc.get("self_measurement_exist") or ""), "1"),
        "oral_care_exist_0": onehot_equals(str(mc.get("oral_care_exist") or ""), "0"),
        "oral_care_exist_1": onehot_equals(str(mc.get("oral_care_exist") or ""), "1"),
        "drug_management_exist_0": onehot_equals(str(mc.get("drug_management_exist") or ""), "0"),
        "drug_management_exist_1": onehot_equals(str(mc.get("drug_management_exist") or ""), "1"),
        "rehab_equipment_exist_0": onehot_equals(str(mc.get("rehab_equipment_exist") or ""), "0"),
        "rehab_equipment_exist_1": onehot_equals(str(mc.get("rehab_equipment_exist") or ""), "1"),
        "rehab_aids_exist_0": onehot_equals(str(mc.get("rehab_aids_exist") or ""), "0"),
        "rehab_aids_exist_1": onehot_equals(str(mc.get("rehab_aids_exist") or ""), "1"),
        "narcotic_use_yes": onehot_equals(str(mc.get("narcotic_use") or ""), "yes"),
        "narcotic_use_no": onehot_equals(str(mc.get("narcotic_use") or ""), "no"),
        "rehab_equipment_description": normalize_text(mc.get("rehab_equipment_description")),
        "rehab_aids_description": normalize_text(mc.get("rehab_aids_description")),
    }

    for i in range(1,5): out[f"frailty_detail_{i}"] = onehot_equals(str(frailty.get("frailty_detail_select") or ""), str(i))
    for i in range(1,5): out[f"dementia_detail_{i}"] = onehot_equals(str(dementia.get("dementia_detail_select") or ""), str(i))
    for i in range(1,8): out[f"cancer_detail_{i}"] = onehot_equals(str(cancer.get("cancer_detail_select") or ""), str(i))
    for i in range(1,7): out[f"bone_detail_{i}"] = onehot_equals(str(bone.get("bone_detail_select") or ""), str(i))

    for i in range(1,4):
        row = hospitals[i-1] if i-1 < len(hospitals) and isinstance(hospitals[i-1], dict) else {}
        out[f"other_hospital_{i}"] = normalize_text(row.get("other_hospital"))
        out[f"diagnosis_{i}"] = normalize_text(row.get("diagnosis"))
        out[f"treatment_content_{i}"] = normalize_text(row.get("treatment_content"))
        out[f"remarks_{i}"] = normalize_text(row.get("remarks"))

    for ch in "abcdef": out[f"no_reason_{ch}"] = onehot_in(no_reason, ch)

    for n in ["central_venous","nasal","peg"]: out[f"nutrition_type_{n}"] = onehot_in(nutrition_type, n)
    for n in ["subcutaneous_infusion","blood_transfusion","insulin_self_injection","intravenous_injection","drip_infusion","subcutaneous_im_non_insulin"]: out[f"injection_type_{n}"] = onehot_in(injection_type, n)
    for n in ["indwelling_bladder_catheter","condom_catheter","self_catheterization","renal_catheter","bladder_drainage","liver_catheter"]: out[f"catheter_type_{n}"] = onehot_in(catheter_type, n)
    for n in ["suction","inhalation"]: out[f"tracheotomy_type_{n}"] = onehot_in(tracheotomy_type, n)
    for n in ["suction","inhalation","home_oxygen","ventilator"]: out[f"respiration_type_{n}"] = onehot_in(respiration_type, n)
    for n in ["capd_apd","hemodialysis"]: out[f"dialysis_type_{n}"] = onehot_in(dialysis_type, n)
    for n in ["artificial_anus","artificial_bladder"]: out[f"stoma_type_{n}"] = onehot_in(stoma_type, n)
    for n in ["pressure_ulcer","wound"]: out[f"wound_type_{n}"] = onehot_in(wound_type, n)
    for n in ["subcutaneous_injection","epidural_injection","oral_medication","patch_or_mucosal"]: out[f"pain_management_{n}"] = onehot_in(pain_management, n)
    for n in ["blood_glucose","continuous_monitor"]: out[f"self_measurement_{n}"] = onehot_in(self_measurement, n)
    for n in ["clinic","home_visit","dental_hygienist_visit"]: out[f"oral_visit_{n}"] = onehot_in(oral_visit, n)
    for n in ["oral_medication","suppository","eye_drops","external_medicine","injection"]: out[f"drug_management_{n}"] = onehot_in(drug_management, n)

    return out


def ensure_form15_columns(conn: sqlite3.Connection):
    columns = [
        ("strange_feeling_0", "INTEGER"),
        ("strange_feeling_1", "INTEGER"),
        ("vital_change_overall_detail", "TEXT"),
        ("vital_respiration_0", "INTEGER"),
        ("vital_respiration_1", "INTEGER"),
        ("vital_spo2_0", "INTEGER"),
        ("vital_spo2_1", "INTEGER"),
        ("vital_temp_0", "INTEGER"),
        ("vital_temp_1", "INTEGER"),
        ("vital_bp_0", "INTEGER"),
        ("vital_bp_1", "INTEGER"),
        ("vital_pulse_0", "INTEGER"),
        ("vital_pulse_1", "INTEGER"),
        ("consciousness_level_0", "INTEGER"),
        ("consciousness_level_1", "INTEGER"),
        ("consciousness_level_2", "INTEGER"),
        ("skin_changes_0", "INTEGER"),
        ("skin_changes_1", "INTEGER"),
        ("dyspnea_grade_0", "INTEGER"),
        ("dyspnea_grade_1", "INTEGER"),
        ("dyspnea_grade_2", "INTEGER"),
        ("dyspnea_grade_3", "INTEGER"),
        ("dyspnea_grade_4", "INTEGER"),
        ("nyha_class_0", "INTEGER"),
        ("nyha_class_I", "INTEGER"),
        ("nyha_class_II", "INTEGER"),
        ("nyha_class_III", "INTEGER"),
        ("nyha_class_IV", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page15_to_form15_columns(page15: dict) -> dict:
    ds = (page15.get("diseaseSigns") or page15 or {}) or {}
    vs = (page15.get("vitalSigns") or page15 or {}) or {}
    rg = (page15.get("respiratoryGrade") or page15 or {}) or {}

    strange = str(ds.get("vital_change_overall") or "")
    respiration = str(vs.get("respiration_rate") or "")
    spo2 = str(vs.get("vital_spo2") or "")
    temp = str(vs.get("vital_temp") or "")
    bp = str(vs.get("vital_bp") or "")
    pulse = str(vs.get("vital_pulse") or "")
    consciousness = str(vs.get("consciousness_level") or "")
    skin = str(vs.get("skin_changes") or "")
    dyspnea = str(rg.get("breath_grade") or "")
    nyha = str(rg.get("nyha_class") or "")

    return {
        "strange_feeling_0": onehot_equals(strange, "0"),
        "strange_feeling_1": onehot_equals(strange, "1"),
        "vital_change_overall_detail": normalize_text(ds.get("vital_change_overall_detail")),
        "vital_respiration_0": onehot_equals(respiration, "0"),
        "vital_respiration_1": onehot_equals(respiration, "1"),
        "vital_spo2_0": onehot_equals(spo2, "0"),
        "vital_spo2_1": onehot_equals(spo2, "1"),
        "vital_temp_0": onehot_equals(temp, "0"),
        "vital_temp_1": onehot_equals(temp, "1"),
        "vital_bp_0": onehot_equals(bp, "0"),
        "vital_bp_1": onehot_equals(bp, "1"),
        "vital_pulse_0": onehot_equals(pulse, "0"),
        "vital_pulse_1": onehot_equals(pulse, "1"),
        "consciousness_level_0": onehot_equals(consciousness, "0"),
        "consciousness_level_1": onehot_equals(consciousness, "1"),
        "consciousness_level_2": onehot_equals(consciousness, "2"),
        "skin_changes_0": onehot_equals(skin, "0"),
        "skin_changes_1": onehot_equals(skin, "1"),
        "dyspnea_grade_0": onehot_equals(dyspnea, "0"),
        "dyspnea_grade_1": onehot_equals(dyspnea, "1"),
        "dyspnea_grade_2": onehot_equals(dyspnea, "2"),
        "dyspnea_grade_3": onehot_equals(dyspnea, "3"),
        "dyspnea_grade_4": onehot_equals(dyspnea, "4"),
        "nyha_class_0": onehot_equals(nyha, "0"),
        "nyha_class_I": onehot_equals(nyha, "I"),
        "nyha_class_II": onehot_equals(nyha, "II"),
        "nyha_class_III": onehot_equals(nyha, "III"),
        "nyha_class_IV": onehot_equals(nyha, "IV"),
    }


def ensure_form16_columns(conn: sqlite3.Connection):
    columns = [
        ("has_bedsore_0", "INTEGER"),
        ("has_bedsore_1", "INTEGER"),
        ("has_pain_0", "INTEGER"),
        ("has_pain_1", "INTEGER"),
        ("has_paralysis_0", "INTEGER"),
        ("has_paralysis_1", "INTEGER"),
        ("has_kannsetsu_0", "INTEGER"),
        ("has_kannsetsu_1", "INTEGER"),
        ("wound_depth_d0", "INTEGER"),
        ("wound_depth_d1", "INTEGER"),
        ("wound_depth_d2", "INTEGER"),
        ("wound_depth_d3", "INTEGER"),
        ("wound_depth_d4", "INTEGER"),
        ("wound_depth_d5", "INTEGER"),
        ("wound_depth_dti", "INTEGER"),
        ("wound_depth_du", "INTEGER"),
        ("wound_exudate_e0", "INTEGER"),
        ("wound_exudate_e1", "INTEGER"),
        ("wound_exudate_e3", "INTEGER"),
        ("wound_exudate_e6", "INTEGER"),
        ("wound_size_s0", "INTEGER"),
        ("wound_size_s3", "INTEGER"),
        ("wound_size_s6", "INTEGER"),
        ("wound_size_s8", "INTEGER"),
        ("wound_size_s9", "INTEGER"),
        ("wound_size_s12", "INTEGER"),
        ("wound_size_s15", "INTEGER"),
        ("wound_infection_i0", "INTEGER"),
        ("wound_infection_i1", "INTEGER"),
        ("wound_infection_i3c", "INTEGER"),
        ("wound_infection_i3", "INTEGER"),
        ("wound_infection_i9", "INTEGER"),
        ("wound_granulation_g0", "INTEGER"),
        ("wound_granulation_g1", "INTEGER"),
        ("wound_granulation_g3", "INTEGER"),
        ("wound_granulation_g4", "INTEGER"),
        ("wound_granulation_g5", "INTEGER"),
        ("wound_granulation_g6", "INTEGER"),
        ("wound_necrosis_n0", "INTEGER"),
        ("wound_necrosis_n3", "INTEGER"),
        ("wound_necrosis_n6", "INTEGER"),
        ("wound_pocket_p0", "INTEGER"),
        ("wound_pocket_p6", "INTEGER"),
        ("wound_pocket_p6_4to16", "INTEGER"),
        ("wound_pocket_p12", "INTEGER"),
        ("wound_pocket_p24", "INTEGER"),
        ("wound_total_score", "INTEGER"),
        ("pain_image_front", "TEXT"),
        ("pain_image_back", "TEXT"),
        ("mahi_image_front", "TEXT"),
        ("mahi_image_back", "TEXT"),
        ("kan_image_front", "TEXT"),
        ("kan_image_back", "TEXT"),
        ("jokusou_image_front", "TEXT"),
        ("jokusou_image_back", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page16_to_form16_columns(page16: dict) -> dict:
    bedsore = (page16.get("bedsore") or page16 or {}) or {}
    design = (bedsore.get("designR") or page16 or {}) or {}
    ppc = (page16.get("painParalysisContracture") or page16 or {}) or {}

    out = {
        "has_bedsore_0": onehot_equals(str(bedsore.get("has_bedsore") or ""), "0"),
        "has_bedsore_1": onehot_equals(str(bedsore.get("has_bedsore") or ""), "1"),
        "has_pain_0": onehot_equals(str(ppc.get("has_pain") or ""), "0"),
        "has_pain_1": onehot_equals(str(ppc.get("has_pain") or ""), "1"),
        "has_paralysis_0": onehot_equals(str(ppc.get("has_paralysis") or ""), "0"),
        "has_paralysis_1": onehot_equals(str(ppc.get("has_paralysis") or ""), "1"),
        "has_kannsetsu_0": onehot_equals(str(ppc.get("has_kannsetsu") or ""), "0"),
        "has_kannsetsu_1": onehot_equals(str(ppc.get("has_kannsetsu") or ""), "1"),
        "wound_total_score": to_int_or_none(design.get("wound_total_score")),
        "pain_image_front": normalize_text(ppc.get("pain_image_front")),
        "pain_image_back": normalize_text(ppc.get("pain_image_back")),
        "mahi_image_front": normalize_text(ppc.get("mahi_image_front")),
        "mahi_image_back": normalize_text(ppc.get("mahi_image_back")),
        "kan_image_front": normalize_text(ppc.get("kan_image_front")),
        "kan_image_back": normalize_text(ppc.get("kan_image_back")),
        "jokusou_image_front": normalize_text(design.get("jokusou_image_front")),
        "jokusou_image_back": normalize_text(design.get("jokusou_image_back")),
    }
    for n in ["d0","d1","d2","d3","d4","d5","dti","du"]: out[f"wound_depth_{n}"] = onehot_equals(str(design.get("wound_depth") or ""), n)
    for n in ["e0","e1","e3","e6"]: out[f"wound_exudate_{n}"] = onehot_equals(str(design.get("wound_exudate") or ""), n)
    for n in ["s0","s3","s6","s8","s9","s12","s15"]: out[f"wound_size_{n}"] = onehot_equals(str(design.get("wound_size") or ""), n)
    for n in ["i0","i1","i3c","i3","i9"]: out[f"wound_infection_{n}"] = onehot_equals(str(design.get("wound_infection") or ""), n)
    for n in ["g0","g1","g3","g4","g5","g6"]: out[f"wound_granulation_{n}"] = onehot_equals(str(design.get("wound_redness_area") or ""), n)
    for n in ["n0","n3","n6"]: out[f"wound_necrosis_{n}"] = onehot_equals(str(design.get("wound_necrosis") or ""), n)
    for n in ["p0","p6","p6_4to16","p12","p24"]: out[f"wound_pocket_{n}"] = onehot_equals(str(design.get("wound_pocket") or ""), n)
    return out


def ensure_form17_columns(conn: sqlite3.Connection):
    columns = [
        ("med_image_1_filename", "TEXT"),
        ("med_image_2_filename", "TEXT"),
        ("med_image_3_filename", "TEXT"),
        ("med_image_4_filename", "TEXT"),
        ("med_image_5_filename", "TEXT"),
        ("med_image_6_filename", "TEXT"),
        ("med_image_7_filename", "TEXT"),
        ("med_image_8_filename", "TEXT"),
        ("med_image_9_filename", "TEXT"),
        ("med_image_10_filename", "TEXT"),
        ("med_image_11_filename", "TEXT"),
        ("med_image_12_filename", "TEXT"),
        ("med_image_13_filename", "TEXT"),
        ("med_image_14_filename", "TEXT"),
        ("med_image_15_filename", "TEXT"),
        ("med_image_16_filename", "TEXT"),
        ("med_image_17_filename", "TEXT"),
        ("med_image_18_filename", "TEXT"),
        ("med_image_19_filename", "TEXT"),
        ("med_image_20_filename", "TEXT"),
        ("med_image_21_filename", "TEXT"),
        ("med_image_22_filename", "TEXT"),
        ("med_image_23_filename", "TEXT"),
        ("med_image_24_filename", "TEXT"),
        ("med_have_1", "INTEGER"),
        ("med_have_2", "INTEGER"),
        ("med_have_3", "INTEGER"),
        ("med_have_4", "INTEGER"),
        ("med_have_5", "INTEGER"),
        ("med_have_6", "INTEGER"),
        ("med_have_7", "INTEGER"),
        ("med_have_8", "INTEGER"),
        ("med_have_9", "INTEGER"),
        ("med_have_10", "INTEGER"),
        ("med_have_11", "INTEGER"),
        ("med_have_12", "INTEGER"),
        ("med_have_13", "INTEGER"),
        ("med_have_14", "INTEGER"),
        ("med_have_15", "INTEGER"),
        ("med_have_16", "INTEGER"),
        ("med_have_17", "INTEGER"),
        ("med_have_18", "INTEGER"),
        ("med_have_19", "INTEGER"),
        ("med_have_20", "INTEGER"),
        ("med_have_21", "INTEGER"),
        ("med_have_22", "INTEGER"),
        ("med_have_23", "INTEGER"),
        ("med_have_24", "INTEGER"),
        ("med_photo_single", "TEXT"),
        ("med_photo_1", "TEXT"),
        ("med_photo_2", "TEXT"),
        ("med_photo_3", "TEXT"),
        ("side_effect_0", "INTEGER"),
        ("side_effect_1", "INTEGER"),
        ("side_effect_detail", "TEXT"),
        ("medicine_usage_0", "INTEGER"),
        ("medicine_usage_0a", "INTEGER"),
        ("medicine_usage_1", "INTEGER"),
        ("medicine_detail_a", "INTEGER"),
        ("medicine_detail_b", "INTEGER"),
        ("medicine_detail_c", "INTEGER"),
        ("medicine_detail_d", "INTEGER"),
        ("medicine_detail_e", "INTEGER"),
        ("medicine_detail_f", "INTEGER"),
        ("medicine_detail_g", "INTEGER"),
        ("medicine_detail_h", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page17_to_form17_columns(page17: dict) -> dict:
    mu = (page17.get("medicationUsage") or page17 or {}) or {}
    rows = mu.get("medicine_categories")
    if not isinstance(rows, list):
        rows = []
    medicine_detail = mu.get("medicine_detail")
    if not isinstance(medicine_detail, list):
        medicine_detail = [] if medicine_detail in (None, "", []) else [medicine_detail]

    out = {
        "med_photo_single": None,
        "med_photo_1": normalize_text(mu.get("med_photo_1")),
        "med_photo_2": normalize_text(mu.get("med_photo_2")),
        "med_photo_3": normalize_text(mu.get("med_photo_3")),
        "side_effect_0": onehot_equals(str(mu.get("side_effect") or ""), "なし"),
        "side_effect_1": onehot_equals(str(mu.get("side_effect") or ""), "あり"),
        "side_effect_detail": normalize_text(mu.get("side_effect_detail")),
        "medicine_usage_0": onehot_equals(str(mu.get("medicine_usage") or ""), "0"),
        "medicine_usage_0a": onehot_equals(str(mu.get("medicine_usage") or ""), "0a"),
        "medicine_usage_1": onehot_equals(str(mu.get("medicine_usage") or ""), "1"),
    }

    for i in range(1, 25):
        row = rows[i - 1] if i - 1 < len(rows) and isinstance(rows[i - 1], dict) else {}
        direct_filename = normalize_text(mu.get(f"med_image_{i}_filename"))
        nested_filename = normalize_text(row.get("image_filename"))
        out[f"med_image_{i}_filename"] = direct_filename or nested_filename
        out[f"med_have_{i}"] = 1 if str(row.get("has_medicine") or "") == "1" else 0

    for ch in "abcdefgh":
        out[f"medicine_detail_{ch}"] = onehot_in(medicine_detail, ch)

    return out


def ensure_form18_columns(conn: sqlite3.Connection):
    columns = [
        ("induction_consultation_0", "INTEGER"),
        ("induction_consultation_1", "INTEGER"),
        ("induction_detail_discussion", "TEXT"),
        ("induction_detail_support", "TEXT"),
        ("induction_detail_values", "TEXT"),
        ("emergency_transport_wish_a", "INTEGER"),
        ("emergency_transport_wish_b", "INTEGER"),
        ("emergency_transport_wish_c", "INTEGER"),
        ("emergency_transport_wish_d", "INTEGER"),
        ("emergency_transport_wish_e", "INTEGER"),
        ("emergency_transport_wish_f", "INTEGER"),
        ("treatment_respirator_0", "INTEGER"),
        ("treatment_respirator_1", "INTEGER"),
        ("treatment_central_venous_nutrition_0", "INTEGER"),
        ("treatment_central_venous_nutrition_1", "INTEGER"),
        ("treatment_infusion_hydration_0", "INTEGER"),
        ("treatment_infusion_hydration_1", "INTEGER"),
        ("treatment_chemotherapy_0", "INTEGER"),
        ("treatment_chemotherapy_1", "INTEGER"),
        ("treatment_tube_feeding_0", "INTEGER"),
        ("treatment_tube_feeding_1", "INTEGER"),
        ("treatment_drug_therapy_0", "INTEGER"),
        ("treatment_drug_therapy_1", "INTEGER"),
        ("treatment_dialysis_0", "INTEGER"),
        ("treatment_dialysis_1", "INTEGER"),
        ("treatment_blood_transfusion_0", "INTEGER"),
        ("treatment_blood_transfusion_1", "INTEGER"),
        ("treatment_cardiac_massage_0", "INTEGER"),
        ("treatment_cardiac_massage_1", "INTEGER"),
        ("treatment_other_detail", "TEXT"),
        ("life_prolongation_no_prolongation", "INTEGER"),
        ("life_prolongation_palliative_care", "INTEGER"),
        ("life_prolongation_withdraw_life_support", "INTEGER"),
        ("acceptance_individual_0", "INTEGER"),
        ("acceptance_individual_1", "INTEGER"),
        ("acceptance_family_0", "INTEGER"),
        ("acceptance_family_1", "INTEGER"),
        ("physical_activity_2", "INTEGER"),
        ("physical_activity_3", "INTEGER"),
        ("physical_activity_4", "INTEGER"),
        ("physical_activity_5", "INTEGER"),
        ("physical_activity_6", "INTEGER"),
        ("physical_activity_7", "INTEGER"),
        ("physical_activity_8", "INTEGER"),
        ("physical_activity_9", "INTEGER"),
        ("physical_activity_10", "INTEGER"),
        ("pain_0", "INTEGER"),
        ("pain_1", "INTEGER"),
        ("pain_2", "INTEGER"),
        ("pain_3", "INTEGER"),
        ("pain_4", "INTEGER"),
        ("pain_5", "INTEGER"),
        ("pain_6", "INTEGER"),
        ("pain_7", "INTEGER"),
        ("pain_8", "INTEGER"),
        ("pain_9", "INTEGER"),
        ("pain_10", "INTEGER"),
        ("numbness_0", "INTEGER"),
        ("numbness_1", "INTEGER"),
        ("numbness_2", "INTEGER"),
        ("numbness_3", "INTEGER"),
        ("numbness_4", "INTEGER"),
        ("numbness_5", "INTEGER"),
        ("numbness_6", "INTEGER"),
        ("numbness_7", "INTEGER"),
        ("numbness_8", "INTEGER"),
        ("numbness_9", "INTEGER"),
        ("numbness_10", "INTEGER"),
        ("drowsiness_0", "INTEGER"),
        ("drowsiness_1", "INTEGER"),
        ("drowsiness_2", "INTEGER"),
        ("drowsiness_3", "INTEGER"),
        ("drowsiness_4", "INTEGER"),
        ("drowsiness_5", "INTEGER"),
        ("drowsiness_6", "INTEGER"),
        ("drowsiness_7", "INTEGER"),
        ("drowsiness_8", "INTEGER"),
        ("drowsiness_9", "INTEGER"),
        ("drowsiness_10", "INTEGER"),
        ("fatigue_score_0", "INTEGER"),
        ("fatigue_score_1", "INTEGER"),
        ("fatigue_score_2", "INTEGER"),
        ("fatigue_score_3", "INTEGER"),
        ("fatigue_score_4", "INTEGER"),
        ("fatigue_score_5", "INTEGER"),
        ("fatigue_score_6", "INTEGER"),
        ("fatigue_score_7", "INTEGER"),
        ("fatigue_score_8", "INTEGER"),
        ("fatigue_score_9", "INTEGER"),
        ("fatigue_score_10", "INTEGER"),
        ("shortness_of_breath_0", "INTEGER"),
        ("shortness_of_breath_1", "INTEGER"),
        ("shortness_of_breath_2", "INTEGER"),
        ("shortness_of_breath_3", "INTEGER"),
        ("shortness_of_breath_4", "INTEGER"),
        ("shortness_of_breath_5", "INTEGER"),
        ("shortness_of_breath_6", "INTEGER"),
        ("shortness_of_breath_7", "INTEGER"),
        ("shortness_of_breath_8", "INTEGER"),
        ("shortness_of_breath_9", "INTEGER"),
        ("shortness_of_breath_10", "INTEGER"),
        ("loss_of_appetite_0", "INTEGER"),
        ("loss_of_appetite_1", "INTEGER"),
        ("loss_of_appetite_2", "INTEGER"),
        ("loss_of_appetite_3", "INTEGER"),
        ("loss_of_appetite_4", "INTEGER"),
        ("loss_of_appetite_5", "INTEGER"),
        ("loss_of_appetite_6", "INTEGER"),
        ("loss_of_appetite_7", "INTEGER"),
        ("loss_of_appetite_8", "INTEGER"),
        ("loss_of_appetite_9", "INTEGER"),
        ("loss_of_appetite_10", "INTEGER"),
        ("nausea_0", "INTEGER"),
        ("nausea_1", "INTEGER"),
        ("nausea_2", "INTEGER"),
        ("nausea_3", "INTEGER"),
        ("nausea_4", "INTEGER"),
        ("nausea_5", "INTEGER"),
        ("nausea_6", "INTEGER"),
        ("nausea_7", "INTEGER"),
        ("nausea_8", "INTEGER"),
        ("nausea_9", "INTEGER"),
        ("nausea_10", "INTEGER"),
        ("sleep_0", "INTEGER"),
        ("sleep_1", "INTEGER"),
        ("sleep_2", "INTEGER"),
        ("sleep_3", "INTEGER"),
        ("sleep_4", "INTEGER"),
        ("sleep_5", "INTEGER"),
        ("sleep_6", "INTEGER"),
        ("sleep_7", "INTEGER"),
        ("sleep_8", "INTEGER"),
        ("sleep_9", "INTEGER"),
        ("sleep_10", "INTEGER"),
        ("emotional_distress_0", "INTEGER"),
        ("emotional_distress_1", "INTEGER"),
        ("emotional_distress_2", "INTEGER"),
        ("emotional_distress_3", "INTEGER"),
        ("emotional_distress_4", "INTEGER"),
        ("emotional_distress_5", "INTEGER"),
        ("emotional_distress_6", "INTEGER"),
        ("emotional_distress_7", "INTEGER"),
        ("emotional_distress_8", "INTEGER"),
        ("emotional_distress_9", "INTEGER"),
        ("emotional_distress_10", "INTEGER"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page18_to_form18_columns(page18: dict) -> dict:
    intro = (page18.get("eolIntro") or page18 or {}) or {}
    symptom = (page18.get("symptomAssessment") or page18 or {}) or {}
    transport = (page18.get("transportWish") or page18 or {}) or {}
    treat = (page18.get("treatmentAgreement") or page18 or {}) or {}
    prolong = (page18.get("lifeProlongation") or page18 or {}) or {}
    accept = (page18.get("acceptance") or page18 or {}) or {}

    life = prolong.get("life_prolongation")
    if not isinstance(life, list):
        life = [] if life in (None, "", []) else [life]

    wish = str(transport.get("emergency_transport_wish") or "")

    out = {
        "induction_consultation_0": onehot_equals(str(intro.get("induction_consultation") or ""), "0"),
        "induction_consultation_1": onehot_equals(str(intro.get("induction_consultation") or ""), "1"),
        "induction_detail_discussion": normalize_text(intro.get("induction_detail_discussion")),
        "induction_detail_support": normalize_text(intro.get("induction_detail_support")),
        "induction_detail_values": normalize_text(intro.get("induction_detail_values")),
        "treatment_other_detail": normalize_text(treat.get("treatment_other_detail")),
        "life_prolongation_no_prolongation": onehot_in(life, "no_prolongation"),
        "life_prolongation_palliative_care": onehot_in(life, "palliative_care"),
        "life_prolongation_withdraw_life_support": onehot_in(life, "withdraw_life_support"),
        "acceptance_individual_0": onehot_equals(str(accept.get("acceptance_individual") or ""), "0"),
        "acceptance_individual_1": onehot_equals(str(accept.get("acceptance_individual") or ""), "1"),
        "acceptance_family_0": onehot_equals(str(accept.get("acceptance_family") or ""), "0"),
        "acceptance_family_1": onehot_equals(str(accept.get("acceptance_family") or ""), "1"),
    }

    for ch in "abcdef":
        out[f"emergency_transport_wish_{ch}"] = onehot_equals(wish, f"emergency_transport_wish_{ch}")

    for n in [
        "treatment_respirator","treatment_central_venous_nutrition","treatment_infusion_hydration","treatment_chemotherapy",
        "treatment_tube_feeding","treatment_drug_therapy","treatment_dialysis","treatment_blood_transfusion","treatment_cardiac_massage"
    ]:
        v = str(treat.get(n) or "")
        out[f"{n}_0"] = onehot_equals(v, "0")
        out[f"{n}_1"] = onehot_equals(v, "1")

    body = str(symptom.get("body_activity") or "")
    for i in range(2,11):
        out[f"physical_activity_{i}"] = onehot_equals(body, str(i))

    for prefix, key in [
        ("pain","pain"),("numbness","numbness"),("drowsiness","drowsiness"),("fatigue_score","fatigue_score"),
        ("shortness_of_breath","shortness_of_breath"),("loss_of_appetite","loss_of_appetite"),("nausea","nausea"),
        ("sleep","sleep"),("emotional_distress","emotional_distress")
    ]:
        v = str(symptom.get(key) or "")
        for i in range(0,11):
            out[f"{prefix}_{i}"] = onehot_equals(v, str(i))

    return out


def ensure_form19_columns(conn: sqlite3.Connection):
    columns = [
        ("fall_0", "INTEGER"),
        ("fall_1", "INTEGER"),
        ("fall_count", "INTEGER"),
        ("fall_detail", "TEXT"),
        ("fall_anxiety_0", "INTEGER"),
        ("fall_anxiety_1", "INTEGER"),
        ("fall_anxiety_2", "INTEGER"),
        ("anxiety_reason_aging_muscle", "INTEGER"),
        ("anxiety_reason_disease", "INTEGER"),
        ("anxiety_reason_medicine", "INTEGER"),
        ("anxiety_reason_internal_other", "INTEGER"),
        ("internal_other_text", "TEXT"),
        ("anxiety_reason_environment_external", "INTEGER"),
        ("fracture_0", "INTEGER"),
        ("fracture_1", "INTEGER"),
        ("fracture_cause_fall", "INTEGER"),
        ("fracture_cause_other", "INTEGER"),
        ("fracture_count", "INTEGER"),
        ("fracture_location", "TEXT"),
        ("height_decrease", "REAL"),
        ("back_curved", "INTEGER"),
        ("back_pain", "INTEGER"),
        ("drug_abuse_0", "INTEGER"),
        ("drug_abuse_1", "INTEGER"),
        ("drug_abuse_type_a", "INTEGER"),
        ("drug_abuse_type_b", "INTEGER"),
        ("drug_abuse_type_c", "INTEGER"),
        ("choking_risk_0", "INTEGER"),
        ("choking_risk_1", "INTEGER"),
        ("choking_detail_type_a", "INTEGER"),
        ("choking_detail_type_b", "INTEGER"),
        ("choking_detail_type_c", "INTEGER"),
        ("abuse_evaluation_0", "INTEGER"),
        ("abuse_evaluation_1", "INTEGER"),
        ("abuse_detail_type_a", "INTEGER"),
        ("abuse_detail_type_b", "INTEGER"),
        ("abuse_detail_type_c", "INTEGER"),
        ("kodokushi_feeling_0", "INTEGER"),
        ("kodokushi_feeling_1", "INTEGER"),
        ("kodokushi_feeling_2", "INTEGER"),
        ("kodokushi_feeling_3", "INTEGER"),
        ("fire_water_negligence_0", "INTEGER"),
        ("fire_water_negligence_1", "INTEGER"),
        ("fire_water_detail_type_a", "INTEGER"),
        ("fire_water_detail_type_b", "INTEGER"),
        ("fire_water_detail_type_c", "INTEGER"),
        ("news_risk_0", "INTEGER"),
        ("news_risk_1", "INTEGER"),
        ("news_risk_2", "INTEGER"),
        ("dehydration_prevention_0", "INTEGER"),
        ("dehydration_prevention_1", "INTEGER"),
        ("dehydration_detail_type_a", "INTEGER"),
        ("dehydration_detail_type_b", "INTEGER"),
        ("dehydration_detail_type_c", "INTEGER"),
        ("abnormal_behavior_severity_0", "INTEGER"),
        ("abnormal_behavior_severity_1", "INTEGER"),
        ("abnormal_behavior_severity_2", "INTEGER"),
        ("abnormal_behavior_severity_3", "INTEGER"),
        ("abnormal_behavior_detail_type_a", "INTEGER"),
        ("abnormal_behavior_detail_type_b", "INTEGER"),
        ("abnormal_behavior_detail_type_c", "INTEGER"),
        ("fracture_count_check", "INTEGER"),
        ("height_decrease_check", "INTEGER"),
        ("nurse_name", "TEXT"),
    ]
    for column_name, column_type in columns:
        ensure_column_exists(conn, "form0_legacy", column_name, column_type)


def map_page19_to_form19_columns(page19: dict, page0: dict) -> dict:
    rm = (page19.get("riskManagement") or page19 or {}) or {}
    fr = (rm.get("fallRisk") or page19 or {}) or {}
    fx = (rm.get("fractureRisk") or page19 or {}) or {}
    da = (rm.get("drugAbuse") or page19 or {}) or {}
    ts = (rm.get("temperatureSkinRisk") or page19 or {}) or {}
    ao = (rm.get("abuseOverall") or page19 or {}) or {}
    fw = (rm.get("fireWater") or page19 or {}) or {}

    anxiety_reason = fr.get("anxiety_reason")
    if not isinstance(anxiety_reason, list):
        anxiety_reason = [] if anxiety_reason in (None, "", []) else [anxiety_reason]
    fracture_signs = fx.get("fracture_related_signs")
    if not isinstance(fracture_signs, list):
        fracture_signs = [] if fracture_signs in (None, "", []) else [fracture_signs]

    nurse_name_val = normalize_text(get_by_path(page0, "receptionInfo.staff") or page0.get("reception_staff"))

    height_val = None
    hv = str(fx.get("height_decrease") or "").strip()
    if hv != "":
        try:
            height_val = float(hv)
        except ValueError:
            height_val = None

    out = {
        "fall_0": onehot_equals(str(fr.get("fall") or ""), "0"),
        "fall_1": onehot_equals(str(fr.get("fall") or ""), "1"),
        "fall_count": to_int_or_none(fr.get("fall_count")),
        "fall_detail": normalize_text(fr.get("fall_detail")),
        "anxiety_reason_aging_muscle": onehot_in(anxiety_reason, "aging_muscle"),
        "anxiety_reason_disease": onehot_in(anxiety_reason, "disease"),
        "anxiety_reason_medicine": onehot_in(anxiety_reason, "medicine"),
        "anxiety_reason_internal_other": onehot_in(anxiety_reason, "internal_other"),
        "internal_other_text": normalize_text(fr.get("internal_other_text")),
        "anxiety_reason_environment_external": onehot_in(anxiety_reason, "environment_external"),
        "fracture_0": onehot_equals(str(fx.get("fracture") or ""), "0"),
        "fracture_1": onehot_equals(str(fx.get("fracture") or ""), "1"),
        "fracture_cause_fall": onehot_equals(str(fx.get("fracture_cause") or ""), "fall"),
        "fracture_cause_other": onehot_equals(str(fx.get("fracture_cause") or ""), "other"),
        "fracture_count": to_int_or_none(fx.get("fracture_count")),
        "fracture_location": normalize_text(fx.get("fracture_location")),
        "height_decrease": height_val,
        "back_curved": onehot_in(fracture_signs, "back_curved"),
        "back_pain": onehot_in(fracture_signs, "back_pain"),
        "drug_abuse_0": onehot_equals(str(da.get("drug_abuse") or ""), "0"),
        "drug_abuse_1": onehot_equals(str(da.get("drug_abuse") or ""), "1"),
        "choking_risk_0": onehot_equals(str(ts.get("choking_risk") or ""), "0"),
        "choking_risk_1": onehot_equals(str(ts.get("choking_risk") or ""), "1"),
        "abuse_evaluation_0": onehot_equals(str(ao.get("abuse_evaluation") or ""), "0"),
        "abuse_evaluation_1": onehot_equals(str(ao.get("abuse_evaluation") or ""), "1"),
        "fire_water_negligence_0": onehot_equals(str(fw.get("fire_water_negligence") or ""), "0"),
        "fire_water_negligence_1": onehot_equals(str(fw.get("fire_water_negligence") or ""), "1"),
        "dehydration_prevention_0": onehot_equals(str(rm.get("dehydration_prevention") or ""), "0"),
        "dehydration_prevention_1": onehot_equals(str(rm.get("dehydration_prevention") or ""), "1"),
        "fracture_count_check": onehot_equals(str(fx.get("fracture_count_check") or ""), "1"),
        "height_decrease_check": onehot_equals(str(fx.get("height_decrease_check") or ""), "1"),
        "nurse_name": nurse_name_val,
    }

    for i in range(3):
        out[f"fall_anxiety_{i}"] = onehot_equals(str(fr.get("fall_anxiety") or ""), str(i))
    for ch in "abc":
        out[f"drug_abuse_type_{ch}"] = onehot_equals(str(da.get("drug_abuse_type") or ""), ch)
        out[f"choking_detail_type_{ch}"] = onehot_equals(str(ts.get("choking_detail_type") or ""), ch)
        out[f"abuse_detail_type_{ch}"] = onehot_equals(str(ao.get("abuse_detail_type") or ""), ch)
        out[f"fire_water_detail_type_{ch}"] = onehot_equals(str(fw.get("fire_water_detail_type") or ""), ch)
        out[f"dehydration_detail_type_{ch}"] = onehot_equals(str(rm.get("dehydration_detail_type") or ""), ch)
        out[f"abnormal_behavior_detail_type_{ch}"] = onehot_equals(str(rm.get("abnormal_behavior_detail_type") or ""), ch)
    for i in range(4):
        out[f"kodokushi_feeling_{i}"] = onehot_equals(str(rm.get("kodokushi_feeling") or ""), str(i))
        out[f"abnormal_behavior_severity_{i}"] = onehot_equals(str(rm.get("abnormal_behavior_severity") or ""), str(i))
    for i in range(3):
        out[f"news_risk_{i}"] = onehot_equals(str(rm.get("news_risk") or ""), str(i))

    return out


def ensure_form1_columns(conn: sqlite3.Connection):
    columns = [
        ("housing_type_home", "INTEGER"), ("housing_type_apartment", "INTEGER"), ("housing_type_mansion", "INTEGER"),
        ("housing_type_senior_mansion", "INTEGER"), ("housing_type_group_home", "INTEGER"), ("housing_type_rented", "INTEGER"),
        ("housing_type_welfare", "INTEGER"), ("housing_type_rehab", "INTEGER"), ("housing_type_employment_facility", "INTEGER"),
        ("housing_type_other_flag", "INTEGER"), ("housing_type_other", "TEXT"), ("insurer_name", "TEXT"),
        ("user_burden_ratio_1割", "INTEGER"), ("user_burden_ratio_2割", "INTEGER"), ("user_burden_ratio_3割", "INTEGER"),
        ("certification_year", "INTEGER"), ("certification_month", "INTEGER"), ("certification_day", "INTEGER"),
        ("valid_start_year", "INTEGER"), ("valid_start_month", "INTEGER"), ("valid_start_day", "INTEGER"),
        ("valid_end_year", "INTEGER"), ("valid_end_month", "INTEGER"), ("valid_end_day", "INTEGER"),
        ("care_status_要支援1", "INTEGER"), ("care_status_要支援2", "INTEGER"),
        ("care_status_nursing_要介護1", "INTEGER"), ("care_status_nursing_要介護2", "INTEGER"), ("care_status_nursing_要介護3", "INTEGER"), ("care_status_nursing_要介護4", "INTEGER"), ("care_status_nursing_要介護5", "INTEGER"),
        ("benefit_limit", "INTEGER"), ("dementia_level_自立", "INTEGER"), ("dementia_level_Ⅰ", "INTEGER"),
        ("dementia_level_Ⅱa", "INTEGER"), ("dementia_level_Ⅱb", "INTEGER"), ("dementia_level_Ⅲa", "INTEGER"),
        ("dementia_level_Ⅲb", "INTEGER"), ("dementia_level_Ⅳ", "INTEGER"), ("dementia_level_M", "INTEGER"),
        ("elderly_independence_level_自立", "INTEGER"), ("elderly_independence_level_J1", "INTEGER"), ("elderly_independence_level_J2", "INTEGER"),
        ("elderly_independence_level_A1", "INTEGER"), ("elderly_independence_level_A2", "INTEGER"), ("elderly_independence_level_B1", "INTEGER"),
        ("elderly_independence_level_B2", "INTEGER"), ("elderly_independence_level_C1", "INTEGER"), ("elderly_independence_level_C2", "INTEGER"),
        ("insurer_name_medical", "TEXT"), ("insurance_type_self", "INTEGER"), ("insurance_type_family", "INTEGER"),
        ("insurance_category_national", "INTEGER"), ("insurance_category_social", "INTEGER"), ("insurance_category_mutual", "INTEGER"),
        ("insurance_category_labor", "INTEGER"), ("insurance_category_elderly", "INTEGER"),
        ("kouki_kourei_burden_1割", "INTEGER"), ("kouki_kourei_burden_2割", "INTEGER"), ("kouki_kourei_burden_3割", "INTEGER"),
        ("insurance_category_other_flag", "INTEGER"), ("insurance_other_detail", "TEXT"),
        ("my_number_card_yes", "INTEGER"), ("my_number_card_no", "INTEGER"), ("doctor_opinion", "TEXT"),
        ("support_type_1_keyperson", "INTEGER"), ("support_type_1_maincaregiver", "INTEGER"),
        ("living_status_1_samehouse", "INTEGER"), ("living_status_1_dayabsent", "INTEGER"), ("living_status_1_separate", "INTEGER"),
        ("care_burden_1_working", "INTEGER"), ("care_burden_1_studying", "INTEGER"), ("care_burden_1_elderly", "INTEGER"),
        ("care_burden_1_disabled", "INTEGER"), ("care_burden_1_pregnant", "INTEGER"),
        ("support_type_2_keyperson", "INTEGER"), ("support_type_2_maincaregiver", "INTEGER"),
        ("living_status_2_samehouse", "INTEGER"), ("living_status_2_dayabsent", "INTEGER"), ("living_status_2_separate", "INTEGER"),
        ("care_burden_2_working", "INTEGER"), ("care_burden_2_studying", "INTEGER"), ("care_burden_2_elderly", "INTEGER"),
        ("care_burden_2_disabled", "INTEGER"), ("care_burden_2_pregnant", "INTEGER"),
        ("care_sharing_3", "TEXT"), ("living_status_3_samehouse", "INTEGER"), ("living_status_3_dayabsent", "INTEGER"),
        ("living_status_3_separate", "INTEGER"), ("care_burden_3_working", "INTEGER"), ("care_burden_3_studying", "INTEGER"),
        ("care_burden_3_elderly", "INTEGER"), ("care_burden_3_disabled", "INTEGER"), ("care_burden_3_pregnant", "INTEGER"),
        ("care_sharing_4", "TEXT"), ("living_status_4_samehouse", "INTEGER"), ("living_status_4_dayabsent", "INTEGER"),
        ("living_status_4_separate", "INTEGER"), ("care_burden_4_working", "INTEGER"), ("care_burden_4_studying", "INTEGER"),
        ("care_burden_4_elderly", "INTEGER"), ("care_burden_4_disabled", "INTEGER"), ("care_burden_4_pregnant", "INTEGER"),
        ("genogramCanvas_image", "TEXT"), ("user_requests", "TEXT"), ("family_requests", "TEXT"),
    ]
    for c, ty in columns:
        ensure_column_exists(conn, "form0_legacy", c, ty)


def ensure_form2_columns(conn: sqlite3.Connection):
    columns = [
        ("activity_daily", "TEXT"), ("expensive_cost_usage_0", "INTEGER"), ("expensive_cost_usage_1a", "INTEGER"), ("expensive_cost_usage_1b", "INTEGER"),
        ("expensive_cost_usage_2a", "INTEGER"), ("expensive_cost_usage_2b", "INTEGER"), ("expensive_cost_no_reason", "TEXT"), ("expensive_cost_reason", "TEXT"),
        ("public_medical_usage_0", "INTEGER"), ("public_medical_usage_1", "INTEGER"), ("public_medical_usage_2", "INTEGER"),
        ("public_medical_detail1a", "INTEGER"), ("public_medical_detail1b", "INTEGER"), ("public_medical_detail1c", "INTEGER"), ("public_medical_detail1d", "INTEGER"),
        ("public_medical_detail2a", "INTEGER"), ("public_medical_detail2b", "INTEGER"), ("public_medical_detail2c", "INTEGER"),
        ("public_medical_detail3", "INTEGER"), ("public_medical_detail4", "INTEGER"), ("public_medical_detail5", "INTEGER"),
        ("public_medical_detail1d_reason", "TEXT"), ("public_medical_detail2c_reason", "TEXT"), ("public_medical_detail5_reason", "TEXT"),
        ("public_medical_detail_disease", "TEXT"), ("public_medical_usage_2_reason", "TEXT"),
        ("public_system_use_detail0", "INTEGER"), ("public_system_use_detail1", "INTEGER"), ("public_system_use_detail2", "INTEGER"),
        ("public_system_detail_1_1", "INTEGER"), ("public_system_detail_1_2", "TEXT"), ("public_system_detail_1_3", "INTEGER"),
        ("public_system_detail_1_4", "INTEGER"), ("public_system_detail_1_5", "INTEGER"), ("public_system_detail_1_6", "TEXT"),
        ("option_detail_1", "TEXT"), ("option_detail_2", "TEXT"), ("option_detail_3", "TEXT"),
        ("public_system_usage_detail_shintai_shu", "TEXT"), ("public_system_usage_detail_shintai_kyu", "TEXT"), ("public_system_shinshotecho_grade", "TEXT"),
        ("public_system2_reason", "TEXT"),
        ("economic_status_1_1", "INTEGER"), ("economic_status_1_2", "INTEGER"), ("economic_status_1_3", "INTEGER"), ("economic_status_1_4", "INTEGER"), ("economic_status_1_5", "INTEGER"),
        ("economic_status_2_1", "INTEGER"), ("economic_status_2_2", "INTEGER"), ("economic_status_2_3", "INTEGER"), ("economic_status_2_4", "INTEGER"), ("economic_status_2_5", "INTEGER"),
        ("economic_status_3_food", "INTEGER"), ("economic_status_3_medical", "INTEGER"), ("economic_status_3_care", "INTEGER"), ("economic_status_3_transport", "INTEGER"),
        ("economic_status_3_housing", "INTEGER"), ("economic_status_3_utilities", "INTEGER"), ("economic_status_3_leisure", "INTEGER"),
        ("economic_status_3_other_flag", "INTEGER"), ("economic_status_3_difficulties_other", "TEXT"),
    ]
    for c, ty in columns:
        ensure_column_exists(conn, "form0_legacy", c, ty)


def map_page2_to_form2_columns(page2: dict) -> dict:
    daily = (page2.get("dailyRhythm") or page2 or {}) or {}
    pea = (page2.get("publicAndEconomic") or page2 or {}) or {}
    ec = (pea.get("expensiveCost") or page2 or {}) or {}
    ec_u = str(ec.get("usage") or page2.get("expensive_cost_usage") or "")
    no_reason = ec.get("noReason") or page2.get("expensive_cost_no_reason") or page2.get("expensive_cost_reason") or ""
    pm = (pea.get("publicMedical") or page2 or {}) or {}
    pm_u = str(pm.get("usage") or page2.get("public_medical_usage") or "")
    pmd = (pm.get("detail") or page2 or {}) or {}
    cat1 = pmd.get("category1")
    if not isinstance(cat1, list): cat1 = [] if cat1 in (None, "", []) else [cat1]
    cat2 = pmd.get("category2")
    if not isinstance(cat2, list): cat2 = [] if cat2 in (None, "", []) else [cat2]
    c35 = pmd.get("category3to5")
    if not isinstance(c35, list): c35 = [] if c35 in (None, "", []) else [c35]
    def _on(v) -> bool:
        return str(v or "").strip().lower() not in {"", "0", "false", "none", "null"}
    if not cat1:
        if _on(page2.get("public_medical_1a")): cat1.append("a")
        if _on(page2.get("public_medical_1b")): cat1.append("b")
        if _on(page2.get("public_medical_1c")): cat1.append("c")
        if _on(page2.get("public_medical_1d")): cat1.append("d")
    if not cat2:
        if _on(page2.get("public_medical_2a")): cat2.append("a")
        if _on(page2.get("public_medical_2b")): cat2.append("b")
        if _on(page2.get("public_medical_2c")): cat2.append("c")
    if not c35:
        if _on(page2.get("public_medical_3")): c35.append("3")
        if _on(page2.get("public_medical_4")): c35.append("4")
        if _on(page2.get("public_medical_5")): c35.append("5")
    ps = (pea.get("publicSystem") or page2 or {}) or {}
    ps_u = str(ps.get("usage") or page2.get("public_system_usage") or "")
    psd = (ps.get("detail") or page2 or {}) or {}
    nb = (psd.get("mentalHealthNotebook") or page2 or {}) or {}
    dn = (psd.get("disabilityNotebook") or page2 or {}) or {}
    rn = (psd.get("rehabilitationNotebook") or page2 or {}) or {}
    others = psd.get("others")
    if not isinstance(others, list): others = [] if others in (None, "", []) else [others]
    if not others:
        if _on(page2.get("public_system_4")): others.append("4")
        if _on(page2.get("public_system_5")): others.append("5")
        if _on(page2.get("public_system_6")): others.append("6")
    n_use = normalize_text(ps.get("noUseReason") or page2.get("public_system_no_reason"))
    es = (pea.get("economicStatus") or page2 or {}) or {}
    hd = str(es.get("householdDifficulty") or page2.get("economic_status_1") or "")
    bd = str(es.get("beforePaydayDifficulty") or page2.get("economic_status_2") or "")
    hi = es.get("hardshipItems")
    if not isinstance(hi, list):
        hi = page2.get("economic_status_3")
    if not isinstance(hi, list): hi = [] if hi in (None, "", []) else [hi]
    dname = normalize_text(pmd.get("diseaseName") or page2.get("public_medical_5_reason"))
    return {
        "activity_daily": normalize_text(daily.get("activityDaily") or page2.get("activity_daily")),
        "expensive_cost_usage_0": onehot_equals(ec_u, "0"), "expensive_cost_usage_1a": onehot_equals(ec_u, "1a"),
        "expensive_cost_usage_1b": onehot_equals(ec_u, "1b"), "expensive_cost_usage_2a": onehot_equals(ec_u, "2a"),
        "expensive_cost_usage_2b": onehot_equals(ec_u, "2b"),
        "expensive_cost_no_reason": normalize_text(no_reason) if ec_u == "2a" else None,
        "expensive_cost_reason": normalize_text(no_reason) if ec_u == "2b" else None,
        "public_medical_usage_0": onehot_equals(pm_u, "0"), "public_medical_usage_1": onehot_equals(pm_u, "1"), "public_medical_usage_2": onehot_equals(pm_u, "2"),
        "public_medical_detail1a": onehot_in(cat1, "a"), "public_medical_detail1b": onehot_in(cat1, "b"), "public_medical_detail1c": onehot_in(cat1, "c"), "public_medical_detail1d": onehot_in(cat1, "d"),
        "public_medical_detail2a": onehot_in(cat2, "a"), "public_medical_detail2b": onehot_in(cat2, "b"), "public_medical_detail2c": onehot_in(cat2, "c"),
        "public_medical_detail3": onehot_in(c35, "3"), "public_medical_detail4": onehot_in(c35, "4"), "public_medical_detail5": onehot_in(c35, "5"),
        "public_medical_detail1d_reason": normalize_text(pmd.get("category1OtherReason") or page2.get("public_medical_1d_reason")),
        "public_medical_detail2c_reason": normalize_text(pmd.get("category2OtherReason") or page2.get("public_medical_2c_reason")),
        "public_medical_detail5_reason": dname, "public_medical_detail_disease": dname,
        "public_medical_usage_2_reason": normalize_text(pm.get("reason") or page2.get("public_medical_reason")) if pm_u == "2" else None,
        "public_system_use_detail0": onehot_equals(ps_u, "0"), "public_system_use_detail1": onehot_equals(ps_u, "1"), "public_system_use_detail2": onehot_equals(ps_u, "2"),
        "public_system_detail_1_1": onehot_equals(str(nb.get("enabled") or page2.get("public_system_1")), "1"), "public_system_detail_1_2": normalize_text(nb.get("kyu") or page2.get("public_system_3_kyu")),
        "public_system_detail_1_3": onehot_in(others, "4"), "public_system_detail_1_4": onehot_in(others, "5"), "public_system_detail_1_5": onehot_in(others, "6"),
        "public_system_detail_1_6": n_use if ps_u == "2" else None,
        "option_detail_1": normalize_text(dn.get("shu") or page2.get("public_system_1_shu")),
        "option_detail_2": normalize_text(dn.get("kyu") or page2.get("public_system_1_kyu")),
        "option_detail_3": normalize_text(nb.get("kyu") or page2.get("public_system_3_kyu")),
        "public_system_usage_detail_shintai_shu": normalize_text(dn.get("shu") or page2.get("public_system_1_shu")),
        "public_system_usage_detail_shintai_kyu": normalize_text(dn.get("kyu") or page2.get("public_system_1_kyu")),
        "public_system_shinshotecho_grade": normalize_text(rn.get("degree") or page2.get("public_system_2_degree")),
        "public_system2_reason": n_use if ps_u == "2" else None,
        "economic_status_1_1": onehot_equals(hd, "0"), "economic_status_1_2": onehot_equals(hd, "1"), "economic_status_1_3": onehot_equals(hd, "2"), "economic_status_1_4": onehot_equals(hd, "3"), "economic_status_1_5": onehot_equals(hd, "4"),
        "economic_status_2_1": onehot_equals(bd, "0"), "economic_status_2_2": onehot_equals(bd, "1"), "economic_status_2_3": onehot_equals(bd, "2"), "economic_status_2_4": onehot_equals(bd, "3"), "economic_status_2_5": onehot_equals(bd, "4"),
        "economic_status_3_food": onehot_in(hi, "food"), "economic_status_3_medical": onehot_in(hi, "medical"), "economic_status_3_care": onehot_in(hi, "care"),
        "economic_status_3_transport": onehot_in(hi, "transport"), "economic_status_3_housing": onehot_in(hi, "housing"), "economic_status_3_utilities": onehot_in(hi, "utilities"),
        "economic_status_3_leisure": onehot_in(hi, "leisure"), "economic_status_3_other_flag": onehot_in(hi, "other_flag"),
        "economic_status_3_difficulties_other": normalize_text(es.get("hardshipOtherText") or page2.get("economic_status_3_other_text")),
    }


def ensure_form3_columns(conn: sqlite3.Connection):
    columns = [
        ("residence_type_house_1f", "INTEGER"), ("residence_type_house_2f", "INTEGER"), ("residence_type_apartment", "INTEGER"),
        ("apartment_floor", "INTEGER"), ("elevator_あり", "INTEGER"), ("elevator_不要", "INTEGER"),
        ("entrance_to_road_危険あり", "INTEGER"), ("entrance_to_road_問題なし", "INTEGER"),
        ("room_photo_image_1_filename", "TEXT"), ("room_photo_image_2_filename", "TEXT"), ("room_photo_image_3_filename", "TEXT"),
        ("room_safety", "TEXT"), ("room_cleanliness_0", "INTEGER"), ("room_cleanliness_1a", "INTEGER"), ("room_cleanliness_1b", "INTEGER"), ("room_cleanliness_2a", "INTEGER"),
        ("room_safety_level_0", "INTEGER"), ("room_safety_level_1", "INTEGER"), ("room_safety_level_2", "INTEGER"),
        ("reform_need_0", "INTEGER"), ("reform_need_1", "INTEGER"),
        ("reform_place_room", "INTEGER"), ("reform_place_bathroom", "INTEGER"), ("reform_place_datsuishitsu", "INTEGER"),
        ("reform_place_bathtub", "INTEGER"), ("reform_place_toilet", "INTEGER"), ("reform_place_benki", "INTEGER"),
        ("reform_place_hallway", "INTEGER"), ("reform_place_entrance", "INTEGER"), ("reform_place_garden", "INTEGER"),
        ("reform_place_stairs", "INTEGER"), ("reform_place_other", "INTEGER"),
        ("care_tool_need_0", "INTEGER"), ("care_tool_need_1", "INTEGER"), ("care_tool_type_move", "INTEGER"), ("care_tool_type_life", "INTEGER"), ("care_tool_type_assist", "INTEGER"),
        ("equipment_need_0", "INTEGER"), ("equipment_need_1", "INTEGER"),
        ("equipment_type_life_tool", "INTEGER"), ("equipment_type_electric", "INTEGER"), ("equipment_type_aircon", "INTEGER"), ("equipment_type_elevator", "INTEGER"),
        ("equipment_type_other_flag", "INTEGER"), ("equipment_type_other", "TEXT"),
        ("social_service_usage_0", "INTEGER"), ("social_service_usage_1", "INTEGER"), ("social_service_usage_2", "INTEGER"), ("social_service_usage_3", "INTEGER"),
        ("social_service_reason_text", "TEXT"),
    ]
    for c, ty in columns:
        ensure_column_exists(conn, "form0_legacy", c, ty)


def _room_photo_filename_from_page3(re_env: dict, slot_index: int):
    k = f"room_photo_image_{slot_index}_filename"
    v = normalize_text(re_env.get(k))
    if v is not None:
        return v
    slots = re_env.get("roomPhotos")
    if isinstance(slots, list) and 1 <= slot_index <= len(slots):
        el = slots[slot_index - 1]
        if isinstance(el, dict):
            return normalize_text(el.get("filename"))
    return None


def map_page3_to_form3_columns(page3: dict) -> dict:
    re_env = (page3.get("residentialEnvironment") or page3 or {}) or {}
    rtype = str(re_env.get("residenceType") or "")
    elev = str(re_env.get("elevator") or "")
    road = str(re_env.get("entranceToRoad") or "")
    clean = (page3.get("cleanAndSafety") or page3 or {}) or {}
    rc = str(clean.get("roomCleanliness") or "")
    rsl = str(clean.get("roomSafetyLevel") or "")
    rte = (page3.get("reformToolsEquipment") or page3 or {}) or {}
    ref = (rte.get("reform") or page3 or {}) or {}
    r_need = str(ref.get("need") or "")
    ref_pl = ref.get("places")
    if not isinstance(ref_pl, list): ref_pl = [] if ref_pl in (None, "", []) else [ref_pl]
    ct = (rte.get("careTool") or page3 or {}) or {}
    ct_n = str(ct.get("need") or "")
    ct_t = ct.get("types")
    if not isinstance(ct_t, list): ct_t = [] if ct_t in (None, "", []) else [ct_t]
    eq = (rte.get("equipment") or page3 or {}) or {}
    eq_n = str(eq.get("need") or "")
    eq_t = eq.get("types")
    if not isinstance(eq_t, list): eq_t = [] if eq_t in (None, "", []) else [eq_t]
    ssd = (page3.get("socialServiceDecision") or page3 or {}) or {}
    ssu = str(ssd.get("usage") or "")
    return {
        "residence_type_house_1f": onehot_equals(rtype, "house_1f"), "residence_type_house_2f": onehot_equals(rtype, "house_2f"), "residence_type_apartment": onehot_equals(rtype, "apartment"),
        "apartment_floor": to_int_or_none(re_env.get("apartmentFloor")), "elevator_あり": onehot_equals(elev, "あり"), "elevator_不要": onehot_equals(elev, "不要"),
        "entrance_to_road_危険あり": onehot_equals(road, "危険あり"), "entrance_to_road_問題なし": onehot_equals(road, "問題なし"),
        "room_photo_image_1_filename": _room_photo_filename_from_page3(re_env, 1), "room_photo_image_2_filename": _room_photo_filename_from_page3(re_env, 2), "room_photo_image_3_filename": _room_photo_filename_from_page3(re_env, 3),
        "room_safety": normalize_text(re_env.get("roomSafetyNote")),
        "room_cleanliness_0": onehot_equals(rc, "0"), "room_cleanliness_1a": onehot_equals(rc, "1a"), "room_cleanliness_1b": onehot_equals(rc, "1b"), "room_cleanliness_2a": onehot_equals(rc, "2a"),
        "room_safety_level_0": onehot_equals(rsl, "0"), "room_safety_level_1": onehot_equals(rsl, "1"), "room_safety_level_2": onehot_equals(rsl, "2"),
        "reform_need_0": onehot_equals(r_need, "0"), "reform_need_1": onehot_equals(r_need, "1"),
        "reform_place_room": onehot_in(ref_pl, "居室"), "reform_place_bathroom": onehot_in(ref_pl, "浴室"), "reform_place_datsuishitsu": onehot_in(ref_pl, "脱衣室"),
        "reform_place_bathtub": onehot_in(ref_pl, "浴槽"), "reform_place_toilet": onehot_in(ref_pl, "トイレ"), "reform_place_benki": onehot_in(ref_pl, "便器"),
        "reform_place_hallway": onehot_in(ref_pl, "廊下"), "reform_place_entrance": onehot_in(ref_pl, "玄関"), "reform_place_garden": onehot_in(ref_pl, "庭"), "reform_place_stairs": onehot_in(ref_pl, "階段"), "reform_place_other": onehot_in(ref_pl, "その他"),
        "care_tool_need_0": onehot_equals(ct_n, "0"), "care_tool_need_1": onehot_equals(ct_n, "1"),
        "care_tool_type_move": onehot_in(ct_t, "移動用具"), "care_tool_type_life": onehot_in(ct_t, "生活用具"), "care_tool_type_assist": onehot_in(ct_t, "介助用具"),
        "equipment_need_0": onehot_equals(eq_n, "0"), "equipment_need_1": onehot_equals(eq_n, "1"),
        "equipment_type_life_tool": onehot_in(eq_t, "障害者用生活用具"), "equipment_type_electric": onehot_in(eq_t, "電気"), "equipment_type_aircon": onehot_in(eq_t, "冷暖房機"), "equipment_type_elevator": onehot_in(eq_t, "エレベータ"),
        "equipment_type_other_flag": onehot_in(eq_t, "その他"), "equipment_type_other": normalize_text(eq.get("otherText")),
        "social_service_usage_0": onehot_equals(ssu, "0"), "social_service_usage_1": onehot_equals(ssu, "1"), "social_service_usage_2": onehot_equals(ssu, "2"), "social_service_usage_3": onehot_equals(ssu, "3"),
        "social_service_reason_text": normalize_text(ssd.get("reasonText")) if ssu == "3" else None,
    }


def get_family_row(page1: dict, index: int) -> dict:
    rows = get_by_path(page1, "familySupport.familyRows")
    if not isinstance(rows, list):
        rows = page1.get("familyRows")
    if not isinstance(rows, list):
        rows = page1.get("family_rows")
    if not isinstance(rows, list) or index < 0 or index >= len(rows):
        return {}
    row = rows[index]
    return row if isinstance(row, dict) else {}


def is_pregnancy_burden(care_burden: str) -> int:
    return 1 if care_burden in ("妊娠", "育児中") else 0


def init_db():
    # データベースに保存先テーブルを用意する
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS form0_legacy (
                updated_at TEXT NOT NULL,
                last_saved_kind TEXT NOT NULL,
                final_submitted_at TEXT,
                user_id TEXT NOT NULL,
                assessment_round INTEGER NOT NULL,
                office_id TEXT,
                personal_id TEXT,
                birth_year INTEGER,
                birth_month INTEGER,
                birth_day INTEGER,
                age INTEGER,
                sex_male INTEGER,
                sex_female INTEGER,
                sex_unspecified INTEGER,
                sex_NA INTEGER,
                request_route_CM INTEGER,
                request_route_MSW INTEGER,
                request_route_hospital_doctor INTEGER,
                request_route_hospital_ns INTEGER,
                request_route_private_doctor INTEGER,
                request_route_welfare_staff INTEGER,
                request_route_health_center INTEGER,
                request_route_family INTEGER,
                request_route_other INTEGER,
                request_organization TEXT,
                requestor_name TEXT,
                requestor_tel TEXT,
                requestor_fax TEXT,
                requestor_email TEXT,
                reception_year INTEGER,
                reception_month INTEGER,
                reception_day INTEGER,
                reception_hour INTEGER,
                reception_minute INTEGER,
                reception_staff TEXT,
                reception_method_document INTEGER,
                reception_method_fax INTEGER,
                reception_method_meeting INTEGER,
                reception_method_mail INTEGER,
                reception_method_phone INTEGER,
                reception_method_other INTEGER,
                request_reason TEXT,
                assessment_first_year INTEGER,
                assessment_first_month INTEGER,
                assessment_first_day INTEGER,
                assessment_regular_year INTEGER,
                assessment_regular_month INTEGER,
                assessment_regular_day INTEGER,
                assessment_worsen_year INTEGER,
                assessment_worsen_month INTEGER,
                assessment_worsen_day INTEGER,
                assessment_discharge_year INTEGER,
                assessment_discharge_month INTEGER,
                assessment_discharge_day INTEGER,
                assessment_admission_year INTEGER,
                assessment_admission_month INTEGER,
                assessment_admission_day INTEGER,
                participant_1 INTEGER,
                participant_2 INTEGER,
                participant_3 INTEGER,
                participant_4 INTEGER,
                participant_5 INTEGER,
                participant_6 INTEGER,
                participant_7 INTEGER,
                participant_8 INTEGER,
                participant_9 INTEGER,
                participant_10 INTEGER,
                interview_location_home INTEGER,
                interview_location_facility INTEGER,
                interview_location_other_flag INTEGER,
                interview_location_other_text TEXT,
                cm_24h_no INTEGER,
                cm_24h_yes INTEGER,
                kaigo_24h_no INTEGER,
                kaigo_24h_yes INTEGER,
                kangoshi_24h_no INTEGER,
                kangoshi_24h_yes INTEGER,
                end_year INTEGER,
                end_month INTEGER,
                end_day INTEGER,
                summary_recorder TEXT,
                exit_summary TEXT,
                PRIMARY KEY (user_id, assessment_round)
            )
            """
        )
        ensure_column_exists(conn, "form0_legacy", "final_submitted_at", "TEXT")
        ensure_updated_and_kind_first(conn)
        ensure_form1_columns(conn)
        ensure_form2_columns(conn)
        ensure_form3_columns(conn)
        ensure_form4_columns(conn)
        ensure_form5_columns(conn)
        ensure_form6_columns(conn)
        ensure_form7_columns(conn)
        ensure_form8_columns(conn)
        ensure_form9_columns(conn)
        ensure_form10_columns(conn)
        ensure_form11_columns(conn)
        ensure_form12_columns(conn)
        ensure_form13_columns(conn)
        ensure_form14_columns(conn)
        ensure_form15_columns(conn)
        ensure_form16_columns(conn)
        ensure_form17_columns(conn)
        ensure_form18_columns(conn)
        ensure_form19_columns(conn)
        ensure_form_payloads_table(conn)


def ensure_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {row[1] for row in rows}
    if column_name in existing:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def ensure_updated_and_kind_first(conn: sqlite3.Connection):
    # DB Browserで見やすいよう、時刻と保存種別を先頭列にそろえる
    rows = conn.execute("PRAGMA table_info(form0_legacy)").fetchall()
    if not rows:
        return
    first_column = rows[0][1]
    second_column = rows[1][1] if len(rows) > 1 else None
    if first_column == "updated_at" and second_column == "last_saved_kind":
        return

    conn.execute(
        """
        CREATE TABLE form0_legacy_new (
            updated_at TEXT NOT NULL,
            last_saved_kind TEXT NOT NULL,
            final_submitted_at TEXT,
            user_id TEXT NOT NULL,
            assessment_round INTEGER NOT NULL,
            office_id TEXT,
            personal_id TEXT,
            birth_year INTEGER,
            birth_month INTEGER,
            birth_day INTEGER,
            age INTEGER,
            sex_male INTEGER,
            sex_female INTEGER,
            sex_unspecified INTEGER,
            sex_NA INTEGER,
            request_route_CM INTEGER,
            request_route_MSW INTEGER,
            request_route_hospital_doctor INTEGER,
            request_route_hospital_ns INTEGER,
            request_route_private_doctor INTEGER,
            request_route_welfare_staff INTEGER,
            request_route_health_center INTEGER,
            request_route_family INTEGER,
            request_route_other INTEGER,
            request_organization TEXT,
            requestor_name TEXT,
            requestor_tel TEXT,
            requestor_fax TEXT,
            requestor_email TEXT,
            reception_year INTEGER,
            reception_month INTEGER,
            reception_day INTEGER,
            reception_hour INTEGER,
            reception_minute INTEGER,
            reception_staff TEXT,
            reception_method_document INTEGER,
            reception_method_fax INTEGER,
            reception_method_meeting INTEGER,
            reception_method_mail INTEGER,
            reception_method_phone INTEGER,
            reception_method_other INTEGER,
            request_reason TEXT,
            assessment_first_year INTEGER,
            assessment_first_month INTEGER,
            assessment_first_day INTEGER,
            assessment_regular_year INTEGER,
            assessment_regular_month INTEGER,
            assessment_regular_day INTEGER,
            assessment_worsen_year INTEGER,
            assessment_worsen_month INTEGER,
            assessment_worsen_day INTEGER,
            assessment_discharge_year INTEGER,
            assessment_discharge_month INTEGER,
            assessment_discharge_day INTEGER,
            assessment_admission_year INTEGER,
            assessment_admission_month INTEGER,
            assessment_admission_day INTEGER,
            participant_1 INTEGER,
            participant_2 INTEGER,
            participant_3 INTEGER,
            participant_4 INTEGER,
            participant_5 INTEGER,
            participant_6 INTEGER,
            participant_7 INTEGER,
            participant_8 INTEGER,
            participant_9 INTEGER,
            participant_10 INTEGER,
            interview_location_home INTEGER,
            interview_location_facility INTEGER,
            interview_location_other_flag INTEGER,
            interview_location_other_text TEXT,
            cm_24h_no INTEGER,
            cm_24h_yes INTEGER,
            kaigo_24h_no INTEGER,
            kaigo_24h_yes INTEGER,
            kangoshi_24h_no INTEGER,
            kangoshi_24h_yes INTEGER,
            end_year INTEGER,
            end_month INTEGER,
            end_day INTEGER,
            summary_recorder TEXT,
            exit_summary TEXT,
            PRIMARY KEY (user_id, assessment_round)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO form0_legacy_new (
            updated_at,
            last_saved_kind,
            final_submitted_at,
            user_id,
            assessment_round,
            office_id,
            personal_id,
            birth_year,
            birth_month,
            birth_day,
            age,
            sex_male,
            sex_female,
            sex_unspecified,
            sex_NA,
            request_route_CM,
            request_route_MSW,
            request_route_hospital_doctor,
            request_route_hospital_ns,
            request_route_private_doctor,
            request_route_welfare_staff,
            request_route_health_center,
            request_route_family,
            request_route_other,
            request_organization,
            requestor_name,
            requestor_tel,
            requestor_fax,
            requestor_email,
            reception_year,
            reception_month,
            reception_day,
            reception_hour,
            reception_minute,
            reception_staff,
            reception_method_document,
            reception_method_fax,
            reception_method_meeting,
            reception_method_mail,
            reception_method_phone,
            reception_method_other,
            request_reason,
            assessment_first_year,
            assessment_first_month,
            assessment_first_day,
            assessment_regular_year,
            assessment_regular_month,
            assessment_regular_day,
            assessment_worsen_year,
            assessment_worsen_month,
            assessment_worsen_day,
            assessment_discharge_year,
            assessment_discharge_month,
            assessment_discharge_day,
            assessment_admission_year,
            assessment_admission_month,
            assessment_admission_day,
            participant_1,
            participant_2,
            participant_3,
            participant_4,
            participant_5,
            participant_6,
            participant_7,
            participant_8,
            participant_9,
            participant_10,
            interview_location_home,
            interview_location_facility,
            interview_location_other_flag,
            interview_location_other_text,
            cm_24h_no,
            cm_24h_yes,
            kaigo_24h_no,
            kaigo_24h_yes,
            kangoshi_24h_no,
            kangoshi_24h_yes,
            end_year,
            end_month,
            end_day,
            summary_recorder,
            exit_summary
        )
        SELECT
            updated_at,
            last_saved_kind,
            final_submitted_at,
            user_id,
            assessment_round,
            office_id,
            personal_id,
            birth_year,
            birth_month,
            birth_day,
            age,
            sex_male,
            sex_female,
            sex_unspecified,
            sex_NA,
            request_route_CM,
            request_route_MSW,
            request_route_hospital_doctor,
            request_route_hospital_ns,
            request_route_private_doctor,
            request_route_welfare_staff,
            request_route_health_center,
            request_route_family,
            request_route_other,
            request_organization,
            requestor_name,
            requestor_tel,
            requestor_fax,
            requestor_email,
            reception_year,
            reception_month,
            reception_day,
            reception_hour,
            reception_minute,
            reception_staff,
            reception_method_document,
            reception_method_fax,
            reception_method_meeting,
            reception_method_mail,
            reception_method_phone,
            reception_method_other,
            request_reason,
            assessment_first_year,
            assessment_first_month,
            assessment_first_day,
            assessment_regular_year,
            assessment_regular_month,
            assessment_regular_day,
            assessment_worsen_year,
            assessment_worsen_month,
            assessment_worsen_day,
            assessment_discharge_year,
            assessment_discharge_month,
            assessment_discharge_day,
            assessment_admission_year,
            assessment_admission_month,
            assessment_admission_day,
            participant_1,
            participant_2,
            participant_3,
            participant_4,
            participant_5,
            participant_6,
            participant_7,
            participant_8,
            participant_9,
            participant_10,
            interview_location_home,
            interview_location_facility,
            interview_location_other_flag,
            interview_location_other_text,
            cm_24h_no,
            cm_24h_yes,
            kaigo_24h_no,
            kaigo_24h_yes,
            kangoshi_24h_no,
            kangoshi_24h_yes,
            end_year,
            end_month,
            end_day,
            summary_recorder,
            exit_summary
        FROM form0_legacy
        """
    )
    conn.execute("DROP TABLE form0_legacy")
    conn.execute("ALTER TABLE form0_legacy_new RENAME TO form0_legacy")


def parse_office_and_personal(user_id: str):
    if "_" not in user_id:
        return (None, None)
    office_id, personal_id = user_id.split("_", 1)
    return (office_id or None, personal_id or None)


def map_form0_to_legacy_row(payload: FormData, save_kind: str):
    # page0のJSONを、既存システムの列形式(one-hot列)に変換する
    page0 = FlexDict(payload.answers.get("page0", {}) or {})
    page1 = FlexDict(payload.answers.get("page1", {}) or {})
    page2 = FlexDict(payload.answers.get("page2", {}) or {})
    form2_cols = map_page2_to_form2_columns(page2)
    page3 = FlexDict(payload.answers.get("page3", {}) or {})
    form3_cols = map_page3_to_form3_columns(page3)
    page4 = FlexDict(payload.answers.get("page4", {}) or {})
    form4_cols = map_page4_to_form4_columns(page4)
    page5 = FlexDict(payload.answers.get("page5", {}) or {})
    form5_cols = map_page5_to_form5_columns(page5)
    page6 = FlexDict(payload.answers.get("page6", {}) or {})
    form6_cols = map_page6_to_form6_columns(page6)
    page7 = FlexDict(payload.answers.get("page7", {}) or {})
    form7_cols = map_page7_to_form7_columns(page7)
    page8 = FlexDict(payload.answers.get("page8", {}) or {})
    form8_cols = map_page8_to_form8_columns(page8)
    page9 = FlexDict(payload.answers.get("page9", {}) or {})
    form9_cols = map_page9_to_form9_columns(page9)
    page10 = FlexDict(payload.answers.get("page10", {}) or {})
    form10_cols = map_page10_to_form10_columns(page10)
    page11 = FlexDict(payload.answers.get("page11", {}) or {})
    form11_cols = map_page11_to_form11_columns(page11)
    page12 = FlexDict(payload.answers.get("page12", {}) or {})
    form12_cols = map_page12_to_form12_columns(page12)
    page13 = FlexDict(payload.answers.get("page13", {}) or {})
    form13_cols = map_page13_to_form13_columns(page13)
    page14 = FlexDict(payload.answers.get("page14", {}) or {})
    form14_cols = map_page14_to_form14_columns(page14)
    page15 = FlexDict(payload.answers.get("page15", {}) or {})
    form15_cols = map_page15_to_form15_columns(page15)
    page16 = FlexDict(payload.answers.get("page16", {}) or {})
    form16_cols = map_page16_to_form16_columns(page16)
    page17 = FlexDict(payload.answers.get("page17", {}) or {})
    form17_cols = map_page17_to_form17_columns(page17)
    page18 = FlexDict(payload.answers.get("page18", {}) or {})
    form18_cols = map_page18_to_form18_columns(page18)
    page19 = FlexDict(payload.answers.get("page19", {}) or {})
    form19_cols = map_page19_to_form19_columns(page19, page0)
    user_info = page0.get("userInfo", {}) or page0 or {}
    request_info = page0.get("requestInfo", {}) or page0 or {}
    reception_info = page0.get("receptionInfo", {}) or page0 or {}
    assessment = page0.get("assessment", {}) or page0 or {}
    interview = page0.get("interview", {}) or page0 or {}
    closing = page0.get("closing", {}) or page0 or {}
    free_text = page1.get("freeText", {}) or page1 or {}
    residence_info = page1.get("residenceInfo", {}) or page1 or {}
    care_insurance = page1.get("careInsurance", {}) or page1 or {}
    medical_insurance = page1.get("medicalInsurance", {}) or page1 or {}

    office_id = get_by_path(payload.answers, "_meta.facilityId")
    personal_id = get_by_path(payload.answers, "_meta.personId")
    if not office_id or not personal_id:
        parsed_office_id, parsed_personal_id = parse_office_and_personal(payload.userId)
        office_id = office_id or parsed_office_id
        personal_id = personal_id or parsed_personal_id

    birth_year, birth_month, birth_day = split_date_ymd(user_info.get("birthDate", ""))
    reception_year, reception_month, reception_day = split_date_ymd(reception_info.get("receptionDate", ""))
    end_year, end_month, end_day = split_date_ymd(closing.get("endDate", ""))
    birth_year = to_int_or_none(user_info.get("birth_year")) if birth_year is None else birth_year
    birth_month = to_int_or_none(user_info.get("birth_month")) if birth_month is None else birth_month
    birth_day = to_int_or_none(user_info.get("birth_day")) if birth_day is None else birth_day
    reception_year = to_int_or_none(reception_info.get("reception_year")) if reception_year is None else reception_year
    reception_month = to_int_or_none(reception_info.get("reception_month")) if reception_month is None else reception_month
    reception_day = to_int_or_none(reception_info.get("reception_day")) if reception_day is None else reception_day
    end_year = to_int_or_none(closing.get("end_year")) if end_year is None else end_year
    end_month = to_int_or_none(closing.get("end_month")) if end_month is None else end_month
    end_day = to_int_or_none(closing.get("end_day")) if end_day is None else end_day

    event_dates = {}
    for event in assessment.get("events", []) or []:
        reason = event.get("reason")
        event_dates[reason] = split_date_ymd(event.get("date", ""))

    first_y, first_m, first_d = event_dates.get("初回", (None, None, None))
    regular_y, regular_m, regular_d = event_dates.get("定期継続評価", (None, None, None))
    worsen_y, worsen_m, worsen_d = event_dates.get("状態悪化", (None, None, None))
    discharge_y, discharge_m, discharge_d = event_dates.get("退院", (None, None, None))
    admission_y, admission_m, admission_d = event_dates.get("入院", (None, None, None))
    first_y = to_int_or_none(assessment.get("assessment_first_year")) if first_y is None else first_y
    first_m = to_int_or_none(assessment.get("assessment_first_month")) if first_m is None else first_m
    first_d = to_int_or_none(assessment.get("assessment_first_day")) if first_d is None else first_d
    regular_y = to_int_or_none(assessment.get("assessment_regular_year")) if regular_y is None else regular_y
    regular_m = to_int_or_none(assessment.get("assessment_regular_month")) if regular_m is None else regular_m
    regular_d = to_int_or_none(assessment.get("assessment_regular_day")) if regular_d is None else regular_d
    worsen_y = to_int_or_none(assessment.get("assessment_worsen_year")) if worsen_y is None else worsen_y
    worsen_m = to_int_or_none(assessment.get("assessment_worsen_month")) if worsen_m is None else worsen_m
    worsen_d = to_int_or_none(assessment.get("assessment_worsen_day")) if worsen_d is None else worsen_d
    discharge_y = to_int_or_none(assessment.get("assessment_discharge_year")) if discharge_y is None else discharge_y
    discharge_m = to_int_or_none(assessment.get("assessment_discharge_month")) if discharge_m is None else discharge_m
    discharge_d = to_int_or_none(assessment.get("assessment_discharge_day")) if discharge_d is None else discharge_d
    admission_y = to_int_or_none(assessment.get("assessment_admission_year")) if admission_y is None else admission_y
    admission_m = to_int_or_none(assessment.get("assessment_admission_month")) if admission_m is None else admission_m
    admission_d = to_int_or_none(assessment.get("assessment_admission_day")) if admission_d is None else admission_d

    sex = user_info.get("sex", "")
    request_route = request_info.get("requestRoute") or request_info.get("request_route") or ""
    reception_method = reception_info.get("method") or reception_info.get("reception_method") or ""
    participants = interview.get("participants")
    if not isinstance(participants, list):
        participants = interview.get("participant")
    if not isinstance(participants, list):
        participants = interview.get("participant[]")
    if not isinstance(participants, list):
        participants = [] if participants in (None, "", []) else [participants]
    location = interview.get("location") or interview.get("interview_location") or ""
    response24h = interview.get("response24h", {}) or {}
    if not isinstance(response24h, dict):
        response24h = {}
    response24h = {
        "cm": response24h.get("cm") or interview.get("cm_24h"),
        "care": response24h.get("care") or interview.get("kaigo_24h"),
        "nurse": response24h.get("nurse") or interview.get("kangoshi_24h"),
    }
    housing_type = residence_info.get("housingType") or residence_info.get("housing_type") or ""
    user_burden_ratio = care_insurance.get("userBurdenRatio", "")
    cert_y, cert_m, cert_d = split_date_ymd(care_insurance.get("certificationDate", ""))
    valid_start_y, valid_start_m, valid_start_d = split_date_ymd(get_by_path(care_insurance, "validPeriod.startDate"))
    valid_end_y, valid_end_m, valid_end_d = split_date_ymd(get_by_path(care_insurance, "validPeriod.endDate"))
    cert_y = to_int_or_none(care_insurance.get("certification_year")) if cert_y is None else cert_y
    cert_m = to_int_or_none(care_insurance.get("certification_month")) if cert_m is None else cert_m
    cert_d = to_int_or_none(care_insurance.get("certification_day")) if cert_d is None else cert_d
    valid_start_y = to_int_or_none(care_insurance.get("valid_start_year")) if valid_start_y is None else valid_start_y
    valid_start_m = to_int_or_none(care_insurance.get("valid_start_month")) if valid_start_m is None else valid_start_m
    valid_start_d = to_int_or_none(care_insurance.get("valid_start_day")) if valid_start_d is None else valid_start_d
    valid_end_y = to_int_or_none(care_insurance.get("valid_end_year")) if valid_end_y is None else valid_end_y
    valid_end_m = to_int_or_none(care_insurance.get("valid_end_month")) if valid_end_m is None else valid_end_m
    valid_end_d = to_int_or_none(care_insurance.get("valid_end_day")) if valid_end_d is None else valid_end_d
    support_status = get_by_path(care_insurance, "careStatus.support") or care_insurance.get("support_status")
    nursing_status = get_by_path(care_insurance, "careStatus.nursing") or care_insurance.get("nursing_status")
    dementia_level = care_insurance.get("dementiaLevel") or care_insurance.get("dementia_level") or ""
    elderly_independence_level = care_insurance.get("elderlyIndependenceLevel") or care_insurance.get("elderly_independence_level") or ""
    insurance_type = medical_insurance.get("insuranceType") or medical_insurance.get("insurance_type") or ""
    insurance_category = medical_insurance.get("insuranceCategory") or medical_insurance.get("insurance_category") or ""
    kouki_kourei_burden = medical_insurance.get("koukiKoureiBurden") or medical_insurance.get("kouki_kourei_burden") or ""
    my_number_card = medical_insurance.get("myNumberCard") or medical_insurance.get("my_number_card") or ""
    family_row_1 = get_family_row(page1, 0)
    family_row_2 = get_family_row(page1, 1)
    family_row_3 = get_family_row(page1, 2)
    family_row_4 = get_family_row(page1, 3)

    now_str = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "office_id": office_id,
        "personal_id": personal_id,
        "user_id": payload.userId,
        "assessment_round": payload.assessment_round,
        "birth_year": birth_year,
        "birth_month": birth_month,
        "birth_day": birth_day,
        "age": to_int_or_none(user_info.get("age")),
        "sex_male": onehot_equals(sex, "男"),
        "sex_female": onehot_equals(sex, "女"),
        "sex_unspecified": onehot_equals(sex, "指定なし"),
        "sex_NA": onehot_equals(sex, "NA"),
        "request_route_CM": onehot_equals(request_route, "CM"),
        "request_route_MSW": onehot_equals(request_route, "MSW"),
        "request_route_hospital_doctor": onehot_equals(request_route, "病院医師"),
        "request_route_hospital_ns": onehot_equals(request_route, "病院NS"),
        "request_route_private_doctor": onehot_equals(request_route, "開業医師"),
        "request_route_welfare_staff": onehot_equals(request_route, "福祉職員"),
        "request_route_health_center": onehot_equals(request_route, "保健所・保健センター職員"),
        "request_route_family": onehot_equals(request_route, "家族"),
        "request_route_other": onehot_equals(request_route, "その他"),
        "request_organization": request_info.get("organization") or request_info.get("request_organization") or None,
        "requestor_name": request_info.get("requestorName") or request_info.get("requestor_name") or None,
        "requestor_tel": request_info.get("requestorTel") or request_info.get("requestor_tel") or None,
        "requestor_fax": request_info.get("requestorFax") or request_info.get("requestor_fax") or None,
        "requestor_email": request_info.get("requestorEmail") or request_info.get("requestor_email") or None,
        "reception_year": reception_year,
        "reception_month": reception_month,
        "reception_day": reception_day,
        "reception_hour": to_int_or_none(get_by_path(reception_info, "receptionTime.hour")) if to_int_or_none(get_by_path(reception_info, "receptionTime.hour")) is not None else to_int_or_none(reception_info.get("reception_hour")),
        "reception_minute": to_int_or_none(get_by_path(reception_info, "receptionTime.minute")) if to_int_or_none(get_by_path(reception_info, "receptionTime.minute")) is not None else to_int_or_none(reception_info.get("reception_minute")),
        "reception_staff": reception_info.get("staff") or reception_info.get("reception_staff") or None,
        "reception_method_document": onehot_equals(reception_method, "書面"),
        "reception_method_fax": onehot_equals(reception_method, "Fax"),
        "reception_method_meeting": onehot_equals(reception_method, "面会"),
        "reception_method_mail": onehot_equals(reception_method, "mail"),
        "reception_method_phone": onehot_equals(reception_method, "電話"),
        "reception_method_other": onehot_equals(reception_method, "その他"),
        "request_reason": reception_info.get("reason") or reception_info.get("request_reason") or None,
        "assessment_first_year": first_y,
        "assessment_first_month": first_m,
        "assessment_first_day": first_d,
        "assessment_regular_year": regular_y,
        "assessment_regular_month": regular_m,
        "assessment_regular_day": regular_d,
        "assessment_worsen_year": worsen_y,
        "assessment_worsen_month": worsen_m,
        "assessment_worsen_day": worsen_d,
        "assessment_discharge_year": discharge_y,
        "assessment_discharge_month": discharge_m,
        "assessment_discharge_day": discharge_d,
        "assessment_admission_year": admission_y,
        "assessment_admission_month": admission_m,
        "assessment_admission_day": admission_d,
        "participant_1": onehot_in(participants, "1"),
        "participant_2": onehot_in(participants, "2"),
        "participant_3": onehot_in(participants, "3"),
        "participant_4": onehot_in(participants, "4"),
        "participant_5": onehot_in(participants, "5"),
        "participant_6": onehot_in(participants, "6"),
        "participant_7": onehot_in(participants, "7"),
        "participant_8": onehot_in(participants, "8"),
        "participant_9": onehot_in(participants, "9"),
        "participant_10": onehot_in(participants, "10"),
        "interview_location_home": onehot_equals(location, "1"),
        "interview_location_facility": onehot_equals(location, "2"),
        "interview_location_other_flag": onehot_equals(location, "3"),
        "interview_location_other_text": interview.get("locationOther") or interview.get("interview_location_other") or None,
        "cm_24h_no": onehot_equals(response24h.get("cm"), "0"),
        "cm_24h_yes": onehot_equals(response24h.get("cm"), "1"),
        "kaigo_24h_no": onehot_equals(response24h.get("care"), "0"),
        "kaigo_24h_yes": onehot_equals(response24h.get("care"), "1"),
        "kangoshi_24h_no": onehot_equals(response24h.get("nurse"), "0"),
        "kangoshi_24h_yes": onehot_equals(response24h.get("nurse"), "1"),
        "end_year": end_year,
        "end_month": end_month,
        "end_day": end_day,
        "summary_recorder": closing.get("summaryRecorder") or closing.get("summary_recorder") or None,
        "exit_summary": closing.get("exitSummary") or closing.get("exit_summary") or None,
        "housing_type_home": onehot_equals(housing_type, "自宅"),
        "housing_type_apartment": onehot_equals(housing_type, "アパート"),
        "housing_type_mansion": onehot_equals(housing_type, "一般マンション"),
        "housing_type_senior_mansion": onehot_equals(housing_type, "高齢者マンション"),
        "housing_type_group_home": onehot_equals(housing_type, "グループホーム"),
        "housing_type_rented": onehot_equals(housing_type, "借間"),
        "housing_type_welfare": onehot_equals(housing_type, "福祉施設"),
        "housing_type_rehab": onehot_equals(housing_type, "生活訓練施設"),
        "housing_type_employment_facility": onehot_equals(housing_type, "入所授産施設"),
        "housing_type_other_flag": onehot_equals(housing_type, "その他"),
        "housing_type_other": normalize_text(residence_info.get("housingTypeOther") or residence_info.get("housing_type_other")),
        "insurer_name": normalize_text(care_insurance.get("insurerName") or care_insurance.get("insurer_name")),
        "user_burden_ratio_1割": onehot_equals(user_burden_ratio, "1割"),
        "user_burden_ratio_2割": onehot_equals(user_burden_ratio, "2割"),
        "user_burden_ratio_3割": onehot_equals(user_burden_ratio, "3割"),
        "certification_year": cert_y, "certification_month": cert_m, "certification_day": cert_d,
        "valid_start_year": valid_start_y, "valid_start_month": valid_start_m, "valid_start_day": valid_start_d,
        "valid_end_year": valid_end_y, "valid_end_month": valid_end_m, "valid_end_day": valid_end_d,
        "care_status_要支援1": onehot_equals(support_status, "要支援1"), "care_status_要支援2": onehot_equals(support_status, "要支援2"),
        "care_status_nursing_要介護1": onehot_equals(nursing_status, "要介護1"), "care_status_nursing_要介護2": onehot_equals(nursing_status, "要介護2"),
        "care_status_nursing_要介護3": onehot_equals(nursing_status, "要介護3"), "care_status_nursing_要介護4": onehot_equals(nursing_status, "要介護4"),
        "care_status_nursing_要介護5": onehot_equals(nursing_status, "要介護5"),
        "benefit_limit": to_int_or_none(care_insurance.get("benefitLimit")) if to_int_or_none(care_insurance.get("benefitLimit")) is not None else to_int_or_none(care_insurance.get("benefit_limit")),
        "dementia_level_自立": onehot_equals(dementia_level, "自立"), "dementia_level_Ⅰ": onehot_equals(dementia_level, "Ⅰ"),
        "dementia_level_Ⅱa": onehot_equals(dementia_level, "Ⅱa"), "dementia_level_Ⅱb": onehot_equals(dementia_level, "Ⅱb"),
        "dementia_level_Ⅲa": onehot_equals(dementia_level, "Ⅲa"), "dementia_level_Ⅲb": onehot_equals(dementia_level, "Ⅲb"),
        "dementia_level_Ⅳ": onehot_equals(dementia_level, "Ⅳ"), "dementia_level_M": onehot_equals(dementia_level, "M"),
        "elderly_independence_level_自立": onehot_equals(elderly_independence_level, "自立"),
        "elderly_independence_level_J1": onehot_equals(elderly_independence_level, "J1"), "elderly_independence_level_J2": onehot_equals(elderly_independence_level, "J2"),
        "elderly_independence_level_A1": onehot_equals(elderly_independence_level, "A1"), "elderly_independence_level_A2": onehot_equals(elderly_independence_level, "A2"),
        "elderly_independence_level_B1": onehot_equals(elderly_independence_level, "B1"), "elderly_independence_level_B2": onehot_equals(elderly_independence_level, "B2"),
        "elderly_independence_level_C1": onehot_equals(elderly_independence_level, "C1"), "elderly_independence_level_C2": onehot_equals(elderly_independence_level, "C2"),
        "insurer_name_medical": normalize_text(medical_insurance.get("insurerName") or medical_insurance.get("insurer_name_medical")),
        "insurance_type_self": onehot_equals(insurance_type, "本人"), "insurance_type_family": onehot_equals(insurance_type, "家族"),
        "insurance_category_national": onehot_equals(insurance_category, "国保"), "insurance_category_social": onehot_equals(insurance_category, "社保"),
        "insurance_category_mutual": onehot_equals(insurance_category, "共済"), "insurance_category_labor": onehot_equals(insurance_category, "労災"),
        "insurance_category_elderly": onehot_equals(insurance_category, "後期高齢者医療"),
        "kouki_kourei_burden_1割": onehot_equals(kouki_kourei_burden, "1割"), "kouki_kourei_burden_2割": onehot_equals(kouki_kourei_burden, "2割"), "kouki_kourei_burden_3割": onehot_equals(kouki_kourei_burden, "3割"),
        "insurance_category_other_flag": onehot_equals(insurance_category, "その他"), "insurance_other_detail": normalize_text(medical_insurance.get("insuranceOtherDetail") or medical_insurance.get("insurance_other_detail")),
        "my_number_card_yes": onehot_equals(my_number_card, "なし"), "my_number_card_no": onehot_equals(my_number_card, "あり"),
        "doctor_opinion": normalize_text(medical_insurance.get("doctorOpinion") or medical_insurance.get("doctor_opinion")),
        "support_type_1_keyperson": onehot_in(family_row_1.get("supportType"), "キーパーソン"), "support_type_1_maincaregiver": onehot_in(family_row_1.get("supportType"), "主介護者"),
        "living_status_1_samehouse": onehot_equals(family_row_1.get("livingStatus"), "同居"), "living_status_1_dayabsent": onehot_equals(family_row_1.get("livingStatus"), "同居日中不在"), "living_status_1_separate": onehot_equals(family_row_1.get("livingStatus"), "別居"),
        "care_burden_1_working": onehot_equals(family_row_1.get("careBurden"), "就労中"), "care_burden_1_studying": onehot_equals(family_row_1.get("careBurden"), "就学中"),
        "care_burden_1_elderly": onehot_equals(family_row_1.get("careBurden"), "高齢"), "care_burden_1_disabled": onehot_equals(family_row_1.get("careBurden"), "要介護等"), "care_burden_1_pregnant": is_pregnancy_burden(family_row_1.get("careBurden", "")),
        "support_type_2_keyperson": onehot_in(family_row_2.get("supportType"), "キーパーソン"), "support_type_2_maincaregiver": onehot_in(family_row_2.get("supportType"), "主介護者"),
        "living_status_2_samehouse": onehot_equals(family_row_2.get("livingStatus"), "同居"), "living_status_2_dayabsent": onehot_equals(family_row_2.get("livingStatus"), "同居日中不在"), "living_status_2_separate": onehot_equals(family_row_2.get("livingStatus"), "別居"),
        "care_burden_2_working": onehot_equals(family_row_2.get("careBurden"), "就労中"), "care_burden_2_studying": onehot_equals(family_row_2.get("careBurden"), "就学中"),
        "care_burden_2_elderly": onehot_equals(family_row_2.get("careBurden"), "高齢"), "care_burden_2_disabled": onehot_equals(family_row_2.get("careBurden"), "要介護等"), "care_burden_2_pregnant": is_pregnancy_burden(family_row_2.get("careBurden", "")),
        "care_sharing_3": normalize_text(family_row_3.get("careSharing")), "living_status_3_samehouse": onehot_equals(family_row_3.get("livingStatus"), "同居"),
        "living_status_3_dayabsent": onehot_equals(family_row_3.get("livingStatus"), "同居日中不在"), "living_status_3_separate": onehot_equals(family_row_3.get("livingStatus"), "別居"),
        "care_burden_3_working": onehot_equals(family_row_3.get("careBurden"), "就労中"), "care_burden_3_studying": onehot_equals(family_row_3.get("careBurden"), "就学中"),
        "care_burden_3_elderly": onehot_equals(family_row_3.get("careBurden"), "高齢"), "care_burden_3_disabled": onehot_equals(family_row_3.get("careBurden"), "要介護等"), "care_burden_3_pregnant": is_pregnancy_burden(family_row_3.get("careBurden", "")),
        "care_sharing_4": normalize_text(family_row_4.get("careSharing")), "living_status_4_samehouse": onehot_equals(family_row_4.get("livingStatus"), "同居"),
        "living_status_4_dayabsent": onehot_equals(family_row_4.get("livingStatus"), "同居日中不在"), "living_status_4_separate": onehot_equals(family_row_4.get("livingStatus"), "別居"),
        "care_burden_4_working": onehot_equals(family_row_4.get("careBurden"), "就労中"), "care_burden_4_studying": onehot_equals(family_row_4.get("careBurden"), "就学中"),
        "care_burden_4_elderly": onehot_equals(family_row_4.get("careBurden"), "高齢"), "care_burden_4_disabled": onehot_equals(family_row_4.get("careBurden"), "要介護等"), "care_burden_4_pregnant": is_pregnancy_burden(family_row_4.get("careBurden", "")),
        "genogramCanvas_image": None,
        "user_requests": normalize_text(free_text.get("userRequests")),
        "family_requests": normalize_text(free_text.get("familyRequests")),
        **form2_cols,
        **form3_cols,
        **form4_cols,
        **form5_cols,
        **form6_cols,
        **form7_cols,
        **form8_cols,
        **form9_cols,
        **form10_cols,
        **form11_cols,
        **form12_cols,
        **form13_cols,
        **form14_cols,
        **form15_cols,
        **form16_cols,
        **form17_cols,
        **form18_cols,
        **form19_cols,
        "last_saved_kind": save_kind,
        "final_submitted_at": now_str if save_kind == "final" else None,
        "updated_at": now_str,
    }


def upsert_form0_legacy(row: dict):
    # 同じ user_id + 回数 の行があれば上書き、なければ新規追加
    columns = list(row.keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(quote_ident(col) for col in columns)
    update_expressions = []
    for col in columns:
        if col in ("user_id", "assessment_round"):
            continue
        if col == "final_submitted_at":
            # /save のときは NULL が来るため、既存の確定時刻を保持する
            col_sql = quote_ident(col)
            update_expressions.append(f"{col_sql}=COALESCE(excluded.{col_sql}, form0_legacy.{col_sql})")
        else:
            col_sql = quote_ident(col)
            update_expressions.append(f"{col_sql}=excluded.{col_sql}")
    updates = ", ".join(update_expressions)
    sql = f"""
    INSERT INTO form0_legacy ({col_list})
    VALUES ({placeholders})
    ON CONFLICT(user_id, assessment_round) DO UPDATE SET
    {updates}
    """
    values = [row[col] for col in columns]
    def _write(conn: sqlite3.Connection):
        conn.execute(sql, values)
    run_db_write_with_retry(_write)


@app.on_event("startup")
async def startup():
    init_db()


def _coerce_round(value) -> int:
    text = str(value or "").strip()
    return int(text) if text in {"1", "2", "3"} else 1


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _is_effectively_empty_payload(data: dict | None) -> bool:
    if not data:
        return True
    meta = {"assessment_round", "user_id", "office_id", "personal_id", "timestamp", "form_id"}
    for key, value in data.items():
        if key in meta or key.endswith("_idx"):
            continue
        if isinstance(value, list):
            if any(str(v or "").strip() not in ("", "0") for v in value):
                return False
            continue
        text = "" if value is None else str(value).strip()
        if text not in ("", "0"):
            return False
    return True


def _read_form_payload(user_id: str, assessment_round: int, form_num: int) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM form_payloads
            WHERE user_id = ? AND assessment_round = ? AND form_num = ?
            """,
            (user_id, assessment_round, form_num),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row[0])
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _upsert_form_payload(user_id: str, assessment_round: int, form_num: int, payload: dict):
    def _write(conn: sqlite3.Connection):
        conn.execute(
            """
            INSERT INTO form_payloads (user_id, assessment_round, form_num, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, assessment_round, form_num) DO UPDATE SET
                payload_json=excluded.payload_json,
                updated_at=excluded.updated_at
            """,
            (user_id, assessment_round, form_num, json.dumps(payload, ensure_ascii=False), _now_text()),
        )
    run_db_write_with_retry(_write)


def _build_legacy_answers_from_payloads(user_id: str, assessment_round: int) -> dict:
    answers = {}
    office_id = None
    personal_id = None
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT form_num, payload_json
            FROM form_payloads
            WHERE user_id = ? AND assessment_round = ?
            ORDER BY form_num
            """,
            (user_id, assessment_round),
        ).fetchall()
    for row in rows:
        form_num = int(row["form_num"])
        try:
            payload = json.loads(row["payload_json"])
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        page_key = f"page{form_num}"
        page_data = dict(payload)
        if office_id is None and str(page_data.get("office_id", "")).strip():
            office_id = str(page_data.get("office_id")).strip()
        if personal_id is None and str(page_data.get("personal_id", "")).strip():
            personal_id = str(page_data.get("personal_id")).strip()
        for meta_key in ("assessment_round", "user_id", "office_id", "personal_id", "timestamp", "form_id"):
            page_data.pop(meta_key, None)
        answers[page_key] = page_data
    for idx in range(20):
        answers.setdefault(f"page{idx}", {})
    answers["_meta"] = {
        "facilityId": office_id,
        "personId": personal_id,
    }
    return answers


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


@app.get("/")
async def root_entry():
    if FORMS_DIR.is_dir() and (FORMS_DIR / "form.html").is_file():
        return RedirectResponse(url="/form.html")
    return {"status": "ok", "message": "API server is running"}


@app.get("/form.html")
async def serve_form_entry():
    path = FORMS_DIR / "form.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="form.html not found")
    return FileResponse(path)


@app.get("/form{form_num}.html")
async def serve_form_page(form_num: int):
    path = FORMS_DIR / f"form{form_num}.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"form{form_num}.html not found")
    return FileResponse(path)


@app.get("/Explanation.html")
async def serve_explanation_page():
    path = FORMS_DIR / "Explanation.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Explanation.html not found")
    return FileResponse(path)


@app.get("/verify.html")
async def serve_verify_page():
    path = FRONTEND_DIR / "verify.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="verify.html not found")
    return FileResponse(path)


@app.post("/api/session/start")
async def session_start(request: Request):
    payload = await request.json()
    office_id = str(payload.get("office_id", "")).strip()
    personal_id = str(payload.get("personal_id", "")).strip()
    cur_round = _coerce_round(payload.get("round"))
    if not office_id or not personal_id:
        raise HTTPException(status_code=400, detail="office_id and personal_id are required")

    user_id = f"{office_id}_{personal_id}"
    if cur_round == 1:
        return {"status": "ok", "round": 1, "created": False, "source": "empty"}

    prev_round = cur_round - 1
    prev_payload = _read_form_payload(user_id, prev_round, 0)
    if prev_payload is None or _is_effectively_empty_payload(prev_payload):
        raise HTTPException(
            status_code=409,
            detail=f"まだ{prev_round}回目のアセスメントが入力されていないため、{cur_round}回目のアセスメントは入力できません。",
        )
    return {"status": "ok", "round": cur_round, "created": False, "source": "current"}


@app.post("/api/session/finalize")
async def session_finalize(request: Request):
    payload = await request.json()
    office_id = str(payload.get("office_id", "")).strip()
    personal_id = str(payload.get("personal_id", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()
    if not user_id and office_id and personal_id:
        user_id = f"{office_id}_{personal_id}"
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    round_num = _coerce_round(payload.get("round") or payload.get("assessment_round"))
    answers = _build_legacy_answers_from_payloads(user_id, round_num)
    form_data = FormData(userId=user_id, assessment_round=round_num, answers=answers)
    legacy_row = map_form0_to_legacy_row(form_data, "final")
    upsert_form0_legacy(legacy_row)
    return {"status": "ok", "user_id": user_id, "assessment_round": round_num, "saved_table": "form0_legacy"}


@app.post("/api/form/{form_num}")
async def save_form_payload(form_num: int, request: Request):
    payload = _normalize_checkbox_bracket_keys(await request.json())
    office_id = str(payload.get("office_id", "")).strip()
    personal_id = str(payload.get("personal_id", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()
    if not user_id and office_id and personal_id:
        user_id = f"{office_id}_{personal_id}"
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    round_num = _coerce_round(payload.get("assessment_round"))
    payload["assessment_round"] = str(round_num)
    payload["user_id"] = user_id
    if office_id:
        payload["office_id"] = office_id
    if personal_id:
        payload["personal_id"] = personal_id
    payload["timestamp"] = _now_text()
    payload["form_id"] = f"form{form_num}"
    _upsert_form_payload(user_id, round_num, form_num, payload)
    # 通常保存時も JSON 原本から one-hot へ反映（draft 更新）
    answers = _build_legacy_answers_from_payloads(user_id, round_num)
    form_data = FormData(userId=user_id, assessment_round=round_num, answers=answers)
    legacy_row = map_form0_to_legacy_row(form_data, "draft")
    upsert_form0_legacy(legacy_row)
    return {"status": "ok", "form_num": form_num, "user_id": user_id, "assessment_round": round_num}


@app.get("/api/form/{form_num}/initial")
async def get_form_initial(form_num: int, user_id: str = Query(...), round: int = Query(1)):
    rid = str(user_id or "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail="user_id is required")
    round_num = _coerce_round(round)
    payload = _read_form_payload(rid, round_num, form_num)
    if payload and not _is_effectively_empty_payload(payload):
        return {"status": "ok", "round": round_num, "initial_data": payload, "source": "current"}
    return {"status": "ok", "round": round_num, "initial_data": {}, "source": "empty"}


@app.get("/api/form/{form_num}/current")
async def get_form_current(form_num: int, office_id: str = Query(...), personal_id: str = Query(...), round: int = Query(1)):
    rid = f"{str(office_id or '').strip()}_{str(personal_id or '').strip()}"
    if rid in {"_", ""}:
        raise HTTPException(status_code=400, detail="office_id and personal_id are required")
    round_num = _coerce_round(round)
    payload = _read_form_payload(rid, round_num, form_num)
    if payload and not _is_effectively_empty_payload(payload):
        return {"status": "ok", "round": round_num, "initial_data": payload, "source": "current"}
    return {"status": "ok", "round": round_num, "initial_data": {}, "source": "empty"}


def sanitize_filename_stem(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or "").strip())
    return text.strip("._-") or "image"


def infer_upload_extension(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    content_type = (upload.content_type or "").lower()
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/gif":
        return ".gif"
    return ".jpg"


@app.post("/api/upload_image")
async def upload_image(
    file: UploadFile = File(...),
    category: str = Form(...),
    label: str = Form(default="image"),
    user_id: str = Form(default="anonymous"),
):
    normalized_category = str(category or "").strip().lower()
    if normalized_category not in ALLOWED_UPLOAD_CATEGORIES:
        raise HTTPException(status_code=400, detail="invalid category")
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="only image file is allowed")

    safe_user = sanitize_filename_stem(user_id)
    safe_label = sanitize_filename_stem(label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid4().hex[:8]
    extension = infer_upload_extension(file)
    filename = f"{safe_user}_{safe_label}_{timestamp}_{unique_id}{extension}"

    save_dir = UPLOADS_DIR / normalized_category
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")
    save_path.write_bytes(contents)

    return {
        "status": "ok",
        "filename": filename,
        "url": f"/uploads/{normalized_category}/{filename}",
        "category": normalized_category,
    }


@app.post("/submit")
async def submit(data: FormData):
    # 確定送信: 「確定時刻」を記録して保存
    legacy_row = map_form0_to_legacy_row(data, "final")
    upsert_form0_legacy(legacy_row)
    return {
        "status": "ok",
        "received_userId": data.userId,
        "received_assessment_round": data.assessment_round,
        "saved_table": "form0_legacy",
        "page_keys": list(data.answers.keys()),
    }


@app.post("/save")
async def save(data: FormData):
    # 下書き保存: 確定時刻は変えずに更新
    legacy_row = map_form0_to_legacy_row(data, "draft")
    upsert_form0_legacy(legacy_row)
    return {
        "status": "saved",
        "received_userId": data.userId,
        "received_assessment_round": data.assessment_round,
        "saved_table": "form0_legacy",
        "page_keys": list(data.answers.keys()),
    }


def fetch_all_dicts(sql: str, params: tuple = ()):
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def evaluate_onehot_group(row: dict, group_name: str, columns: list[str]):
    non_binary = []
    one_count = 0
    selected_columns = []
    for col in columns:
        value = row.get(col)
        if value not in (None, 0, 1):
            non_binary.append(col)
        if value == 1:
            one_count += 1
            selected_columns.append(col)
    return {
        "group": group_name,
        "one_count": one_count,
        "selected_columns": selected_columns,
        "has_conflict": one_count > 1,
        "non_binary_columns": non_binary,
    }


@app.get("/verify/latest")
async def verify_latest(limit: int = Query(default=50, ge=1, le=500)):
    # 検証画面: 最新順の一覧
    rows = fetch_all_dicts(
        """
        SELECT
            updated_at,
            last_saved_kind,
            final_submitted_at,
            user_id,
            assessment_round
        FROM form0_legacy
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return {
        "count": len(rows),
        "rows": rows,
    }


@app.get("/verify/user/{user_id}")
async def verify_user(user_id: str):
    # 検証画面: 指定ユーザーの詳細一覧
    rows = fetch_all_dicts(
        """
        SELECT *
        FROM form0_legacy
        WHERE user_id = ?
        ORDER BY assessment_round
        """,
        (user_id,),
    )
    return {
        "user_id": user_id,
        "count": len(rows),
        "rows": rows,
    }


@app.get("/verify/round-status/{user_id}")
async def verify_round_status(user_id: str):
    # 検証画面: 1回目/2回目/3回目が存在するか確認
    rows = fetch_all_dicts(
        """
        SELECT
            user_id,
            MAX(CASE WHEN assessment_round = 1 THEN 1 ELSE 0 END) AS has_round1,
            MAX(CASE WHEN assessment_round = 2 THEN 1 ELSE 0 END) AS has_round2,
            MAX(CASE WHEN assessment_round = 3 THEN 1 ELSE 0 END) AS has_round3,
            MAX(updated_at) AS latest_update
        FROM form0_legacy
        WHERE user_id = ?
        GROUP BY user_id
        """,
        (user_id,),
    )
    if not rows:
        return {
            "user_id": user_id,
            "has_round1": 0,
            "has_round2": 0,
            "has_round3": 0,
            "latest_update": None,
        }
    return rows[0]


@app.get("/verify/consistency/{user_id}")
async def verify_consistency(user_id: str):
    # 検証画面: one-hot列に矛盾（重複選択・異常値）がないか確認
    rows = fetch_all_dicts(
        """
        SELECT *
        FROM form0_legacy
        WHERE user_id = ?
        ORDER BY assessment_round
        """,
        (user_id,),
    )
    if not rows:
        return {
            "user_id": user_id,
            "count": 0,
            "rows": [],
            "summary": {
                "has_any_conflict": False,
                "rounds_with_conflict": [],
            },
        }

    single_choice_groups = [
        ("sex", ["sex_male", "sex_female", "sex_unspecified", "sex_NA"]),
        (
            "request_route",
            [
                "request_route_CM",
                "request_route_MSW",
                "request_route_hospital_doctor",
                "request_route_hospital_ns",
                "request_route_private_doctor",
                "request_route_welfare_staff",
                "request_route_health_center",
                "request_route_family",
                "request_route_other",
            ],
        ),
        (
            "reception_method",
            [
                "reception_method_document",
                "reception_method_fax",
                "reception_method_meeting",
                "reception_method_mail",
                "reception_method_phone",
                "reception_method_other",
            ],
        ),
        (
            "interview_location",
            [
                "interview_location_home",
                "interview_location_facility",
                "interview_location_other_flag",
            ],
        ),
        ("cm_24h", ["cm_24h_no", "cm_24h_yes"]),
        ("kaigo_24h", ["kaigo_24h_no", "kaigo_24h_yes"]),
        ("kangoshi_24h", ["kangoshi_24h_no", "kangoshi_24h_yes"]),
    ]
    multi_choice_groups = [
        (
            "participants",
            [
                "participant_1",
                "participant_2",
                "participant_3",
                "participant_4",
                "participant_5",
                "participant_6",
                "participant_7",
                "participant_8",
                "participant_9",
                "participant_10",
            ],
        )
    ]

    checked_rows = []
    rounds_with_conflict = []
    for row in rows:
        checks = []
        has_conflict = False
        for group_name, columns in single_choice_groups:
            result = evaluate_onehot_group(row, group_name, columns)
            checks.append(result)
            if result["has_conflict"] or result["non_binary_columns"]:
                has_conflict = True

        multi_stats = []
        for group_name, columns in multi_choice_groups:
            result = evaluate_onehot_group(row, group_name, columns)
            # multi は複数選択が正常なので conflict 扱いしない。異常値のみ検知。
            result["has_conflict"] = False
            multi_stats.append(result)
            if result["non_binary_columns"]:
                has_conflict = True

        checked_row = {
            "assessment_round": row.get("assessment_round"),
            "updated_at": row.get("updated_at"),
            "last_saved_kind": row.get("last_saved_kind"),
            "has_conflict": has_conflict,
            "single_choice_checks": checks,
            "multi_choice_stats": multi_stats,
        }
        if has_conflict:
            rounds_with_conflict.append(row.get("assessment_round"))
        checked_rows.append(checked_row)

    return {
        "user_id": user_id,
        "count": len(checked_rows),
        "rows": checked_rows,
        "summary": {
            "has_any_conflict": len(rounds_with_conflict) > 0,
            "rounds_with_conflict": rounds_with_conflict,
        },
    }


@app.get("/{asset_path:path}")
async def serve_forms_assets(asset_path: str):
    if asset_path.startswith(("api/", "verify/", "uploads/", "static/")):
        raise HTTPException(status_code=404, detail="Not Found")
    if ".." in asset_path:
        raise HTTPException(status_code=400, detail="invalid path")
    path = (FORMS_DIR / asset_path).resolve()
    if not FORMS_DIR.is_dir() or not path.is_file() or FORMS_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path)
