# ============================================================
# newneed API ルーター
# ------------------------------------------------------------
# 23項目（N01–N23）に紐づくカラムのうち、
# 値が「1が立った」ものだけ項目名と該当内容を表示するAPI
# ============================================================

import csv
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from core.storage_db import get_record_db, get_care_plan_db, get_care_plans_for_user_round_db, upsert_care_plan_db

router = APIRouter()

# ------------------------------------------------------------
# パス解決（newneed/spec を参照）
# ------------------------------------------------------------
def _spec_dir() -> Path:
    return Path(__file__).resolve().parent / "spec"


def _newneed_data_dir() -> Path:
    return Path(__file__).resolve().parent


# ------------------------------------------------------------
# ニーズマスター読み込み（need_id -> need_name_jp）
# ------------------------------------------------------------
def _load_needs_master() -> dict[str, str]:
    path = _spec_dir() / "needs_master_schema.csv"
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nid = (row.get("need_id") or "").strip()
                name = (row.get("need_name_jp") or "").strip()
                if nid:
                    out[nid] = name
    except Exception:
        pass
    return out


# ------------------------------------------------------------
# ニーズルール読み込み（need_id -> [(column, operator, target_value, confidence_note)])
# ------------------------------------------------------------
def _load_need_rules() -> dict[str, list[tuple[str, str, str, str]]]:
    path = _spec_dir() / "need_rules_schema.csv"
    out: dict[str, list[tuple[str, str, str, str]]] = {}
    if not path.exists():
        return out
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nid = (row.get("need_id") or "").strip()
                col = (row.get("if_column") or "").strip()
                op = (row.get("operator") or "").strip()
                tv = (row.get("target_value") or "").strip()
                note = (row.get("confidence_note") or "").strip()
                if nid and col:
                    out.setdefault(nid, []).append((col, op, tv, note))
    except Exception:
        pass
    return out


# ------------------------------------------------------------
# カラム表示文言読み込み（(need_id, column_name) および column_name -> display_text）
# 文言・半角スペースは CSV の記載をそのまま使う（strip しない）
# ------------------------------------------------------------
def _load_column_display_text() -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    path = _newneed_data_dir() / "column_display_text.csv"
    by_need_col: dict[tuple[str, str], str] = {}
    by_col: dict[str, str] = {}
    if not path.exists():
        return by_need_col, by_col
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                need_id = (row.get("need_id") or "").strip()
                col = (row.get("column_name") or "").strip()
                # 表示文言は CSV の記載をそのまま使用（半角スペース等を保持）
                text = (row.get("display_text") or "").replace("\r\n", "\n")
                if col:
                    if need_id:
                        by_need_col[(need_id, col)] = text
                    by_col[col] = text
    except Exception:
        pass
    return by_need_col, by_col


# ------------------------------------------------------------
# ルールに合致するか（レコードの値で判定）
# ------------------------------------------------------------
def _value_matches(record_value: Any, operator: str, target_value: str) -> bool:
    s = str(record_value).strip() if record_value is not None else ""
    op = (operator or "").strip().lower()
    tv = (target_value or "").strip()

    if op == "==":
        if tv == "1":
            return s in ("1", "true", "True", "on", "yes", "あり")
        return s == tv

    if op == ">=":
        try:
            num = float(s) if s else 0
            th = float(tv) if tv else 0
            return num >= th
        except ValueError:
            return False

    if op == "<=":
        try:
            num = float(s) if s else 0
            th = float(tv) if tv else 0
            return num <= th
        except ValueError:
            return False

    # between: target_value は "min,max" 形式（例: "1,70" で 1～70 のとき True）
    if op == "between":
        parts = [p.strip() for p in tv.split(",")]
        if len(parts) != 2:
            return False
        try:
            num = float(s) if s else 0
            lo = float(parts[0]) if parts[0] else 0
            hi = float(parts[1]) if parts[1] else 0
            return lo <= num <= hi
        except ValueError:
            return False

    if op == "contains":
        return tv in s

    # != : 空文字との比較で「値がある」判定（テキスト列の表示用）
    if op == "!=":
        if tv == "" or tv == '""':
            return bool(s)
        return s != tv

    return False


# ------------------------------------------------------------
# 23項目表示用データを構築
# ------------------------------------------------------------
def build_display_items(
    record: dict[str, Any],
    needs_master: dict[str, str],
    need_rules: dict[str, list[tuple[str, str, str, str]]],
    column_display_text: tuple[dict[tuple[str, str], str], dict[str, str]],
) -> list[dict[str, Any]]:
    """
    レコードに対して、値が「1が立った」ニーズだけを抽出し、
    need_id, need_name_jp, contents (column + display_text) のリストを返す。
    表示文言は column_display_text.csv を優先（文言・半角スペースは CSV の通り）。
    """
    by_need_col, by_col = column_display_text
    result: list[dict[str, Any]] = []
    need_ids = [f"N{i:02d}" for i in range(1, 24)]

    for need_id in need_ids:
        rules = need_rules.get(need_id, [])
        contents: list[dict[str, str]] = []

        for col, operator, target_value, confidence_note in rules:
            val = record.get(col)
            if not _value_matches(val, operator, target_value):
                continue
            # GAFスコア: 入った点数を帯（1～9, 10～19, …, 60～70）で表示
            if col == "gaf_score" and val is not None:
                try:
                    n = int(float(str(val)))
                    if 1 <= n <= 9:
                        band_key = "gaf_score_1_9"
                    elif 10 <= n <= 19:
                        band_key = "gaf_score_10_19"
                    elif 20 <= n <= 29:
                        band_key = "gaf_score_20_29"
                    elif 30 <= n <= 39:
                        band_key = "gaf_score_30_39"
                    elif 40 <= n <= 49:
                        band_key = "gaf_score_40_49"
                    elif 50 <= n <= 59:
                        band_key = "gaf_score_50_59"
                    elif 60 <= n <= 70:
                        band_key = "gaf_score_60_70"
                    else:
                        band_key = None
                    if band_key:
                        display_text = (
                            by_need_col.get((need_id, band_key)) or by_col.get(band_key)
                            or (confidence_note or "").strip()
                            or col
                        )
                        contents.append({"column": col, "display_text": display_text})
                except (ValueError, TypeError):
                    display_text = (
                        by_need_col.get((need_id, col)) or by_col.get(col)
                        or (confidence_note or "").strip()
                        or col
                    )
                    contents.append({"column": col, "display_text": display_text})
                continue
            # 表示文言: column_display_text.csv を唯一の正とする（(need_id,col)→col の順で参照し、なければ schema の confidence_note）
            display_text = (
                by_need_col.get((need_id, col)) or by_col.get(col)
                or (confidence_note or "").strip()
                or col
            )
            # 記述欄：記入した内容を表示する（ラベル：値）
            _freewrite_cols = (
                "dementia_other", "cancer_other", "circulatory_freewrite_input",
                "bone_other", "leg_circulation_freewrite_input", "doctor_diagnosis_note",
            )
            if col in _freewrite_cols and val is not None:
                v = str(val).strip()
                if v:
                    display_text = display_text + "：" + v
            contents.append({"column": col, "display_text": display_text})

        # N15/N16: うつ関連5項目のうち2つ以上該当したら「うつ的状態が２項目以上」を追加
        if need_id in ("N15", "N16"):
            _m_health_cols = ("m_health_1_2", "m_health_2_2", "m_health_3_1", "m_health_4_2", "m_health_5_1")
            count = sum(1 for c in _m_health_cols if _value_matches(record.get(c), "==", "1"))
            if count >= 2:
                summary_col = "m_health_depressive_2plus"
                summary_text = (
                    by_need_col.get((need_id, summary_col)) or by_col.get(summary_col)
                    or "うつ的状態が２項目以上"
                )
                contents.append({"column": summary_col, "display_text": summary_text})

        if contents:
            result.append({
                "need_id": need_id,
                "need_name_jp": needs_master.get(need_id, need_id),
                "contents": contents,
            })

    return result


def build_assessment_history(
    uid: str,
    need_id: str,
    need_item: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    同一 need_id について、1〜3回目のアセス該当 display_text を column キーで突合したリスト。
    各要素: {"column": str, "rounds": {"1"|"2"|"3": str | None}}
    """
    needs_master, need_rules, column_display_text = _get_masters()
    per_round: dict[str, dict[str, str]] = {"1": {}, "2": {}, "3": {}}
    for r in (1, 2, 3):
        record = get_record_db(uid, str(r))
        if not record:
            continue
        items = build_display_items(record, needs_master, need_rules, column_display_text)
        ni = next((it for it in items if it["need_id"] == need_id), None)
        if not ni:
            continue
        for c in ni.get("contents") or []:
            col = (c.get("column") or "").strip()
            if col:
                per_round[str(r)][col] = c.get("display_text") or ""

    all_cols: set[str] = set()
    for d in per_round.values():
        all_cols.update(d.keys())

    ordered: list[str] = []
    seen: set[str] = set()
    for c in need_item.get("contents") or []:
        col = (c.get("column") or "").strip()
        if col and col not in seen and col in all_cols:
            ordered.append(col)
            seen.add(col)
    for col in sorted(all_cols - seen):
        ordered.append(col)

    out: list[dict[str, Any]] = []
    for col in ordered:
        rounds_out: dict[str, str | None] = {}
        for r in ("1", "2", "3"):
            rounds_out[r] = per_round[r].get(col)
        out.append({"column": col, "rounds": rounds_out})
    return out


def build_needs_by_round(uid: str) -> dict[str, list[dict[str, Any]]]:
    """
    1〜3回目それぞれで build_display_items に該当したニーズ領域の一覧。
    戻り: {"1"|"2"|"3": [{"need_id", "need_name_jp", "content_count"}, ...]}
    content_count はそのニーズ内の該当質問（contents 行）の件数。
    レコードが無い回はキーは残し値は空配列。
    """
    needs_master, need_rules, column_display_text = _get_masters()
    out: dict[str, list[dict[str, Any]]] = {"1": [], "2": [], "3": []}
    for r in (1, 2, 3):
        record = get_record_db(uid, str(r))
        if not record:
            continue
        items = build_display_items(record, needs_master, need_rules, column_display_text)
        out[str(r)] = [
            {
                "need_id": it["need_id"],
                "need_name_jp": (it.get("need_name_jp") or needs_master.get(it["need_id"], it["need_id"])),
                "content_count": len(it.get("contents") or []),
            }
            for it in items
        ]
    return out


def build_needs_comparison(uid: str) -> list[dict[str, Any]]:
    """
    いずれかの回に該当した need_id ごとに、1〜3回目の有無と該当質問件数を返す。
    """
    nbr = build_needs_by_round(uid)
    sets = {r: {it["need_id"] for it in nbr[r]} for r in ("1", "2", "3")}
    count_by_need_round: dict[str, dict[str, int]] = {}
    for r in ("1", "2", "3"):
        for it in nbr[r]:
            nid = it["need_id"]
            count_by_need_round.setdefault(nid, {"1": 0, "2": 0, "3": 0})
            count_by_need_round[nid][r] = int(it.get("content_count") or 0)
    all_ids: set[str] = set()
    for s in sets.values():
        all_ids |= s
    needs_master, _, _ = _get_masters()

    def _sort_key(nid: str) -> tuple[int, str]:
        s = (nid or "").strip()
        if len(s) >= 2 and s[0] == "N" and s[1:].isdigit():
            return (int(s[1:]), s)
        return (9999, s)

    rows: list[dict[str, Any]] = []
    for nid in sorted(all_ids, key=_sort_key):
        cc = count_by_need_round.get(nid, {"1": 0, "2": 0, "3": 0})
        rows.append(
            {
                "need_id": nid,
                "need_name_jp": needs_master.get(nid, nid),
                "present": {
                    "1": nid in sets["1"],
                    "2": nid in sets["2"],
                    "3": nid in sets["3"],
                },
                "content_count_by_round": {"1": cc["1"], "2": cc["2"], "3": cc["3"]},
            }
        )
    return rows


def build_total_question_counts(needs_by_round: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """各回で、全ニーズに含まれる該当質問の合計件数。"""
    out: dict[str, int] = {"1": 0, "2": 0, "3": 0}
    for r in ("1", "2", "3"):
        out[r] = sum(int(it.get("content_count") or 0) for it in needs_by_round.get(r) or [])
    return out


# ------------------------------------------------------------
# キャッシュ（起動時1回読み込み）
# ------------------------------------------------------------
_needs_master: dict[str, str] | None = None
_need_rules: dict[str, list[tuple[str, str, str, str]]] | None = None
_column_display_text: tuple[dict[tuple[str, str], str], dict[str, str]] | None = None


def _get_masters():
    global _needs_master, _need_rules, _column_display_text
    if _needs_master is None:
        _needs_master = _load_needs_master()
    if _need_rules is None:
        _need_rules = _load_need_rules()
    if _column_display_text is None:
        _column_display_text = _load_column_display_text()
    return _needs_master, _need_rules, _column_display_text


# ------------------------------------------------------------
# エンドポイント: GET / （ルート）
# ------------------------------------------------------------
@router.get("/")
async def newneed_root():
    return {"module": "newneed", "status": "ok"}


# ------------------------------------------------------------
# エンドポイント: GET /display（23項目表示用JSON）
# ------------------------------------------------------------
@router.get("/display")
async def display_needs(
    user_id: str | None = Query(None, description="ユーザーID（office_id_personal_id）"),
    office_id: str | None = Query(None, description="事業所ID"),
    personal_id: str | None = Query(None, description="個人ID"),
    round_num: int | None = Query(None, alias="round", description="評価回次 1/2/3"),
):
    uid = (user_id or "").strip()
    if not uid and (office_id or personal_id):
        oid = (office_id or "").strip()
        pid = (personal_id or "").strip()
        if oid and pid:
            uid = f"{oid}_{pid}"
    if not uid:
        raise HTTPException(status_code=400, detail="user_id または office_id と personal_id を指定してください")
    r = (round_num if round_num in (1, 2, 3) else 1)
    r_str = str(r)

    # レコード取得（DBのみ）
    record = get_record_db(uid, r_str)
    if record is None:
        raise HTTPException(status_code=404, detail="指定条件のレコードが見つかりません")

    needs_master, need_rules, column_display_text = _get_masters()
    items = build_display_items(record, needs_master, need_rules, column_display_text)

    return {
        "user_id": uid,
        "assessment_round": r_str,
        "items": items,
    }


# ------------------------------------------------------------
# エンドポイント: GET /display/overview（1〜3回のニーズ領域サマリ・比較用）
# ------------------------------------------------------------
@router.get("/display/overview")
async def display_needs_overview(
    user_id: str | None = Query(None, description="ユーザーID（office_id_personal_id）"),
    office_id: str | None = Query(None, description="事業所ID"),
    personal_id: str | None = Query(None, description="個人ID"),
):
    """レコードの有無に関わらず、取得できた回のニーズ一覧と比較行を返す（空配列可）。"""
    uid = (user_id or "").strip()
    if not uid and (office_id or personal_id):
        oid = (office_id or "").strip()
        pid = (personal_id or "").strip()
        if oid and pid:
            uid = f"{oid}_{pid}"
    if not uid:
        raise HTTPException(status_code=400, detail="user_id または office_id と personal_id を指定してください")

    needs_by_round = build_needs_by_round(uid)
    needs_comparison = build_needs_comparison(uid)
    total_question_counts = build_total_question_counts(needs_by_round)
    payload = {
        "user_id": uid,
        "needs_by_round": needs_by_round,
        "needs_comparison": needs_comparison,
        "total_question_counts": total_question_counts,
    }
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"Cache-Control": "no-store"},
    )


# ------------------------------------------------------------
# エンドポイント: GET /page（表示画面へリダイレクト）
# ------------------------------------------------------------
@router.get("/page")
async def display_page():
    """HTML/CSS で作った表示画面（display.html）へリダイレクト"""
    return RedirectResponse(url="/api/newneed/static/display.html", status_code=302)


# ------------------------------------------------------------
# 看護計画書：フォーム用データ（該当内容 + 既存計画）
# ------------------------------------------------------------
@router.get("/care-plan/form")
async def care_plan_form(
    user_id: str | None = Query(None),
    office_id: str | None = Query(None),
    personal_id: str | None = Query(None),
    round_num: int | None = Query(None, alias="round"),
    need_id: str = Query(..., description="N01～N23"),
):
    uid = (user_id or "").strip()
    if not uid and (office_id or personal_id):
        oid = (office_id or "").strip()
        pid = (personal_id or "").strip()
        if oid and pid:
            uid = f"{oid}_{pid}"
    if not uid:
        raise HTTPException(status_code=400, detail="user_id または office_id と personal_id を指定してください")
    r = (round_num if round_num in (1, 2, 3) else 1)
    r_str = str(r)
    nid = (need_id or "").strip()
    if not nid or not nid.startswith("N"):
        raise HTTPException(status_code=400, detail="need_id は N01～N23 を指定してください")

    record = get_record_db(uid, r_str)
    if record is None:
        raise HTTPException(status_code=404, detail="指定条件のレコードが見つかりません")

    needs_master, need_rules, column_display_text = _get_masters()
    items = build_display_items(record, needs_master, need_rules, column_display_text)
    need_item = next((it for it in items if it["need_id"] == nid), None)
    if need_item is None:
        need_item = {
            "need_id": nid,
            "need_name_jp": needs_master.get(nid, nid),
            "contents": [],
        }

    existing = get_care_plan_db(uid, r_str, nid)
    default_care_plan = {
        "care_goal": "",
        "care_plan_text": "",
        "support_methods": "",
        "change_level": "",
        "change_contents": "",
        "change_from_previous": "",
        "updated_at": "",
        "question_evaluations": [],
        "care_evaluations": [],
    }
    care_plan_out = existing or default_care_plan
    if care_plan_out is existing and existing is not None:
        if "question_evaluations" not in existing:
            existing["question_evaluations"] = []
        if "care_evaluations" not in existing:
            existing["care_evaluations"] = []
    nbr = build_needs_by_round(uid)
    resp = {
        "user_id": uid,
        "assessment_round": r_str,
        "need_id": nid,
        "need_item": need_item,
        "care_plan": care_plan_out,
        "assessment_history": build_assessment_history(uid, nid, need_item),
        "needs_by_round": nbr,
        "total_question_counts": build_total_question_counts(nbr),
    }
    if existing and existing.get("care_plans"):
        resp["care_plans"] = existing["care_plans"]
    return JSONResponse(
        content=jsonable_encoder(resp),
        headers={"Cache-Control": "no-store"},
    )


class CarePlanBody(BaseModel):
    user_id: str
    assessment_round: str
    need_id: str
    care_plan_text: str = ""
    support_methods: str = ""
    change_from_previous: str = ""
    care_goal: str = ""
    change_level: str = ""
    change_contents: str = ""
    care_plans: list[dict] | None = None  # 複数計画 [{ care_goal, care_plan_text, support_methods }, ...]
    care_evaluations: list[dict] | None = None  # ケア行ごとの評価
    question_evaluations: list[dict] | None = None  # 質問項目ごとの経過（任意）[{ column, trend, note }, ...]


# ------------------------------------------------------------
# 看護計画書：保存
# ------------------------------------------------------------
@router.post("/care-plan")
async def care_plan_save(body: CarePlanBody):
    import json
    uid = (body.user_id or "").strip()
    r = (body.assessment_round or "").strip()
    nid = (body.need_id or "").strip()
    if not uid or not r or not nid:
        raise HTTPException(status_code=400, detail="user_id, assessment_round, need_id は必須です")

    care_goal = body.care_goal or ""
    care_plan_text = body.care_plan_text or ""
    support_methods = body.support_methods or ""
    plans_json = ""

    if body.care_plans and len(body.care_plans) > 0:
        plans_json = json.dumps(body.care_plans, ensure_ascii=False)
        goals = []
        texts = []
        support_set = set()
        for i, p in enumerate(body.care_plans):
            goal = (p.get("care_goal") or "").strip()
            text = (p.get("care_plan_text") or "").strip()
            if goal:
                goals.append("【計画" + str(i + 1) + "】\n" + goal)
            for line in (text or "").splitlines():
                line = (line or "").strip()
                if line:
                    texts.append("・" + line)
            for s in (p.get("support_methods") or "").replace("、", ",").split(","):
                s = (s or "").strip()
                if s:
                    support_set.add(s)
        care_goal = "\n\n".join(goals) if goals else care_goal
        care_plan_text = "\n".join(texts) if texts else care_plan_text
        support_methods = ",".join(sorted(support_set)) if support_set else support_methods

    qe_json = ""
    if body.question_evaluations is not None:
        qe_json = json.dumps(body.question_evaluations, ensure_ascii=False)
    ce_json = ""
    if body.care_evaluations is not None:
        ce_json = json.dumps(body.care_evaluations, ensure_ascii=False)

    upsert_care_plan_db(
        uid,
        r,
        nid,
        care_plan_text,
        support_methods,
        body.change_from_previous or "",
        care_goal=care_goal,
        change_level=body.change_level or "",
        change_contents=body.change_contents or "",
        plans_json=plans_json,
        question_evaluations_json=qe_json,
        care_evaluations_json=ce_json,
    )
    return {"ok": True, "message": "看護計画を保存しました"}
