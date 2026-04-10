"""단일 E2E ESG 파이프라인 러너.

목적:
- 정형/반정형/비정형이 섞인 입력을 하나의 파이프라인에서 처리한다.
- 기존 생성기/정규화기/처리기를 순차 오케스트레이션하고,
  다중 출처 정규화 결과를 claim/row 브리지로 승격한 뒤 canonical 계산을 수행한다.
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
    bridge_dir = args.work_dir / "bridge"
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

    bridge_cmd = [
        "python", "bridge_staging_to_canonical.py",
        "--staging", str(raw_dir / "unified_raw_staging.csv"),
        "--out-dir", str(bridge_dir),
        "--auto-merge",
    ]
    run(bridge_cmd)

    calc_cmd = [
        "python", "calculate_canonical_emissions.py",
        "--canonical", str(bridge_dir / "canonical_rows.csv"),
        "--factors", str(base_dir / "emission_factors.csv"),
        "--out-dir", str(bridge_dir),
    ]
    run(calc_cmd)

    print(f"[OK] unified pipeline complete: {args.work_dir.resolve()}")
    merged_rows = read_csv(bridge_dir / "canonical_rows.csv")
    print(f"- merged canonical rows: {len(merged_rows)}")


if __name__ == "__main__":
    main()
