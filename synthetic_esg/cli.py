from __future__ import annotations

import argparse
from pathlib import Path

from .config import SCALE_PRESETS, GenerationConfig
from .generators.scaffold import create_phase2_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synthetic_esg",
        description="LGES-scale synthetic ESG data generator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        help="Generate synthetic ESG data outputs",
    )
    generate.add_argument("--profile", type=Path, default=None)
    generate.add_argument("--out-dir", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--scale", choices=sorted(SCALE_PRESETS), default=None)
    generate.add_argument("--months", type=int, default=None)
    generate.add_argument("--sites", type=int, default=None)
    generate.add_argument("--lines", type=int, default=None)
    generate.add_argument("--products", type=int, default=None)
    generate.add_argument("--suppliers", type=int, default=None)
    generate.add_argument("--meters", type=int, default=None)
    generate.set_defaults(handler=handle_generate)

    return parser


def handle_generate(args: argparse.Namespace) -> int:
    config = GenerationConfig.from_args(args)
    manifest_path = create_phase2_output(config)
    print(f"[OK] synthetic ESG data generated: {config.out_dir.resolve()}")
    print(f"[OK] manifest: {manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
