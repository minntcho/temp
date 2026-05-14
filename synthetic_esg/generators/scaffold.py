from __future__ import annotations

import json
from pathlib import Path

from synthetic_esg import __version__
from synthetic_esg.config import GenerationConfig


OUTPUT_CONTRACT = ["master", "raw_sources", "truth"]

MASTER_FILE_HEADERS = {
    "legal_entities.csv": [
        "entity_id",
        "entity_name",
        "country",
        "ownership_type",
        "reporting_included",
    ],
    "business_units.csv": ["business_unit_id", "business_unit_name", "entity_id"],
    "sites.csv": ["site_id", "site_name", "entity_id", "country", "site_type", "reporting_included"],
    "production_lines.csv": ["line_id", "line_name", "site_id", "line_type"],
    "products.csv": ["product_id", "product_name", "product_category", "main_line_id"],
    "suppliers.csv": ["supplier_id", "supplier_name", "country", "supplier_tier"],
    "meters.csv": ["meter_id", "meter_name", "site_id", "activity_type", "unit"],
    "reporting_calendar.csv": ["period_id", "year", "month", "quarter", "fiscal_year"],
    "emission_factors.csv": [
        "factor_id",
        "activity_type",
        "unit",
        "scope_category",
        "emission_factor",
        "factor_unit",
    ],
    "unit_conversions.csv": ["conversion_id", "activity_type", "from_unit", "to_unit", "multiplier", "offset"],
}

TRUTH_FILE_HEADERS = {
    "canonical_activity.csv": [
        "truth_activity_id",
        "period_id",
        "entity_id",
        "site_id",
        "activity_type",
        "standardized_amount",
        "standardized_unit",
    ],
    "canonical_emissions.csv": ["truth_emission_id", "truth_activity_id", "scope_category", "co2e_kg", "factor_id"],
    "source_to_truth_map.csv": ["source_type", "source_ref", "source_row_id", "truth_activity_id"],
    "injected_anomalies.csv": [
        "anomaly_id",
        "source_type",
        "source_ref",
        "source_row_id",
        "truth_activity_id",
        "anomaly_type",
    ],
}

RAW_SOURCE_DIRS = ["erp", "mes", "ems", "suppliers", "manual", "field_notes", "emails"]


def create_phase2_output(config: GenerationConfig) -> Path:
    config.out_dir.mkdir(parents=True, exist_ok=True)
    for dirname in OUTPUT_CONTRACT:
        (config.out_dir / dirname).mkdir(parents=True, exist_ok=True)
    for dirname in RAW_SOURCE_DIRS:
        (config.out_dir / "raw_sources" / dirname).mkdir(parents=True, exist_ok=True)
    for filename, headers in MASTER_FILE_HEADERS.items():
        write_header_csv(config.out_dir / "master" / filename, headers)
    for filename, headers in TRUTH_FILE_HEADERS.items():
        write_header_csv(config.out_dir / "truth" / filename, headers)

    manifest = {
        "generator": "synthetic_esg",
        "generator_version": __version__,
        "phase": "phase4_output_contract",
        "seed": config.seed,
        "profile": str(config.profile) if config.profile else None,
        "company": config.company,
        "period": config.period,
        "scale": config.scale,
        "activity_types": config.activity_types,
        "source_mix": config.source_mix,
        "noise": config.noise,
        "output": config.output,
        "outputs": {
            "master": "master/",
            "raw_sources": "raw_sources/",
            "truth": "truth/",
            "master_files": list(MASTER_FILE_HEADERS),
            "truth_files": list(TRUTH_FILE_HEADERS),
            "raw_source_dirs": RAW_SOURCE_DIRS,
        },
    }
    report = {
        "status": "created",
        "phase": "phase4_output_contract",
        "output_contract": OUTPUT_CONTRACT,
        "output_files": {
            "master": len(MASTER_FILE_HEADERS),
            "truth": len(TRUTH_FILE_HEADERS),
            "raw_source_dirs": len(RAW_SOURCE_DIRS),
        },
        "profile": {
            "company_profile": config.company.get("profile"),
            "source_count": len(config.source_mix),
            "noise_rule_count": len(config.noise),
        },
        "record_counts": {},
        "notes": "Phase 3 loads profile configuration and creates the output contract skeleton.",
    }

    manifest_path = config.out_dir / "manifest.json"
    write_json(manifest_path, manifest)
    write_json(config.out_dir / "generation_report.json", report)
    return manifest_path


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_header_csv(path: Path, headers: list[str]) -> None:
    path.write_text(",".join(headers) + "\n", encoding="utf-8")
