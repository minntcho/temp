"""다중 출처 E(환경) 원시데이터를 표준 스키마로 정규화.

입력:
- erp_energy.csv
- supplier_fuel_sheet.csv
- field_notes.txt
- email_dump.jsonl

출력:
- unified_raw_staging.csv
- parse_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ACTIVITY_MAP = {
    "electricity": "electricity",
    "전력": "electricity",
    "diesel": "diesel",
    "디젤": "diesel",
    "natural_gas": "natural_gas",
    "천연가스": "natural_gas",
    "steam": "steam",
    "스팀": "steam",
}

UNIT_MAP = {
    "kWh": ("kWh", 1.0),
    "MWh": ("kWh", 1000.0),
    "L": ("L", 1.0),
    "gallon": ("L", 3.78541),
    "Nm3": ("Nm3", 1.0),
    "m3": ("Nm3", 1.0),
    "kg": ("ton", 0.001),
    "ton": ("ton", 1.0),
}


def normalize_unit(amount: float, unit: str):
    if unit not in UNIT_MAP:
        return "", "", "failed", "unknown_unit"
    std_unit, mult = UNIT_MAP[unit]
    return std_unit, round(amount * mult, 6), "ok", ""


def parse_erp(path: Path):
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            activity = ACTIVITY_MAP.get(r["energy_kind"], "")
            amount = float(r["qty"])
            std_unit, std_amount, status, note = normalize_unit(amount, r["uom"])
            rows.append(
                {
                    "source_type": "erp_csv",
                    "source_ref": path.name,
                    "raw_text": "",
                    "site": r["plant_name"],
                    "period": r["work_dt"][:7],
                    "activity_type": activity,
                    "raw_amount": amount,
                    "raw_unit": r["uom"],
                    "standardized_amount": std_amount,
                    "standardized_unit": std_unit,
                    "parse_method": "rule",
                    "confidence": 0.95,
                    "status": "ok" if activity and status == "ok" else "failed",
                    "note": note if activity else "unknown_activity",
                }
            )
    return rows


def parse_supplier(path: Path):
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            activity = ACTIVITY_MAP.get(r["항목"], "")
            amount = float(r["사용량"])
            std_unit, std_amount, status, note = normalize_unit(amount, r["단위"])
            rows.append(
                {
                    "source_type": "supplier_sheet_csv",
                    "source_ref": path.name,
                    "raw_text": "",
                    "site": r["사업장"],
                    "period": r["기준월"],
                    "activity_type": activity,
                    "raw_amount": amount,
                    "raw_unit": r["단위"],
                    "standardized_amount": std_amount,
                    "standardized_unit": std_unit,
                    "parse_method": "rule",
                    "confidence": 0.9,
                    "status": "ok" if activity and status == "ok" else "failed",
                    "note": note if activity else "unknown_activity",
                }
            )
    return rows


def parse_text_line(line: str):
    # site
    site_match = re.search(r"(울산공장|평택공장|인천물류센터|서울사무소)", line)
    period_match = re.search(r"(20\d{2}[-/]\d{2})", line)
    activity_match = re.search(r"(전력|디젤|스팀|천연가스|electricity|diesel|steam|natural_gas)", line)
    amount_unit_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(MWh|kWh|gallon|L|kg|ton|Nm3|m3)", line)

    site = site_match.group(1) if site_match else ""
    period = period_match.group(1).replace("/", "-") if period_match else ""
    activity = ACTIVITY_MAP.get(activity_match.group(1), "") if activity_match else ""

    if amount_unit_match:
        amount = float(amount_unit_match.group(1))
        unit = amount_unit_match.group(2)
    else:
        amount, unit = 0.0, ""

    std_unit, std_amount, status, note = normalize_unit(amount, unit) if unit else ("", "", "failed", "amount_or_unit_not_found")
    ok = bool(site and period and activity and status == "ok")

    return {
        "site": site,
        "period": period,
        "activity_type": activity,
        "raw_amount": amount,
        "raw_unit": unit,
        "standardized_amount": std_amount,
        "standardized_unit": std_unit,
        "status": "ok" if ok else "failed",
        "note": "" if ok else note or "semantic_parse_failed",
    }


def parse_field_notes(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_text_line(line)
        parsed.update(
            {
                "source_type": "field_notes_txt",
                "source_ref": path.name,
                "raw_text": line,
                "parse_method": "regex+heuristic",
                "confidence": 0.7 if parsed["status"] == "ok" else 0.3,
            }
        )
        rows.append(parsed)
    return rows


def parse_email_dump(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        parsed = parse_text_line(obj.get("body", ""))
        parsed.update(
            {
                "source_type": "email_jsonl",
                "source_ref": obj.get("mail_id", ""),
                "raw_text": obj.get("body", ""),
                "parse_method": "regex+heuristic",
                "confidence": 0.75 if parsed["status"] == "ok" else 0.35,
            }
        )
        rows.append(parsed)
    return rows


def write_csv(path: Path, rows):
    if not rows:
        raise ValueError("no rows")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="다중 출처 ESG 원시데이터 표준화")
    p.add_argument("--in-dir", type=Path, default=Path("raw_multisource"))
    p.add_argument("--out-dir", type=Path, default=Path("raw_multisource"))
    args = p.parse_args()

    all_rows = []
    all_rows.extend(parse_erp(args.in_dir / "erp_energy.csv"))
    all_rows.extend(parse_supplier(args.in_dir / "supplier_fuel_sheet.csv"))
    all_rows.extend(parse_field_notes(args.in_dir / "field_notes.txt"))
    all_rows.extend(parse_email_dump(args.in_dir / "email_dump.jsonl"))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / "unified_raw_staging.csv"
    write_csv(out_csv, all_rows)

    report = {
        "total": len(all_rows),
        "ok": sum(1 for r in all_rows if r["status"] == "ok"),
        "failed": sum(1 for r in all_rows if r["status"] == "failed"),
        "by_source": {
            "erp_csv": sum(1 for r in all_rows if r["source_type"] == "erp_csv"),
            "supplier_sheet_csv": sum(1 for r in all_rows if r["source_type"] == "supplier_sheet_csv"),
            "field_notes_txt": sum(1 for r in all_rows if r["source_type"] == "field_notes_txt"),
            "email_jsonl": sum(1 for r in all_rows if r["source_type"] == "email_jsonl"),
        },
    }
    (args.out_dir / "parse_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] unified staging saved: {out_csv}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
