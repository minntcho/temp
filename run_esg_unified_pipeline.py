"""단일 E2E ESG 파이프라인 러너.

목적:
- 정형/반정형/비정형이 섞인 입력을 하나의 파이프라인에서 처리한다.
- 기존 생성기/정규화기/처리기를 순차 오케스트레이션하고,
  다중 출처 정규화 결과를 activity_raw에 병합한 뒤 계산을 수행한다.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def stage_to_activity_rows(staging_rows: list[dict[str, str]], start_idx: int = 1) -> list[dict[str, str]]:
    scope_map = {
        "electricity": "Scope2",
        "steam": "Scope2",
        "diesel": "Scope1",
        "natural_gas": "Scope1",
    }
    out = []
    idx = start_idx
    for r in staging_rows:
        if r.get("status") != "ok":
            continue
        period = r.get("period", "2025-01")
        activity_date = f"{period}-01"
        out.append(
            {
                "activity_id": f"ACT-MIX-{idx:07d}",
                "activity_date": activity_date,
                "period_id": f"P-{period.replace('-', '')}",
                "entity_id": "ENT-EXT",
                "site_id": f"SITE-EXT-{idx:05d}",
                "product_id": "",
                "supplier_id": "SUP-EXT",
                "activity_type": r.get("activity_type", ""),
                "scope_category": scope_map.get(r.get("activity_type", ""), "Scope2"),
                "raw_unit": r.get("raw_unit", ""),
                "raw_amount": r.get("raw_amount", "0"),
                "source_system": r.get("source_type", "multisource"),
                "measurement_type": "estimated",
                "reporting_included": "Y",
                "recorded_at": f"{activity_date}T00:00:00Z",
                "is_injected_anomaly": "N",
                "injected_anomaly_type": "",
            }
        )
        idx += 1
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="단일 E2E ESG 파이프라인")
    p.add_argument("--work-dir", type=Path, default=Path("unified_esg"))
    p.add_argument("--base-rows", type=int, default=80)
    p.add_argument("--source-rows", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--trace", action="store_true")
    args = p.parse_args()

    base_dir = args.work_dir / "base"
    raw_dir = args.work_dir / "multisource"
    args.work_dir.mkdir(parents=True, exist_ok=True)

    run([
        "python", "generate_esg_dummy_data.py",
        "--out-dir", str(base_dir),
        "--rows", str(args.base_rows),
        "--seed", str(args.seed),
    ])
    run([
        "python", "generate_multisource_esg_raw.py",
        "--out-dir", str(raw_dir),
        "--rows", str(args.source_rows),
        "--seed", str(args.seed),
    ])
    run([
        "python", "normalize_multisource_esg.py",
        "--in-dir", str(raw_dir),
        "--out-dir", str(raw_dir),
    ])

    base_rows = read_csv(base_dir / "activity_raw.csv")
    staging_rows = read_csv(raw_dir / "unified_raw_staging.csv")
    mixed_rows = stage_to_activity_rows(staging_rows, start_idx=len(base_rows) + 1)

    merged = base_rows + mixed_rows
    write_csv(base_dir / "activity_raw.csv", merged)

    cmd = ["python", "process_esg_dummy_data.py", "--in-dir", str(base_dir), "--out-dir", str(base_dir)]
    if args.trace:
        cmd.append("--trace")
    run(cmd)

    print(f"[OK] unified pipeline complete: {args.work_dir.resolve()}")
    print(f"- merged activity_raw rows: {len(merged)}")


if __name__ == "__main__":
    main()
