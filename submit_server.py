"""
ローカル確認用: POST /save と POST /submit を 8000 番で受け付けます。

起動例:
  pip install -r requirements.txt
  uvicorn submit_server:app --reload --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI()
DB_PATH = Path(__file__).with_name("apos_hc.db")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def onehot_equals(value, expected):
    return 1 if value == expected else 0


def onehot_in(values, expected):
    if not isinstance(values, list):
        return 0
    return 1 if expected in values else 0


def init_db():
    # データベースに保存先テーブルを用意する
    with sqlite3.connect(DB_PATH) as conn:
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
    page0 = payload.answers.get("page0", {}) or {}
    user_info = page0.get("userInfo", {}) or {}
    request_info = page0.get("requestInfo", {}) or {}
    reception_info = page0.get("receptionInfo", {}) or {}
    assessment = page0.get("assessment", {}) or {}
    interview = page0.get("interview", {}) or {}
    closing = page0.get("closing", {}) or {}

    office_id = get_by_path(payload.answers, "_meta.facilityId")
    personal_id = get_by_path(payload.answers, "_meta.personId")
    if not office_id or not personal_id:
        parsed_office_id, parsed_personal_id = parse_office_and_personal(payload.userId)
        office_id = office_id or parsed_office_id
        personal_id = personal_id or parsed_personal_id

    birth_year, birth_month, birth_day = split_date_ymd(user_info.get("birthDate", ""))
    reception_year, reception_month, reception_day = split_date_ymd(reception_info.get("receptionDate", ""))
    end_year, end_month, end_day = split_date_ymd(closing.get("endDate", ""))

    event_dates = {}
    for event in assessment.get("events", []) or []:
        reason = event.get("reason")
        event_dates[reason] = split_date_ymd(event.get("date", ""))

    first_y, first_m, first_d = event_dates.get("初回", (None, None, None))
    regular_y, regular_m, regular_d = event_dates.get("定期継続評価", (None, None, None))
    worsen_y, worsen_m, worsen_d = event_dates.get("状態悪化", (None, None, None))
    discharge_y, discharge_m, discharge_d = event_dates.get("退院", (None, None, None))
    admission_y, admission_m, admission_d = event_dates.get("入院", (None, None, None))

    sex = user_info.get("sex", "")
    request_route = request_info.get("requestRoute", "")
    reception_method = reception_info.get("method", "")
    participants = interview.get("participants", []) or []
    location = interview.get("location", "")
    response24h = interview.get("response24h", {}) or {}

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
        "request_organization": request_info.get("organization") or None,
        "requestor_name": request_info.get("requestorName") or None,
        "requestor_tel": request_info.get("requestorTel") or None,
        "requestor_fax": request_info.get("requestorFax") or None,
        "requestor_email": request_info.get("requestorEmail") or None,
        "reception_year": reception_year,
        "reception_month": reception_month,
        "reception_day": reception_day,
        "reception_hour": to_int_or_none(get_by_path(reception_info, "receptionTime.hour")),
        "reception_minute": to_int_or_none(get_by_path(reception_info, "receptionTime.minute")),
        "reception_staff": reception_info.get("staff") or None,
        "reception_method_document": onehot_equals(reception_method, "書面"),
        "reception_method_fax": onehot_equals(reception_method, "Fax"),
        "reception_method_meeting": onehot_equals(reception_method, "面会"),
        "reception_method_mail": onehot_equals(reception_method, "mail"),
        "reception_method_phone": onehot_equals(reception_method, "電話"),
        "reception_method_other": onehot_equals(reception_method, "その他"),
        "request_reason": reception_info.get("reason") or None,
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
        "interview_location_other_text": interview.get("locationOther") or None,
        "cm_24h_no": onehot_equals(response24h.get("cm"), "0"),
        "cm_24h_yes": onehot_equals(response24h.get("cm"), "1"),
        "kaigo_24h_no": onehot_equals(response24h.get("care"), "0"),
        "kaigo_24h_yes": onehot_equals(response24h.get("care"), "1"),
        "kangoshi_24h_no": onehot_equals(response24h.get("nurse"), "0"),
        "kangoshi_24h_yes": onehot_equals(response24h.get("nurse"), "1"),
        "end_year": end_year,
        "end_month": end_month,
        "end_day": end_day,
        "summary_recorder": closing.get("summaryRecorder") or None,
        "exit_summary": closing.get("exitSummary") or None,
        "last_saved_kind": save_kind,
        "final_submitted_at": now_str if save_kind == "final" else None,
        "updated_at": now_str,
    }


def upsert_form0_legacy(row: dict):
    # 同じ user_id + 回数 の行があれば上書き、なければ新規追加
    columns = list(row.keys())
    placeholders = ", ".join(["?"] * len(columns))
    update_expressions = []
    for col in columns:
        if col in ("user_id", "assessment_round"):
            continue
        if col == "final_submitted_at":
            # /save のときは NULL が来るため、既存の確定時刻を保持する
            update_expressions.append(f"{col}=COALESCE(excluded.{col}, form0_legacy.{col})")
        else:
            update_expressions.append(f"{col}=excluded.{col}")
    updates = ", ".join(update_expressions)
    sql = f"""
    INSERT INTO form0_legacy ({", ".join(columns)})
    VALUES ({placeholders})
    ON CONFLICT(user_id, assessment_round) DO UPDATE SET
    {updates}
    """
    values = [row[col] for col in columns]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(sql, values)


@app.on_event("startup")
async def startup():
    init_db()


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
    with sqlite3.connect(DB_PATH) as conn:
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
