from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .profile import load_profile


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
            scale["scale"] = args.scale
        for attr in ("months", "sites", "lines", "products", "suppliers"):
            value = getattr(args, attr)
            if value is not None:
                scale[attr] = value

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
