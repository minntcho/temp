"""canonical row(merged)만 대상으로 배출량 계산."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="canonical emissions calculator")
    p.add_argument("--canonical", type=Path, required=True)
    p.add_argument("--factors", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    canonical = read_csv(args.canonical)
    factors = read_csv(args.factors)
    factor_map = {(f["activity_type"], f["unit"]): f for f in factors}

    out = []
    for r in canonical:
        if r.get("status") != "merged":
            continue
        key = (r.get("activity_type", ""), r.get("standardized_unit", ""))
        f = factor_map.get(key)
        if not f:
            continue
        amount = float(r.get("standardized_amount", "0") or 0)
        ef = float(f["emission_factor"])
        out.append(
            {
                "row_id": r["row_id"],
                "factor_id": f["factor_id"],
                "standardized_amount": amount,
                "standardized_unit": r["standardized_unit"],
                "applied_factor": ef,
                "factor_unit": f["factor_unit"],
                "co2e_kg": round(amount * ef, 6),
                "scope_category": r["scope_category"],
                "calculation_status": "success",
                "calculated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "canonical_activity_emissions.csv", out)
    report = {"input_canonical_rows": len(canonical), "calculated_rows": len(out)}
    (args.out_dir / "canonical_calc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] canonical calculation complete: {args.out_dir.resolve()}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
