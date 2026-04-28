# ============================================================
# submit_server の SQLite（form0_legacy 等）から newneed 用データを取得
# ============================================================

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

# submit_server.get_db_connection と揃えたロック対策（定数のみ重複）
_SQLITE_TIMEOUT_SEC = 15.0
_SQLITE_BUSY_MS = 15000


def _db_path() -> Path:
    env = os.environ.get("APOS_HC_DB_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "apos_hc.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    conn = sqlite3.connect(str(path), timeout=_SQLITE_TIMEOUT_SEC)
    conn.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_MS}")
    return conn


def get_record_db(user_id: str, assessment_round: str) -> dict[str, Any] | None:
    """
    form0_legacy の1行をフラット dict として返す（need ルール評価用）。
    レコードが無い場合は None。
    """
    uid = (user_id or "").strip()
    if not uid:
        return None
    try:
        r = int(str(assessment_round).strip())
    except (ValueError, TypeError):
        r = 1
    path = _db_path()
    if not path.is_file():
        return None
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM form0_legacy WHERE user_id = ? AND assessment_round = ?",
            (uid, r),
        ).fetchone()
    if not row:
        return None
    return {k: row[k] for k in row.keys()}


def _ensure_care_plan_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS newneed_care_plans (
            user_id TEXT NOT NULL,
            assessment_round TEXT NOT NULL,
            need_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, assessment_round, need_id)
        )
        """
    )


def get_care_plan_db(user_id: str, assessment_round: str, need_id: str) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    r = (assessment_round or "").strip()
    nid = (need_id or "").strip()
    if not uid or not r or not nid:
        return None
    path = _db_path()
    if not path.is_file():
        return None
    with _connect() as conn:
        _ensure_care_plan_table(conn)
        row = conn.execute(
            """
            SELECT payload_json FROM newneed_care_plans
            WHERE user_id = ? AND assessment_round = ? AND need_id = ?
            """,
            (uid, r, nid),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def get_care_plans_for_user_round_db(user_id: str, assessment_round: str) -> list[dict[str, Any]]:
    """将来用・現状は未使用。"""
    return []


def upsert_care_plan_db(
    uid: str,
    assessment_round: str,
    need_id: str,
    care_plan_text: str,
    support_methods: str,
    change_from_previous: str,
    *,
    care_goal: str = "",
    change_level: str = "",
    change_contents: str = "",
    plans_json: str = "",
    question_evaluations_json: str = "",
    care_evaluations_json: str = "",
) -> None:
    uid = (uid or "").strip()
    r = (assessment_round or "").strip()
    nid = (need_id or "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    qe: list[Any] = []
    ce: list[Any] = []
    try:
        if question_evaluations_json:
            qe = json.loads(question_evaluations_json)
        if care_evaluations_json:
            ce = json.loads(care_evaluations_json)
    except Exception:
        pass

    care_plans: list[Any] | None = None
    if plans_json:
        try:
            parsed = json.loads(plans_json)
            care_plans = parsed if isinstance(parsed, list) else []
        except Exception:
            care_plans = []

    payload: dict[str, Any] = {
        "care_goal": care_goal or "",
        "care_plan_text": care_plan_text or "",
        "support_methods": support_methods or "",
        "change_from_previous": change_from_previous or "",
        "change_level": change_level or "",
        "change_contents": change_contents or "",
        "updated_at": now,
        "question_evaluations": qe if isinstance(qe, list) else [],
        "care_evaluations": ce if isinstance(ce, list) else [],
    }
    if care_plans is not None:
        payload["care_plans"] = care_plans

    with _connect() as conn:
        _ensure_care_plan_table(conn)
        conn.execute(
            """
            INSERT INTO newneed_care_plans (user_id, assessment_round, need_id, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, assessment_round, need_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (uid, r, nid, json.dumps(payload, ensure_ascii=False), now),
        )
        conn.commit()
