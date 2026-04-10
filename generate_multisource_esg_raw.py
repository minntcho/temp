"""출처별 원형 ESG 원시데이터 생성기.

목적:
- 처음부터 통일된 스키마가 아닌, 출처별로 서로 다른 형태의 데이터를 생성한다.
- 정형/반정형/비정형 입력을 섞어 ingestion/표준화 파이프라인 테스트에 사용한다.

산출물:
- erp_energy.csv          (정형)
- supplier_fuel_sheet.csv (반정형: 컬럼명/단위 혼재)
- field_notes.txt         (비정형 자유서술)
- email_dump.jsonl        (비정형 메일 본문)
- source_manifest.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SITES = ["울산공장", "평택공장", "인천물류센터", "서울사무소"]


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def make_erp_energy(path: Path, rows: int, rng: random.Random, start: date, end: date) -> int:
    dates = list(daterange(start, end))
    out_rows = []
    for _ in range(rows):
        out_rows.append(
            {
                "work_dt": rng.choice(dates).isoformat(),
                "plant_name": rng.choice(SITES),
                "energy_kind": rng.choice(["electricity", "diesel", "natural_gas"]),
                "qty": round(max(0.0, rng.gauss(500, 120)), 3),
                "uom": rng.choice(["kWh", "L", "Nm3"]),
            }
        )

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    return len(out_rows)


def make_supplier_sheet(path: Path, rows: int, rng: random.Random, start: date, end: date) -> int:
    dates = list(daterange(start, end))
    headers = ["공급사", "사업장", "기준월", "항목", "사용량", "단위"]
    suppliers = ["한빛화학", "동해물류", "미래소재", "세종기계"]
    items = ["전력", "디젤", "스팀"]
    units = ["MWh", "gallon", "kg", "kWh"]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for _ in range(rows):
            d = rng.choice(dates)
            w.writerow(
                [
                    rng.choice(suppliers),
                    rng.choice(SITES),
                    f"{d.year}-{d.month:02d}",
                    rng.choice(items),
                    round(max(0.0, rng.gauss(80, 30)), 3),
                    rng.choice(units),
                ]
            )
    return rows


def make_field_notes(path: Path, rows: int, rng: random.Random, start: date, end: date) -> int:
    dates = list(daterange(start, end))
    templates = [
        "{site} {month} 전력 사용량 약 {amount}MWh 로 집계됨",
        "{site}에서 {month} 디젤 {amount} gallon 사용",
        "{site} {month} 스팀 사용량 {amount}kg 추정",
        "{site} {month} 천연가스 {amount}Nm3",
    ]
    lines = []
    for _ in range(rows):
        d = rng.choice(dates)
        lines.append(
            rng.choice(templates).format(
                site=rng.choice(SITES),
                month=f"{d.year}-{d.month:02d}",
                amount=round(max(0.0, rng.gauss(120, 45)), 2),
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(lines)


def make_email_dump(path: Path, rows: int, rng: random.Random, start: date, end: date) -> int:
    dates = list(daterange(start, end))
    bodies = []
    for i in range(rows):
        d = rng.choice(dates)
        site = rng.choice(SITES)
        body = rng.choice(
            [
                f"[{site}] {d.year}-{d.month:02d} electricity {round(rng.uniform(0.8,2.5),2)} MWh 확인 바랍니다.",
                f"{site} {d.year}/{d.month:02d} diesel {round(rng.uniform(30,120),2)}L 입력 요청",
                f"보고: {site} {d.year}-{d.month:02d} steam {round(rng.uniform(200,1200),1)}kg",
            ]
        )
        bodies.append({"mail_id": f"MAIL-{i+1:05d}", "subject": "ESG data", "body": body})

    with path.open("w", encoding="utf-8") as f:
        for obj in bodies:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return len(bodies)


def main() -> None:
    p = argparse.ArgumentParser(description="출처별 ESG 원시 데이터 생성기")
    p.add_argument("--out-dir", type=Path, default=Path("raw_multisource"))
    p.add_argument("--rows", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--start-date", type=str, default="2025-01-01")
    p.add_argument("--end-date", type=str, default="2025-12-31")
    args = p.parse_args()

    rng = random.Random(args.seed)
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "erp_energy.csv": make_erp_energy(args.out_dir / "erp_energy.csv", args.rows, rng, start, end),
        "supplier_fuel_sheet.csv": make_supplier_sheet(args.out_dir / "supplier_fuel_sheet.csv", args.rows, rng, start, end),
        "field_notes.txt": make_field_notes(args.out_dir / "field_notes.txt", args.rows, rng, start, end),
        "email_dump.jsonl": make_email_dump(args.out_dir / "email_dump.jsonl", args.rows, rng, start, end),
    }
    (args.out_dir / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] generated multisource raw data at: {args.out_dir.resolve()}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
