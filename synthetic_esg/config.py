from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .profile import load_profile

SCALE_PRESETS: dict[str, dict[str, int]] = {
    "smoke": {
        "legal_entities": 2,
        "business_units": 2,
        "sites": 3,
        "production_lines": 5,
        "products": 6,
        "suppliers": 10,
        "meters": 20,
    },
    "enterprise": {
        "legal_entities": 12,
        "business_units": 6,
        "sites": 80,
        "production_lines": 500,
        "products": 300,
        "suppliers": 2000,
        "meters": 5000,
    },
    "large": {
        "legal_entities": 18,
        "business_units": 8,
        "sites": 120,
        "production_lines": 900,
        "products": 500,
        "suppliers": 5000,
        "meters": 12000,
    },
    "stress": {
        "legal_entities": 24,
        "business_units": 12,
        "sites": 200,
        "production_lines": 1500,
        "products": 900,
        "suppliers": 10000,
        "meters": 30000,
    },
}


@dataclass(frozen=True)
class GenerationConfig:
    out_dir: Path
    seed: int
    profile: Path | None = None
    company: dict[str, Any] = field(default_factory=dict)
    period: dict[str, Any] = field(default_factory=dict)
    scale: dict[str, Any] = field(default_factory=dict)
    activity_types: dict[str, Any] = field(default_factory=dict)
    source_mix: dict[str, Any] = field(default_factory=dict)
    noise: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "GenerationConfig":
        profile_data = load_profile(args.profile)
        scale = dict(profile_data.get("scale", {}))
        if args.scale is not None:
            scale.update(SCALE_PRESETS[args.scale])
        for attr, target in (
            ("months", "months"),
            ("sites", "sites"),
            ("lines", "production_lines"),
            ("products", "products"),
            ("suppliers", "suppliers"),
            ("meters", "meters"),
        ):
            value = getattr(args, attr)
            if value is not None:
                scale[target] = value

        return cls(
            out_dir=args.out_dir,
            seed=args.seed,
            profile=args.profile,
            company=dict(profile_data.get("company", {})),
            period=dict(profile_data.get("period", {})),
            scale=scale,
            activity_types=dict(profile_data.get("activity_types", {})),
            source_mix=dict(profile_data.get("source_mix", {})),
            noise=dict(profile_data.get("noise", {})),
            output=dict(profile_data.get("output", {})),
        )

    def scale_overrides(self) -> dict[str, int | str]:
        return dict(self.scale)
