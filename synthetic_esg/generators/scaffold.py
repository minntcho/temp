from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from synthetic_esg import __version__
from synthetic_esg.config import GenerationConfig
from synthetic_esg.generators.full_factory import populate_output_rows


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

TRUTH_CONTRACT = {
    "primary_keys": {
        "canonical_activity.csv": "truth_activity_id",
        "canonical_emissions.csv": "truth_emission_id",
        "source_to_truth_map.csv": ["source_type", "source_ref", "source_row_id"],
        "injected_anomalies.csv": "anomaly_id",
    },
    "relationships": {
        "source_to_truth_map.truth_activity_id": "canonical_activity.truth_activity_id",
        "canonical_emissions.truth_activity_id": "canonical_activity.truth_activity_id",
        "injected_anomalies.truth_activity_id": "canonical_activity.truth_activity_id",
    },
}


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

    generated_metadata = populate_output_rows(
        config=config,
        master_headers=MASTER_FILE_HEADERS,
        truth_headers=TRUTH_FILE_HEADERS,
    )
    distribution_stats = generated_metadata.pop("__distribution_stats__", {})
    record_counts = generated_metadata

    config_hash = build_config_hash(config)
    noise_validation = validate_noise_rates(config.noise)

    manifest = {
        "generator": "synthetic_esg",
        "generator_version": __version__,
        "phase": "phase5_quality_metadata",
        "seed": config.seed,
        "profile": str(config.profile) if config.profile else None,
        "company": config.company,
        "period": config.period,
        "scale": config.scale,
        "activity_types": config.activity_types,
        "source_mix": config.source_mix,
        "noise": config.noise,
        "output": config.output,
        "reproducibility": {
            "seed": config.seed,
            "profile": config.company.get("profile"),
            "config_hash": config_hash,
        },
        "truth_contract": TRUTH_CONTRACT,
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
        "phase": "phase5_quality_metadata",
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
        "quality_checks": {
            "truth_relationships_declared": "ok",
            "noise_rates_valid": "ok" if noise_validation["valid"] else "failed",
            "rows_generated": "ok" if any(record_counts.values()) else "failed",
            "distribution_stats_recorded": "ok" if distribution_stats else "failed",
        },
        "noise": {
            "rates": config.noise,
            "total_configured_rate": noise_validation["total"],
        },
        "record_counts": record_counts,
        "distribution_stats": distribution_stats,
        "notes": "Phase 6 populates the generation-only output contract with synthetic master, raw source, and truth rows.",
    }

    manifest_path = config.out_dir / "manifest.json"
    write_json(manifest_path, manifest)
    write_json(config.out_dir / "generation_report.json", report)
    return manifest_path


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_header_csv(path: Path, headers: list[str]) -> None:
    path.write_text(",".join(headers) + "\n", encoding="utf-8")


def build_config_hash(config: GenerationConfig) -> str:
    payload = {
        "seed": config.seed,
        "company": config.company,
        "period": config.period,
        "scale": config.scale,
        "activity_types": config.activity_types,
        "source_mix": config.source_mix,
        "noise": config.noise,
        "output": config.output,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_noise_rates(noise: dict[str, Any]) -> dict[str, Any]:
    total = 0.0
    valid = True
    for value in noise.values():
        if not isinstance(value, (int, float)):
            valid = False
            continue
        if value < 0 or value > 1:
            valid = False
        total += float(value)
    return {"valid": valid and total <= 1.0, "total": round(total, 6)}
