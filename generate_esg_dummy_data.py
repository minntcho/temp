"""ESG 더미 데이터 생성기 (생성 전용).

역할:
- 마스터/원시 데이터 생성만 수행 (처리 정책 미포함)

생성 산출물
- legal_entities.csv
- sites.csv
- products.csv
- suppliers.csv
- reporting_calendar.csv
- unit_conversions.csv
- emission_factors.csv
- activity_raw.csv
- metadata.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ActivityProfile:
    activity_type: str
    standard_unit: str
    amount_mean: float
    amount_std: float
    emission_factor: float
    factor_unit: str
    default_scope: str


PROFILES: tuple[ActivityProfile, ...] = (
    ActivityProfile("electricity", "kWh", 1200, 250, 0.45, "kgCO2e/kWh", "Scope2"),
    ActivityProfile("diesel", "L", 80, 20, 2.68, "kgCO2e/L", "Scope1"),
    ActivityProfile("natural_gas", "Nm3", 300, 70, 2.02, "kgCO2e/Nm3", "Scope1"),
    ActivityProfile("steam", "ton", 7, 2, 120.0, "kgCO2e/ton", "Scope2"),
)

ENERGY_PROFILE_TO_ALLOWED_ACTIVITIES = {
    "electricity_only": {"electricity"},
    "gas_heavy": {"electricity", "natural_gas", "steam"},
    "mixed": {"electricity", "diesel", "natural_gas", "steam"},
    "office_light": {"electricity"},
}

POSSIBLE_WRONG_UNITS = {
    "electricity": "MWh",
    "diesel": "gallon",
    "natural_gas": "m3",
    "steam": "kg",
}


def daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def month_start_dates(start: date, end: date) -> list[date]:
    cursor = date(start.year, start.month, 1)
    out: list[date] = []
    while cursor <= end:
        out.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return out


def parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def validate_args(args: argparse.Namespace) -> None:
    if args.rows < 1:
        raise ValueError("rows must be >= 1")
    if args.num_entities < 1:
        raise ValueError("num_entities must be >= 1")
    if args.num_sites < 1:
        raise ValueError("num_sites must be >= 1")
    if args.num_products < 1:
        raise ValueError("num_products must be >= 1")
    if args.num_suppliers < 1:
        raise ValueError("num_suppliers must be >= 1")
    if not (0 <= args.anomaly_rate <= 1):
        raise ValueError("anomaly_rate must be between 0 and 1")
    if parse_iso_date(args.start_date) > parse_iso_date(args.end_date):
        raise ValueError("start_date must be <= end_date")


def generate_legal_entities(num_entities: int) -> list[dict[str, str]]:
    ownership_types = ["operational_control", "financial_control", "equity_share"]
    countries = ["KR", "US", "VN", "CN"]
    rows = []
    for i in range(1, num_entities + 1):
        rows.append(
            {
                "entity_id": f"ENT-{i:03d}",
                "entity_name": f"Entity_{i:03d}",
                "country": countries[(i - 1) % len(countries)],
                "ownership_type": ownership_types[(i - 1) % len(ownership_types)],
                "reporting_included": "N" if i % 7 == 0 else "Y",
            }
        )
    return rows


def generate_sites(num_sites: int, entities: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed + 101)
    site_types = ["plant", "office", "warehouse"]
    energy_profiles = list(ENERGY_PROFILE_TO_ALLOWED_ACTIVITIES.keys())
    rows = []
    for i in range(1, num_sites + 1):
        entity = rng.choice(entities)
        rows.append(
            {
                "site_id": f"SITE-{i:03d}",
                "site_name": f"Site_{i:03d}",
                "entity_id": entity["entity_id"],
                "country": entity["country"],
                "site_type": rng.choice(site_types),
                "energy_profile": rng.choice(energy_profiles),
                "reporting_included": entity["reporting_included"],
            }
        )
    return rows


def generate_products(num_products: int, sites: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed + 202)
    product_categories = ["component", "module", "assembly", "packaging"]
    rows = []
    for i in range(1, num_products + 1):
        main_site = rng.choice(sites)
        rows.append(
            {
                "product_id": f"PRD-{i:04d}",
                "product_name": f"Product_{i:04d}",
                "product_category": rng.choice(product_categories),
                "main_site_id": main_site["site_id"],
                "carbon_relevant": "N" if i % 11 == 0 else "Y",
            }
        )

    plant_sites = [s for s in sites if s["site_type"] == "plant"]
    product_by_site = {p["main_site_id"] for p in rows}
    idx = 0
    for site in plant_sites:
        if site["site_id"] not in product_by_site:
            rows[idx % len(rows)]["main_site_id"] = site["site_id"]
            idx += 1
    return rows


def generate_suppliers(num_suppliers: int) -> list[dict[str, str]]:
    sectors = ["metal", "chemical", "electronics", "logistics", "packaging"]
    grades = ["A", "B", "C"]
    rows = []
    for i in range(1, num_suppliers + 1):
        rows.append(
            {
                "supplier_id": f"SUP-{i:03d}",
                "supplier_name": f"Supplier_{i:03d}",
                "sector": sectors[(i - 1) % len(sectors)],
                "country": "KR" if i % 2 else "US",
                "esg_grade": grades[(i - 1) % len(grades)],
                "human_rights_risk": "high" if i % 13 == 0 else "low",
            }
        )
    return rows


def generate_reporting_calendar(start: date, end: date) -> list[dict[str, str | int]]:
    rows = []
    for month_start in month_start_dates(start, end):
        rows.append(
            {
                "period_id": f"P-{month_start.year}{month_start.month:02d}",
                "year": month_start.year,
                "month": month_start.month,
                "quarter": ((month_start.month - 1) // 3) + 1,
                "fiscal_year": month_start.year,
            }
        )
    return rows


def generate_unit_conversions() -> list[dict[str, str | float]]:
    return [
        {"conversion_id": "UC-ELC-MWH-TO-KWH", "activity_type": "electricity", "from_unit": "MWh", "to_unit": "kWh", "multiplier": 1000.0, "offset": 0.0, "rule_version": "v1.0", "valid_from": "2025-01-01", "valid_to": "2026-12-31"},
        {"conversion_id": "UC-DSL-GALLON-TO-L", "activity_type": "diesel", "from_unit": "gallon", "to_unit": "L", "multiplier": 3.78541, "offset": 0.0, "rule_version": "v1.0", "valid_from": "2025-01-01", "valid_to": "2026-12-31"},
        {"conversion_id": "UC-NG-M3-TO-NM3", "activity_type": "natural_gas", "from_unit": "m3", "to_unit": "Nm3", "multiplier": 1.0, "offset": 0.0, "rule_version": "v1.0", "valid_from": "2025-01-01", "valid_to": "2026-12-31"},
        {"conversion_id": "UC-STM-KG-TO-TON", "activity_type": "steam", "from_unit": "kg", "to_unit": "ton", "multiplier": 0.001, "offset": 0.0, "rule_version": "v1.0", "valid_from": "2025-01-01", "valid_to": "2026-12-31"},
    ]


def generate_emission_factors() -> list[dict[str, str | float]]:
    rows = []
    for idx, p in enumerate(PROFILES, start=1):
        rows.append(
            {
                "factor_id": f"EF-{idx:03d}",
                "activity_type": p.activity_type,
                "unit": p.standard_unit,
                "scope_category": p.default_scope,
                "emission_factor": round(p.emission_factor, 6),
                "factor_unit": p.factor_unit,
                "factor_source": "IPCC_2024_guideline_mock",
                "factor_version": "v1.0",
                "calculation_method": "activity_x_factor",
                "applicable_country": "GLOBAL",
                "valid_from": "2025-01-01",
                "valid_to": "2026-12-31",
            }
        )
    return rows


def inject_anomaly(row: dict[str, str | float], rng: random.Random) -> str:
    anomaly_type = rng.choice(["spike", "zero", "negative", "unit_mismatch", "missing_product"])
    if anomaly_type == "spike":
        row["raw_amount"] = round(float(row["raw_amount"]) * rng.uniform(5, 12), 3)
    elif anomaly_type == "zero":
        row["raw_amount"] = 0.0
    elif anomaly_type == "negative":
        row["raw_amount"] = -abs(float(row["raw_amount"]))
    elif anomaly_type == "unit_mismatch":
        row["raw_unit"] = POSSIBLE_WRONG_UNITS.get(str(row["activity_type"]), str(row["raw_unit"]))
    elif anomaly_type == "missing_product":
        row["product_id"] = ""
    return anomaly_type


def generate_activity_raw(*, rows: int, start_date: date, end_date: date, anomaly_rate: float, seed: int, sites: list[dict[str, str]], products: list[dict[str, str]], suppliers: list[dict[str, str]]) -> tuple[list[dict[str, str | float]], dict[str, int]]:
    rng = random.Random(seed)
    dates = list(daterange(start_date, end_date))
    profile_map = {p.activity_type: p for p in PROFILES}

    products_by_site: dict[str, list[dict[str, str]]] = {}
    for p in products:
        products_by_site.setdefault(p["main_site_id"], []).append(p)

    anomaly_counter: dict[str, int] = {}
    results: list[dict[str, str | float]] = []
    for i in range(1, rows + 1):
        site = rng.choice(sites)
        activity_type = rng.choice(list(ENERGY_PROFILE_TO_ALLOWED_ACTIVITIES[site["energy_profile"]]))
        profile = profile_map[activity_type]
        activity_date = rng.choice(dates)
        period_id = f"P-{activity_date.year}{activity_date.month:02d}"
        site_products = products_by_site.get(site["site_id"], [])
        product_id = rng.choice(site_products)["product_id"] if site["site_type"] == "plant" and site_products else ""

        row: dict[str, str | float] = {
            "activity_id": f"ACT-{i:07d}",
            "activity_date": activity_date.isoformat(),
            "period_id": period_id,
            "entity_id": site["entity_id"],
            "site_id": site["site_id"],
            "product_id": product_id,
            "supplier_id": rng.choice(suppliers)["supplier_id"],
            "activity_type": activity_type,
            "scope_category": profile.default_scope,
            "raw_unit": profile.standard_unit,
            "raw_amount": round(max(0.0, rng.gauss(profile.amount_mean, profile.amount_std)), 3),
            "source_system": rng.choice(["erp", "mes", "manual", "iot"]),
            "measurement_type": rng.choice(["measured", "estimated", "manual"]),
            "reporting_included": site["reporting_included"],
            "recorded_at": f"{activity_date.isoformat()}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:00Z",
        }

        if rng.random() < anomaly_rate:
            atype = inject_anomaly(row, rng)
            row["is_injected_anomaly"] = "Y"
            row["injected_anomaly_type"] = atype
            anomaly_counter[atype] = anomaly_counter.get(atype, 0) + 1
        else:
            row["is_injected_anomaly"] = "N"
            row["injected_anomaly_type"] = ""
        results.append(row)
    return results, anomaly_counter


def write_csv(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ESG 더미 데이터 생성기(생성 전용)")
    parser.add_argument("--out-dir", type=Path, default=Path("dummy_esg"))
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--num-entities", type=int, default=5)
    parser.add_argument("--num-sites", type=int, default=20)
    parser.add_argument("--num-products", type=int, default=60)
    parser.add_argument("--num-suppliers", type=int, default=30)
    parser.add_argument("--start-date", type=str, default="2025-01-01")
    parser.add_argument("--end-date", type=str, default="2025-12-31")
    parser.add_argument("--anomaly-rate", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_args(args)
    start_date = parse_iso_date(args.start_date)
    end_date = parse_iso_date(args.end_date)

    entities = generate_legal_entities(args.num_entities)
    sites = generate_sites(args.num_sites, entities, args.seed)
    products = generate_products(args.num_products, sites, args.seed)
    suppliers = generate_suppliers(args.num_suppliers)
    calendar = generate_reporting_calendar(start_date, end_date)
    unit_conversions = generate_unit_conversions()
    factors = generate_emission_factors()
    raw_rows, anomaly_counter = generate_activity_raw(rows=args.rows, start_date=start_date, end_date=end_date, anomaly_rate=args.anomaly_rate, seed=args.seed, sites=sites, products=products, suppliers=suppliers)

    write_csv(args.out_dir / "legal_entities.csv", entities)
    write_csv(args.out_dir / "sites.csv", sites)
    write_csv(args.out_dir / "products.csv", products)
    write_csv(args.out_dir / "suppliers.csv", suppliers)
    write_csv(args.out_dir / "reporting_calendar.csv", calendar)
    write_csv(args.out_dir / "unit_conversions.csv", unit_conversions)
    write_csv(args.out_dir / "emission_factors.csv", factors)
    write_csv(args.out_dir / "activity_raw.csv", raw_rows)

    metadata = {
        "rows": args.rows,
        "date_range": [args.start_date, args.end_date],
        "anomaly_rate": args.anomaly_rate,
        "seed": args.seed,
        "generated_files": [
            "legal_entities.csv", "sites.csv", "products.csv", "suppliers.csv", "reporting_calendar.csv",
            "unit_conversions.csv", "emission_factors.csv", "activity_raw.csv"
        ],
        "injected_anomaly_count": sum(anomaly_counter.values()),
        "injected_anomaly_breakdown": anomaly_counter,
        "notes": "Generation-only ESG dummy dataset",
    }
    (args.out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] raw/master data generated at: {args.out_dir.resolve()}")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
