# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(__file__).with_name("submit_server.py")
text = path.read_text(encoding="utf-8")

if "def ensure_form11_columns" in text:
    print("form11 already present")
    raise SystemExit(0)

cols = []
for letter in "abcdefgh":
    cols.append((f"m11_nutrition_self_{letter}", "INTEGER"))
for i in range(5):
    cols.append((f"emotion_level_{i}", "INTEGER"))
for n in range(1, 9):
    cols.append((f"m_health_{n}_1", "INTEGER"))
    cols.append((f"m_health_{n}_2", "INTEGER"))
cols.append(("m_health_8_detail", "TEXT"))
cols.append(("a_positive_count", "INTEGER"))

lines = ["def ensure_form11_columns(conn: sqlite3.Connection):", "    columns = ["]
for name, typ in cols:
    lines.append(f'        ("{name}", "{typ}"),')
lines.append("    ]")
lines.append("    for column_name, column_type in columns:")
lines.append('        ensure_column_exists(conn, "form0_legacy", column_name, column_type)')
ensure_fn = "\n".join(lines)

map_fn = r'''
def map_page11_to_form11_columns(page11: dict) -> dict:
    cog = (page11.get("cognitiveStatus") or {}) or {}
    rank = str(cog.get("independenceRank") or "")

    hl = (page11.get("healthLiteracy") or {}) or {}
    el = str(hl.get("emotionLevel") or "")

    dep = (page11.get("depressiveState") or {}) or {}

    out: dict = {}
    for letter in "abcdefgh":
        out[f"m11_nutrition_self_{letter}"] = onehot_equals(
            rank, f"nutrition_self_management_{letter}"
        )
    for i in range(5):
        out[f"emotion_level_{i}"] = onehot_equals(el, str(i))
    for n in range(1, 9):
        qv = str(dep.get(f"q{n}") or "")
        out[f"m_health_{n}_1"] = onehot_equals(qv, f"m_health_{n}_1")
        out[f"m_health_{n}_2"] = onehot_equals(qv, f"m_health_{n}_2")
    out["m_health_8_detail"] = normalize_text(dep.get("q8Detail"))
    out["a_positive_count"] = to_int_or_none(dep.get("aPositiveCount"))
    return out
'''

block = "\n" + ensure_fn + "\n" + map_fn

anchor = (
    '        out[f"visual_condition_{letter}"] = onehot_in(cond_detail, letter)\n'
    "\n"
    "    return out\n"
    "\n"
    "def ensure_form1_columns(conn: sqlite3.Connection):"
)
if anchor not in text:
    raise SystemExit("anchor not found for form11")
text = text.replace(
    anchor,
    '        out[f"visual_condition_{letter}"] = onehot_in(cond_detail, letter)\n'
    "\n"
    "    return out"
    + block
    + "\ndef ensure_form1_columns(conn: sqlite3.Connection):",
    1,
)

text = text.replace(
    "        ensure_form10_columns(conn)\n",
    "        ensure_form10_columns(conn)\n        ensure_form11_columns(conn)\n",
    1,
)
text = text.replace(
    "    form10_cols = map_page10_to_form10_columns(page10)\n",
    '    form10_cols = map_page10_to_form10_columns(page10)\n'
    '    page11 = payload.answers.get("page11", {}) or {}\n'
    "    form11_cols = map_page11_to_form11_columns(page11)\n",
    1,
)
text = text.replace("        **form10_cols,\n", "        **form10_cols,\n        **form11_cols,\n", 1)

path.write_text(text, encoding="utf-8", newline="\n")
print("form11 ok, columns:", len(cols))
