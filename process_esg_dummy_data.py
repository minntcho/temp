"""ESG 더미 데이터 처리기 (정책 적용 전용).

입력(생성기 산출물)
- activity_raw.csv
- unit_conversions.csv
- emission_factors.csv

출력
- activity_normalized.csv
- activity_emissions.csv
- processing_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def normalize_activity_units(raw_rows: list[dict[str, str]], conversion_rules: list[dict[str, str]]) -> list[dict[str, str | float]]:
    profile_std = {
        "electricity": "kWh",
        "diesel": "L",
        "natural_gas": "Nm3",
        "steam": "ton",
    }
    rule_map = {(r["activity_type"], r["from_unit"]): r for r in conversion_rules}

    out: list[dict[str, str | float]] = []
    for r in raw_rows:
        activity_type = r["activity_type"]
        raw_unit = r["raw_unit"]
        raw_amount = float(r["raw_amount"])
        target_unit = profile_std.get(activity_type, raw_unit)

        conversion_id = ""
        conversion_status = "failed"
        conversion_note = ""
        standardized_amount = ""

        if raw_amount < 0:
            conversion_status = "failed"
            conversion_note = "negative_amount"
        elif raw_unit == target_unit:
            conversion_status = "already_standard"
            standardized_amount = round(raw_amount, 6)
        else:
            rule = rule_map.get((activity_type, raw_unit))
            if rule is None:
                conversion_status = "failed"
                conversion_note = "no_conversion_rule"
            else:
                conversion_id = rule["conversion_id"]
                standardized_amount = round(raw_amount * float(rule["multiplier"]) + float(rule["offset"]), 6)
                conversion_status = "converted"

        out.append(
            {
                "activity_id": r["activity_id"],
                "activity_type": activity_type,
                "raw_unit": raw_unit,
                "raw_amount": raw_amount,
                "standardized_unit": target_unit,
                "standardized_amount": standardized_amount,
                "conversion_id": conversion_id,
                "conversion_status": conversion_status,
                "conversion_note": conversion_note,
            }
        )

    return out


def calculate_activity_emissions(raw_rows: list[dict[str, str]], normalized_rows: list[dict[str, str | float]], factors: list[dict[str, str]]) -> list[dict[str, str | float]]:
    factor_map = {(f["activity_type"], f["unit"]): f for f in factors}
    raw_map = {r["activity_id"]: r for r in raw_rows}

    out: list[dict[str, str | float]] = []
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    for n in normalized_rows:
        activity_id = str(n["activity_id"])
        raw = raw_map[activity_id]

        standardized_amount = n["standardized_amount"]
        calculation_status = "failed"
        excluded_from_reporting = "N"
        exclusion_reason = ""
        factor_id = ""
        applied_factor = ""
        factor_unit = ""
        co2e_kg = ""

        if standardized_amount == "":
            exclusion_reason = "conversion_failed"
        elif raw["reporting_included"] == "N":
            calculation_status = "excluded"
            excluded_from_reporting = "Y"
            exclusion_reason = "reporting_boundary_excluded"
        else:
            factor = factor_map.get((str(n["activity_type"]), str(n["standardized_unit"])))
            if factor is None:
                exclusion_reason = "factor_not_found"
            else:
                factor_id = factor["factor_id"]
                applied_factor = float(factor["emission_factor"])
                factor_unit = factor["factor_unit"]
                co2e_kg = round(float(standardized_amount) * applied_factor, 6)
                calculation_status = "success"

        out.append(
            {
                "activity_id": activity_id,
                "factor_id": factor_id,
                "standardized_amount": standardized_amount,
                "standardized_unit": n["standardized_unit"],
                "applied_factor": applied_factor,
                "factor_unit": factor_unit,
                "co2e_kg": co2e_kg,
                "scope_category": raw["scope_category"],
                "calculation_status": calculation_status,
                "excluded_from_reporting": excluded_from_reporting,
                "exclusion_reason": exclusion_reason,
                "calculation_version": "calc-v1.0",
                "calculated_at": now,
            }
        )

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ESG 더미 데이터 처리기(정책 적용 전용)")
    parser.add_argument("--in-dir", type=Path, default=Path("dummy_esg"))
    parser.add_argument("--out-dir", type=Path, default=Path("dummy_esg"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    raw_rows = read_csv(args.in_dir / "activity_raw.csv")
    conversion_rules = read_csv(args.in_dir / "unit_conversions.csv")
    factors = read_csv(args.in_dir / "emission_factors.csv")

    normalized_rows = normalize_activity_units(raw_rows, conversion_rules)
    emissions_rows = calculate_activity_emissions(raw_rows, normalized_rows, factors)

    write_csv(args.out_dir / "activity_normalized.csv", normalized_rows)
    write_csv(args.out_dir / "activity_emissions.csv", emissions_rows)

    processing_report = {
        "input_rows": len(raw_rows),
        "normalized_success": sum(1 for r in normalized_rows if r["conversion_status"] in ("converted", "already_standard")),
        "normalized_failed": sum(1 for r in normalized_rows if r["conversion_status"] == "failed"),
        "calculation_success": sum(1 for r in emissions_rows if r["calculation_status"] == "success"),
        "calculation_failed": sum(1 for r in emissions_rows if r["calculation_status"] == "failed"),
        "calculation_excluded": sum(1 for r in emissions_rows if r["calculation_status"] == "excluded"),
    }
    (args.out_dir / "processing_report.json").write_text(json.dumps(processing_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] processed data written to: {args.out_dir.resolve()}")
    print(json.dumps(processing_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
