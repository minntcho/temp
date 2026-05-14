from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path
from typing import Any, Iterable

from synthetic_esg.config import GenerationConfig
from synthetic_esg.naming import generate_entity_name, generate_supplier_name

DEFAULT_ACTIVITIES: dict[str, dict[str, Any]] = {
    "electricity": {"standard_unit": "kWh", "scope": "Scope2", "factor": 0.45, "factor_unit": "kgCO2e/kWh"},
    "diesel": {"standard_unit": "L", "scope": "Scope1", "factor": 2.68, "factor_unit": "kgCO2e/L"},
    "natural_gas": {"standard_unit": "Nm3", "scope": "Scope1", "factor": 2.02, "factor_unit": "kgCO2e/Nm3"},
    "steam": {"standard_unit": "ton", "scope": "Scope2", "factor": 120.0, "factor_unit": "kgCO2e/ton"},
}

UNIT_VARIANTS = {
    "electricity": [("kWh", 1.0), ("MWh", 0.001)],
    "diesel": [("L", 1.0), ("gallon", 1 / 3.78541)],
    "natural_gas": [("Nm3", 1.0), ("m3", 1.0)],
    "steam": [("ton", 1.0), ("kg", 1000.0)],
}

WRONG_UNITS = {
    "electricity": ["L", "gallon", "kg"],
    "diesel": ["kWh", "MWh", "Nm3"],
    "natural_gas": ["kWh", "L", "ton"],
    "steam": ["kWh", "L", "Nm3"],
}

COUNTRIES = ["KR", "US", "PL", "CN", "ID", "VN"]
OWNERSHIP_TYPES = ["operational_control", "financial_control", "equity_share"]
BUSINESS_UNITS = ["Cell", "ModulePack", "ESS", "BMS", "RND", "Operations", "Quality", "SCM"]
SITE_TYPES = ["plant", "r_and_d", "warehouse", "office"]
SITE_NAMES = [
    "Ochangg Energy Plant",
    "Daejeon RnD Campus",
    "Gumi Module Plant",
    "Michigan Cell Plant",
    "Arizona Battery Plant",
    "Wroclaw Battery Plant",
    "Nanjing Cell Plant",
    "Karawang Joint Plant",
    "Seoul Office",
    "Incheon Logistics Hub",
]
LINE_TYPES = ["electrode_coating_line", "cell_assembly_line", "formation_line", "aging_line", "module_pack_line"]
PRODUCT_CATEGORIES = ["pouch_cell", "cylindrical_cell", "prismatic_cell", "ev_module", "ess_pack", "bms_component"]


def populate_output_rows(
    *,
    config: GenerationConfig,
    master_headers: dict[str, list[str]],
    truth_headers: dict[str, list[str]],
) -> dict[str, int]:
    """Populate the generation-only output contract with synthetic rows.

    This writes master data, raw source observations, truth labels, raw-to-truth
    links, and injected anomaly labels. It intentionally does not normalize,
    repair, analyze, or calculate from raw inputs.
    """

    rng = random.Random(config.seed)
    config.out_dir.mkdir(parents=True, exist_ok=True)
    (config.out_dir / "master").mkdir(parents=True, exist_ok=True)
    (config.out_dir / "truth").mkdir(parents=True, exist_ok=True)
    (config.out_dir / "raw_sources").mkdir(parents=True, exist_ok=True)

    activities = normalize_activities(config.activity_types)
    periods = build_periods(config)
    masters = build_master_data(config, rng, periods, activities)
    truth_activity, truth_emissions = build_truth_data(config, rng, periods, activities, masters)
    source_map: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []

    counts: dict[str, int] = {}
    for filename, headers in master_headers.items():
        stem = filename.removesuffix(".csv")
        counts[f"master/{filename}"] = write_csv(config.out_dir / "master" / filename, headers, masters.get(stem, []))

    counts.update(
        export_raw_sources(
            config=config,
            rng=rng,
            periods=periods,
            masters=masters,
            truth_activity=truth_activity,
            source_map=source_map,
            anomalies=anomalies,
        )
    )

    truth_rows = {
        "canonical_activity.csv": truth_activity,
        "canonical_emissions.csv": truth_emissions,
        "source_to_truth_map.csv": source_map,
        "injected_anomalies.csv": anomalies,
    }
    for filename, headers in truth_headers.items():
        counts[f"truth/{filename}"] = write_csv(config.out_dir / "truth" / filename, headers, truth_rows.get(filename, []))

    return counts


def normalize_activities(activity_types: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not activity_types:
        return dict(DEFAULT_ACTIVITIES)
    out: dict[str, dict[str, Any]] = {}
    for name, raw in activity_types.items():
        default = DEFAULT_ACTIVITIES.get(name, {})
        out[name] = {
            "standard_unit": raw.get("standard_unit", default.get("standard_unit", "unit")),
            "scope": raw.get("scope", default.get("scope", "ScopeX")),
            "factor": raw.get("factor", default.get("factor", 1.0)),
            "factor_unit": raw.get("factor_unit", default.get("factor_unit", "kgCO2e/unit")),
        }
    return out


def build_periods(config: GenerationConfig) -> list[dict[str, Any]]:
    start = str(config.period.get("start_month", "2026-01"))
    end = str(config.period.get("end_month", start))
    months = month_range(start, end)
    month_override = config.scale.get("months")
    if isinstance(month_override, int) and month_override > 0:
        while len(months) < month_override:
            months.append(add_month(months[-1], 1))
        months = months[:month_override]

    rows = []
    for month in months:
        year, month_number = [int(part) for part in month.split("-")]
        rows.append(
            {
                "period_id": f"P-{year}{month_number:02d}",
                "period": month,
                "year": year,
                "month": month_number,
                "quarter": ((month_number - 1) // 3) + 1,
                "fiscal_year": year,
            }
        )
    return rows


def month_range(start: str, end: str) -> list[str]:
    year, month = [int(part) for part in start.split("-")]
    end_year, end_month = [int(part) for part in end.split("-")]
    rows = []
    while (year, month) <= (end_year, end_month):
        rows.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return rows


def add_month(month: str, offset: int) -> str:
    year, month_number = [int(part) for part in month.split("-")]
    absolute = year * 12 + (month_number - 1) + offset
    new_year, new_month_zero = divmod(absolute, 12)
    return f"{new_year:04d}-{new_month_zero + 1:02d}"


def scale_int(config: GenerationConfig, *keys: str, default: int) -> int:
    for key in keys:
        value = config.scale.get(key)
        if isinstance(value, int):
            return value
    return default


def build_master_data(
    config: GenerationConfig,
    rng: random.Random,
    periods: list[dict[str, Any]],
    activities: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    entity_count = scale_int(config, "legal_entities", default=2)
    bu_count = scale_int(config, "business_units", default=2)
    site_count = scale_int(config, "sites", default=3)
    line_count = scale_int(config, "production_lines", "lines", default=5)
    product_count = scale_int(config, "products", default=6)
    supplier_count = scale_int(config, "suppliers", default=10)
    meter_count = scale_int(config, "meters", default=max(20, site_count * 4))

    legal_entities = []
    for i in range(1, entity_count + 1):
        country = COUNTRIES[(i - 1) % len(COUNTRIES)]
        legal_entities.append(
            {
                "entity_id": f"ENT-{i:03d}",
                "entity_name": generate_entity_name(country=country, entity_index=i, seed=config.seed),
                "country": country,
                "ownership_type": OWNERSHIP_TYPES[(i - 1) % len(OWNERSHIP_TYPES)],
                "reporting_included": "N" if i % 17 == 0 else "Y",
            }
        )

    business_units = []
    for i in range(1, bu_count + 1):
        entity = legal_entities[(i - 1) % len(legal_entities)]
        business_units.append(
            {
                "business_unit_id": f"BU-{i:03d}",
                "business_unit_name": BUSINESS_UNITS[(i - 1) % len(BUSINESS_UNITS)],
                "entity_id": entity["entity_id"],
            }
        )

    sites = []
    for i in range(1, site_count + 1):
        entity = legal_entities[(i - 1) % len(legal_entities)]
        sites.append(
            {
                "site_id": f"SITE-{i:04d}",
                "site_name": f"{SITE_NAMES[(i - 1) % len(SITE_NAMES)]} {i:03d}",
                "entity_id": entity["entity_id"],
                "country": entity["country"],
                "site_type": SITE_TYPES[(i - 1) % len(SITE_TYPES)],
                "reporting_included": entity["reporting_included"],
            }
        )

    plant_sites = [site for site in sites if site["site_type"] == "plant"] or sites
    production_lines = []
    for i in range(1, line_count + 1):
        site = plant_sites[(i - 1) % len(plant_sites)]
        line_type = LINE_TYPES[(i - 1) % len(LINE_TYPES)]
        production_lines.append(
            {
                "line_id": f"LINE-{i:05d}",
                "line_name": f"{site['site_id']}-{line_type}-{i:05d}",
                "site_id": site["site_id"],
                "line_type": line_type,
            }
        )

    products = []
    for i in range(1, product_count + 1):
        line = production_lines[(i - 1) % len(production_lines)]
        category = PRODUCT_CATEGORIES[(i - 1) % len(PRODUCT_CATEGORIES)]
        products.append(
            {
                "product_id": f"PRD-{i:05d}",
                "product_name": f"{category.upper()}_{i:05d}",
                "product_category": category,
                "main_line_id": line["line_id"],
            }
        )

    suppliers = []
    for i in range(1, supplier_count + 1):
        country = COUNTRIES[(i - 1) % len(COUNTRIES)]
        suppliers.append(
            {
                "supplier_id": f"SUP-{i:06d}",
                "supplier_name": generate_supplier_name(country=country, supplier_index=i, seed=config.seed),
                "country": country,
                "supplier_tier": ["tier1", "tier2", "tier3"][(i - 1) % 3],
            }
        )

    activity_names = list(activities)
    meters = []
    for i in range(1, meter_count + 1):
        site = sites[(i - 1) % len(sites)]
        activity_type = rng.choice(activity_names)
        meters.append(
            {
                "meter_id": f"MTR-{i:07d}",
                "meter_name": f"{site['site_id']}-{activity_type}-meter-{i:07d}",
                "site_id": site["site_id"],
                "activity_type": activity_type,
                "unit": activities[activity_type]["standard_unit"],
            }
        )

    emission_factors = []
    for i, (activity_type, spec) in enumerate(activities.items(), start=1):
        emission_factors.append(
            {
                "factor_id": f"EF-{i:03d}",
                "activity_type": activity_type,
                "unit": spec["standard_unit"],
                "scope_category": spec["scope"],
                "emission_factor": spec["factor"],
                "factor_unit": spec["factor_unit"],
            }
        )

    unit_conversions = []
    conversion_id = 1
    for activity_type, spec in activities.items():
        variants = UNIT_VARIANTS.get(activity_type, [(spec["standard_unit"], 1.0)])
        for from_unit, standard_to_raw_multiplier in variants:
            unit_conversions.append(
                {
                    "conversion_id": f"UC-{conversion_id:04d}",
                    "activity_type": activity_type,
                    "from_unit": from_unit,
                    "to_unit": spec["standard_unit"],
                    "multiplier": round(1 / standard_to_raw_multiplier, 10),
                    "offset": 0,
                }
            )
            conversion_id += 1

    return {
        "legal_entities": legal_entities,
        "business_units": business_units,
        "sites": sites,
        "production_lines": production_lines,
        "products": products,
        "suppliers": suppliers,
        "meters": meters,
        "reporting_calendar": [
            {
                "period_id": row["period_id"],
                "year": row["year"],
                "month": row["month"],
                "quarter": row["quarter"],
                "fiscal_year": row["fiscal_year"],
            }
            for row in periods
        ],
        "emission_factors": emission_factors,
        "unit_conversions": unit_conversions,
    }


def build_truth_data(
    config: GenerationConfig,
    rng: random.Random,
    periods: list[dict[str, Any]],
    activities: dict[str, dict[str, Any]],
    masters: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sites_by_id = {row["site_id"]: row for row in masters["sites"]}
    factors_by_activity = {row["activity_type"]: row for row in masters["emission_factors"]}
    truth_activity = []
    truth_emissions = []

    for period in periods:
        seasonality = 1.0 + 0.08 * math.sin((int(period["month"]) / 12.0) * 2 * math.pi)
        for index, meter in enumerate(masters["meters"], start=1):
            activity_type = meter["activity_type"]
            baseline = baseline_amount(activity_type, len(masters["meters"]))
            amount = round(max(0, rng.gauss(baseline * seasonality, baseline * 0.18)), 6)
            truth_activity_id = f"ACT-{str(period['period_id']).removeprefix('P')}-{index:07d}"
            site = sites_by_id[meter["site_id"]]
            truth_activity.append(
                {
                    "truth_activity_id": truth_activity_id,
                    "period_id": period["period_id"],
                    "entity_id": site["entity_id"],
                    "site_id": site["site_id"],
                    "activity_type": activity_type,
                    "standardized_amount": amount,
                    "standardized_unit": activities[activity_type]["standard_unit"],
                }
            )
            factor = factors_by_activity[activity_type]
            truth_emissions.append(
                {
                    "truth_emission_id": f"EMI-{str(period['period_id']).removeprefix('P')}-{index:07d}",
                    "truth_activity_id": truth_activity_id,
                    "scope_category": factor["scope_category"],
                    "co2e_kg": round(amount * float(factor["emission_factor"]), 6),
                    "factor_id": factor["factor_id"],
                }
            )
    return truth_activity, truth_emissions


def baseline_amount(activity_type: str, meter_count: int) -> float:
    base = {
        "electricity": 1_200_000,
        "diesel": 8_000,
        "natural_gas": 180_000,
        "steam": 5_000,
    }.get(activity_type, 10_000)
    return max(1.0, base / max(1, meter_count / 85))


def export_raw_sources(
    *,
    config: GenerationConfig,
    rng: random.Random,
    periods: list[dict[str, Any]],
    masters: dict[str, list[dict[str, Any]]],
    truth_activity: list[dict[str, Any]],
    source_map: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for dirname in ["erp", "mes", "ems", "suppliers", "manual", "field_notes", "emails"]:
        (config.out_dir / "raw_sources" / dirname).mkdir(parents=True, exist_ok=True)

    period_by_id = {row["period_id"]: f"{row['year']:04d}-{row['month']:02d}" for row in masters["reporting_calendar"]}
    truth_by_period: dict[str, list[dict[str, Any]]] = {}
    for row in truth_activity:
        truth_by_period.setdefault(str(row["period_id"]), []).append(row)

    counts.update(export_erp(config, rng, masters, truth_by_period, period_by_id, source_map, anomalies))
    counts.update(export_ems(config, rng, truth_by_period, period_by_id, source_map, anomalies))
    counts.update(export_mes(config, rng, masters, period_by_id))
    counts.update(export_supplier_manual_text(config, rng, masters, list(period_by_id.values())))
    return counts


def export_erp(
    config: GenerationConfig,
    rng: random.Random,
    masters: dict[str, list[dict[str, Any]]],
    truth_by_period: dict[str, list[dict[str, Any]]],
    period_by_id: dict[str, str],
    source_map: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {}
    sites_by_id = {row["site_id"]: row for row in masters["sites"]}
    headers = ["source_row_id", "period", "entity_id", "site_name", "activity_type", "amount", "unit"]
    for period_id, rows in truth_by_period.items():
        period = period_by_id[period_id]
        path = config.out_dir / "raw_sources" / "erp" / f"erp_energy_{period.replace('-', '_')}.csv"
        raw_rows = []
        for index, truth in enumerate(rows, start=1):
            source_row_id = f"ERP-{period.replace('-', '')}-{index:08d}"
            amount, unit = raw_amount_and_unit(rng, str(truth["activity_type"]), float(truth["standardized_amount"]))
            site = sites_by_id[str(truth["site_id"])]
            raw = {
                "source_row_id": source_row_id,
                "period": period,
                "entity_id": truth["entity_id"],
                "site_name": site["site_name"],
                "activity_type": truth["activity_type"],
                "amount": amount,
                "unit": unit,
            }
            mutate_raw(raw, config, rng, anomalies, "erp_energy_csv", path.name, str(truth["truth_activity_id"]))
            raw_rows.append(raw)
            source_map.append(
                {
                    "source_type": "erp_energy_csv",
                    "source_ref": path.name,
                    "source_row_id": source_row_id,
                    "truth_activity_id": truth["truth_activity_id"],
                }
            )
            if rng.random() < float(config.noise.get("duplicate_rate", 0)):
                raw_rows.append(dict(raw))
        counts[f"raw_sources/erp/{path.name}"] = write_csv(path, headers, raw_rows)
    return counts


def export_ems(
    config: GenerationConfig,
    rng: random.Random,
    truth_by_period: dict[str, list[dict[str, Any]]],
    period_by_id: dict[str, str],
    source_map: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {}
    for period_id, rows in truth_by_period.items():
        period = period_by_id[period_id]
        path = config.out_dir / "raw_sources" / "ems" / f"meter_readings_{period.replace('-', '_')}.jsonl"
        count = 0
        with path.open("w", encoding="utf-8") as f:
            for index, truth in enumerate(rows, start=1):
                for reading_index in range(1, 5):
                    source_row_id = f"EMS-{period.replace('-', '')}-{index:08d}-{reading_index:03d}"
                    amount = round(max(0, rng.gauss(float(truth["standardized_amount"]) / 4, 1)), 6)
                    raw = {
                        "source_row_id": source_row_id,
                        "timestamp": f"{period}-{min(28, reading_index * 7):02d}T{rng.randint(0, 23):02d}:00:00Z",
                        "period": period,
                        "site_id": truth["site_id"],
                        "activity_type": truth["activity_type"],
                        "amount": amount,
                        "unit": truth["standardized_unit"],
                    }
                    mutate_raw(raw, config, rng, anomalies, "ems_meter_jsonl", path.name, str(truth["truth_activity_id"]))
                    f.write(json.dumps(raw, ensure_ascii=False) + "\n")
                    source_map.append(
                        {
                            "source_type": "ems_meter_jsonl",
                            "source_ref": path.name,
                            "source_row_id": source_row_id,
                            "truth_activity_id": truth["truth_activity_id"],
                        }
                    )
                    count += 1
        counts[f"raw_sources/ems/{path.name}"] = count
    return counts


def export_mes(
    config: GenerationConfig,
    rng: random.Random,
    masters: dict[str, list[dict[str, Any]]],
    period_by_id: dict[str, str],
) -> dict[str, int]:
    counts = {}
    headers = ["source_row_id", "period", "line_id", "product_id", "production_volume", "volume_unit"]
    for period in period_by_id.values():
        rows = []
        for index, product in enumerate(masters["products"], start=1):
            rows.append(
                {
                    "source_row_id": f"MES-{period.replace('-', '')}-{index:08d}",
                    "period": period,
                    "line_id": product["main_line_id"],
                    "product_id": product["product_id"],
                    "production_volume": rng.randint(500, 250000),
                    "volume_unit": "EA",
                }
            )
        path = config.out_dir / "raw_sources" / "mes" / f"mes_production_{period.replace('-', '_')}.csv"
        counts[f"raw_sources/mes/{path.name}"] = write_csv(path, headers, rows)
    return counts


def export_supplier_manual_text(
    config: GenerationConfig,
    rng: random.Random,
    masters: dict[str, list[dict[str, Any]]],
    periods: list[str],
) -> dict[str, int]:
    counts = {}
    supplier_headers = ["source_row_id", "supplier_name", "site_name", "period", "item", "amount", "unit"]
    supplier_rows = []
    for index in range(max(10, min(200, len(masters["suppliers"]) * 2))):
        activity_type = rng.choice(list(DEFAULT_ACTIVITIES))
        amount, unit = raw_amount_and_unit(rng, activity_type, rng.uniform(100, 10000))
        supplier = rng.choice(masters["suppliers"])
        site = rng.choice(masters["sites"])
        supplier_rows.append(
            {
                "source_row_id": f"SUP-{index + 1:08d}",
                "supplier_name": supplier["supplier_name"],
                "site_name": site["site_name"],
                "period": rng.choice(periods),
                "item": activity_type,
                "amount": amount,
                "unit": unit,
            }
        )
    supplier_path = config.out_dir / "raw_sources" / "suppliers" / "supplier_energy_report_batch_001.csv"
    counts[f"raw_sources/suppliers/{supplier_path.name}"] = write_csv(supplier_path, supplier_headers, supplier_rows)

    manual_headers = ["source_row_id", "month", "factory", "item", "qty", "uom", "memo"]
    manual_rows = []
    for index in range(max(10, len(masters["sites"]) * 5)):
        activity_type = rng.choice(list(DEFAULT_ACTIVITIES))
        amount, unit = raw_amount_and_unit(rng, activity_type, rng.uniform(100, 20000))
        site = rng.choice(masters["sites"])
        manual_rows.append(
            {
                "source_row_id": f"MAN-{index + 1:08d}",
                "month": rng.choice(periods),
                "factory": site["site_name"],
                "item": activity_type,
                "qty": amount,
                "uom": unit,
                "memo": "synthetic manual upload row",
            }
        )
    manual_path = config.out_dir / "raw_sources" / "manual" / "manual_upload_001.csv"
    counts[f"raw_sources/manual/{manual_path.name}"] = write_csv(manual_path, manual_headers, manual_rows)

    field_path = config.out_dir / "raw_sources" / "field_notes" / f"field_notes_{periods[0].replace('-', '_')}.txt"
    field_count = 0
    with field_path.open("w", encoding="utf-8") as f:
        for _ in range(max(10, len(masters["sites"]))):
            site = rng.choice(masters["sites"])
            activity_type = rng.choice(list(DEFAULT_ACTIVITIES))
            amount, unit = raw_amount_and_unit(rng, activity_type, rng.uniform(100, 20000))
            f.write(f"{site['site_name']} {rng.choice(periods)} {activity_type} usage about {amount}{unit}\n")
            field_count += 1
    counts[f"raw_sources/field_notes/{field_path.name}"] = field_count

    email_path = config.out_dir / "raw_sources" / "emails" / f"email_dump_{periods[0].replace('-', '_')}.jsonl"
    email_count = 0
    with email_path.open("w", encoding="utf-8") as f:
        for index in range(max(10, len(masters["sites"]))):
            site = rng.choice(masters["sites"])
            activity_type = rng.choice(list(DEFAULT_ACTIVITIES))
            amount, unit = raw_amount_and_unit(rng, activity_type, rng.uniform(100, 20000))
            f.write(
                json.dumps(
                    {
                        "source_row_id": f"MAIL-{index + 1:08d}",
                        "subject": "Synthetic ESG activity submission",
                        "body": f"{site['site_name']} {rng.choice(periods)} {activity_type} {amount} {unit}",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            email_count += 1
    counts[f"raw_sources/emails/{email_path.name}"] = email_count
    return counts


def raw_amount_and_unit(rng: random.Random, activity_type: str, standardized_amount: float) -> tuple[float, str]:
    unit, multiplier = rng.choice(UNIT_VARIANTS.get(activity_type, [(DEFAULT_ACTIVITIES[activity_type]["standard_unit"], 1.0)]))
    return round(standardized_amount * multiplier, 6), unit


def mutate_raw(
    row: dict[str, Any],
    config: GenerationConfig,
    rng: random.Random,
    anomalies: list[dict[str, Any]],
    source_type: str,
    source_ref: str,
    truth_activity_id: str,
) -> None:
    def record(anomaly_type: str) -> None:
        anomalies.append(
            {
                "anomaly_id": f"ANOM-{len(anomalies) + 1:09d}",
                "source_type": source_type,
                "source_ref": source_ref,
                "source_row_id": row["source_row_id"],
                "truth_activity_id": truth_activity_id,
                "anomaly_type": anomaly_type,
            }
        )

    if rng.random() < float(config.noise.get("missing_rate", 0)) and "amount" in row:
        row["amount"] = ""
        record("missing_amount")
    if rng.random() < float(config.noise.get("unit_error_rate", 0)) and "unit" in row:
        row["unit"] = rng.choice(WRONG_UNITS.get(str(row.get("activity_type")), ["unknown_unit"]))
        record("unit_error")
    if rng.random() < float(config.noise.get("period_error_rate", 0)) and "period" in row:
        row["period"] = add_month(str(row["period"]), rng.choice([-1, 1]))
        record("period_error")
    if rng.random() < float(config.noise.get("site_alias_rate", 0)) and "site_name" in row:
        row["site_name"] = str(row["site_name"]).split()[0]
        record("site_alias")
    if rng.random() < float(config.noise.get("outlier_rate", 0)) and "amount" in row and row["amount"] != "":
        row["amount"] = round(float(row["amount"]) * rng.uniform(3, 12), 6)
        record("outlier_amount")
    if rng.random() < float(config.noise.get("negative_amount_rate", 0)) and "amount" in row and row["amount"] != "":
        row["amount"] = -abs(float(row["amount"]))
        record("negative_amount")


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = list(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)
