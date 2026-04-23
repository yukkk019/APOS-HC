"""
column_display_text.csv の文言を need_rules_schema.csv の confidence_note に反映する。
(need_id, column_name) が (need_id, if_column) と一致する行のみ更新する。
同一キーが CSV に複数ある場合は最後の行の display_text を使用する。
"""
import csv
from pathlib import Path

def main():
    base = Path(__file__).resolve().parent
    display_path = base / "column_display_text.csv"
    schema_path = base / "spec" / "need_rules_schema.csv"

    # (need_id, column_name) -> display_text（文言はそのまま、末尾改行のみ除去）
    by_key: dict[tuple[str, str], str] = {}
    with open(display_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            need_id = (row.get("need_id") or "").strip()
            col = (row.get("column_name") or "").strip()
            text = (row.get("display_text") or "").replace("\r\n", "\n").rstrip("\n")
            if need_id and col:
                by_key[(need_id, col)] = text

    # need_rules_schema を読み、confidence_note を上書き
    with open(schema_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    updated = 0
    for row in rows:
        need_id = (row.get("need_id") or "").strip()
        if_col = (row.get("if_column") or "").strip()
        key = (need_id, if_col)
        if key in by_key:
            row["confidence_note"] = by_key[key]
            updated += 1

    with open(schema_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated} rows in need_rules_schema.csv (from column_display_text.csv)")

if __name__ == "__main__":
    main()
