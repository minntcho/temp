"""staging -> claim -> row 브리지 계층 (MVP).

입력: unified_raw_staging.csv
출력:
- claims.csv
- resolved_rows.csv
- commit_table.csv
- event_log.csv
- canonical_rows.csv (merged only)
- bridge_trace.jsonl
- bridge_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


UNIT_COMPAT = {
    "electricity": {"kWh"},
    "diesel": {"L"},
    "natural_gas": {"Nm3"},
    "steam": {"ton"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str | float]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def as_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def main() -> None:
    p = argparse.ArgumentParser(description="staging -> canonical 브리지")
    p.add_argument("--staging", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--auto-merge", action="store_true")
    args = p.parse_args()

    rows = read_csv(args.staging)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    claims = []
    resolved = []
    commits = []
    events = []
    canonical = []
    traces = []

    for i, r in enumerate(rows, start=1):
        claim_id = f"CLM-{i:07d}"
        row_id = f"ROW-{i:07d}"
        raw_id = f"RAW-{i:07d}"

        proposed_site = r.get("site", "")
        proposed_period = r.get("period", "")
        proposed_activity_type = r.get("activity_type", "")
        proposed_raw_amount = r.get("raw_amount", "")
        proposed_raw_unit = r.get("raw_unit", "")

        claims.append(
            {
                "claim_id": claim_id,
                "parent_raw_id": raw_id,
                "source_type": r.get("source_type", ""),
                "source_ref": r.get("source_ref", ""),
                "evidence_text": r.get("raw_text", ""),
                "proposed_site": proposed_site,
                "proposed_period": proposed_period,
                "proposed_activity_type": proposed_activity_type,
                "proposed_raw_amount": proposed_raw_amount,
                "proposed_raw_unit": proposed_raw_unit,
                "parser_version": "parser-v1.0",
                "representation": "claim",
                "status": "resolving",
            }
        )

        # completeness
        completeness_ok = all([
            proposed_site,
            proposed_period,
            proposed_activity_type,
            proposed_raw_amount,
            proposed_raw_unit,
        ])
        # consistency
        amount = as_float(proposed_raw_amount, -1)
        amount_ok = amount >= 0
        period_ok = len(proposed_period) == 7 and proposed_period[4] == "-"
        unit_ok = r.get("standardized_unit", "") in UNIT_COMPAT.get(proposed_activity_type, set())

        completeness_score = 1.0 if completeness_ok else 0.0
        consistency_score = (1.0 if amount_ok else 0.0) * 0.4 + (1.0 if period_ok else 0.0) * 0.3 + (1.0 if unit_ok else 0.0) * 0.3
        parser_score = as_float(str(r.get("confidence", "0")), 0.0)

        resolution_score = round(0.4 * completeness_score + 0.4 * consistency_score + 0.2 * parser_score, 4)

        if not completeness_ok:
            status = "rejected"
            reason = "incomplete_fields"
        elif resolution_score >= 0.8:
            status = "committed"
            reason = "threshold_pass"
        elif resolution_score >= 0.55:
            status = "review_required"
            reason = "needs_review"
        else:
            status = "rejected"
            reason = "low_score"

        if status == "committed" and args.auto_merge:
            final_status = "merged"
        else:
            final_status = status

        resolved_row = {
            "row_id": row_id,
            "parent_claim_id": claim_id,
            "site_id": f"SITE-AUTO-{i:05d}",
            "entity_id": "ENT-AUTO",
            "scope_category": "Scope2" if proposed_activity_type in ("electricity", "steam") else "Scope1",
            "reporting_included": "Y",
            "activity_type": proposed_activity_type,
            "raw_amount": proposed_raw_amount,
            "raw_unit": proposed_raw_unit,
            "standardized_amount": r.get("standardized_amount", ""),
            "standardized_unit": r.get("standardized_unit", ""),
            "resolution_score": resolution_score,
            "representation": "row",
            "status": final_status,
            "reason_code": reason,
            "created_at": now,
        }
        resolved.append(resolved_row)

        commits.append(
            {
                "commit_id": f"CMT-{i:07d}",
                "record_id": row_id,
                "parent_commit_id": "",
                "score": resolution_score,
                "reason_code": reason,
                "rule_version": "bridge-rules-v1.0",
                "model_version": "rule-only",
                "created_by": "system",
                "created_at": now,
                "to_status": final_status,
            }
        )
        events.append(
            {
                "event_id": f"EVT-{i:07d}",
                "record_id": row_id,
                "event_type": "RESOLVED",
                "from_status": "resolving",
                "to_status": final_status,
                "score": resolution_score,
                "reason_code": reason,
                "actor": "system",
                "created_at": now,
            }
        )

        traces.append(
            {
                "run_id": "RUN-BRIDGE-001",
                "record_id": row_id,
                "parent_id": claim_id,
                "representation": "row",
                "status": final_status,
                "reason_code": reason,
                "score": resolution_score,
                "created_at": now,
                "validation": {
                    "completeness_ok": completeness_ok,
                    "amount_ok": amount_ok,
                    "period_ok": period_ok,
                    "unit_ok": unit_ok,
                },
            }
        )

        if final_status == "merged":
            canonical.append(resolved_row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "claims.csv", claims)
    write_csv(args.out_dir / "resolved_rows.csv", resolved)
    write_csv(args.out_dir / "commit_table.csv", commits)
    write_csv(args.out_dir / "event_log.csv", events)
    write_csv(args.out_dir / "canonical_rows.csv", canonical)

    with (args.out_dir / "bridge_trace.jsonl").open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    report = {
        "total_claims": len(claims),
        "committed": sum(1 for r in resolved if r["status"] == "committed"),
        "merged": sum(1 for r in resolved if r["status"] == "merged"),
        "review_required": sum(1 for r in resolved if r["status"] == "review_required"),
        "rejected": sum(1 for r in resolved if r["status"] == "rejected"),
    }
    (args.out_dir / "bridge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] bridge completed: {args.out_dir.resolve()}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
