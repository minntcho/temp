from __future__ import annotations

import json
from pathlib import Path

from synthetic_esg import __version__
from synthetic_esg.config import GenerationConfig


OUTPUT_CONTRACT = ["master", "raw_sources", "truth"]


def create_phase2_output(config: GenerationConfig) -> Path:
    config.out_dir.mkdir(parents=True, exist_ok=True)
    for dirname in OUTPUT_CONTRACT:
        (config.out_dir / dirname).mkdir(parents=True, exist_ok=True)

    manifest = {
        "generator": "synthetic_esg",
        "generator_version": __version__,
        "phase": "phase3_profile_config",
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
        },
    }
    report = {
        "status": "created",
        "phase": "phase3_profile_config",
        "output_contract": OUTPUT_CONTRACT,
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
