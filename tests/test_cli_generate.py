from __future__ import annotations

import json
import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliGenerateTests(unittest.TestCase):
    def test_module_generate_creates_phase2_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "synthetic_esg",
                    "generate",
                    "--out-dir",
                    str(out_dir),
                    "--seed",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out_dir / "master").is_dir())
            self.assertTrue((out_dir / "raw_sources").is_dir())
            self.assertTrue((out_dir / "truth").is_dir())

            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            report = json.loads((out_dir / "generation_report.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["generator"], "synthetic_esg")
            self.assertEqual(manifest["phase"], "phase3_profile_config")
            self.assertEqual(manifest["seed"], 1)
            self.assertEqual(report["status"], "created")
            self.assertEqual(report["output_contract"], ["master", "raw_sources", "truth"])

    def test_profile_values_and_cli_overrides_are_reflected_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "profiled"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "synthetic_esg",
                    "generate",
                    "--profile",
                    "profiles/lges_smoke.yaml",
                    "--out-dir",
                    str(out_dir),
                    "--seed",
                    "7",
                    "--sites",
                    "9",
                    "--suppliers",
                    "25",
                    "--months",
                    "3",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            report = json.loads((out_dir / "generation_report.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["company"]["name"], "LG Energy Solution Synthetic")
            self.assertEqual(manifest["company"]["profile"], "lges_smoke")
            self.assertEqual(manifest["period"]["start_month"], "2026-01")
            self.assertEqual(manifest["scale"]["sites"], 9)
            self.assertEqual(manifest["scale"]["suppliers"], 25)
            self.assertEqual(manifest["scale"]["months"], 3)
            self.assertEqual(manifest["activity_types"]["electricity"]["standard_unit"], "kWh")
            self.assertAlmostEqual(manifest["source_mix"]["erp_energy_csv"], 0.30)
            self.assertAlmostEqual(manifest["noise"]["unit_error_rate"], 0.03)
            self.assertTrue(manifest["output"]["include_ground_truth"])
            self.assertEqual(report["profile"]["company_profile"], "lges_smoke")
            self.assertEqual(report["profile"]["source_count"], 7)
            self.assertEqual(report["profile"]["noise_rule_count"], 8)

    def test_phase2_package_skeleton_modules_are_importable(self) -> None:
        module_names = [
            "synthetic_esg.cli",
            "synthetic_esg.config",
            "synthetic_esg.random_state",
            "synthetic_esg.domain.battery_company",
            "synthetic_esg.domain.e_energy",
            "synthetic_esg.generators.master_data",
            "synthetic_esg.generators.organization",
            "synthetic_esg.generators.sites",
            "synthetic_esg.generators.production_lines",
            "synthetic_esg.generators.products",
            "synthetic_esg.generators.suppliers",
            "synthetic_esg.generators.meters",
            "synthetic_esg.generators.activity",
            "synthetic_esg.generators.production",
            "synthetic_esg.generators.emissions_truth",
            "synthetic_esg.exporters.master_csv",
            "synthetic_esg.exporters.erp_energy",
            "synthetic_esg.exporters.mes_production",
            "synthetic_esg.exporters.ems_meter_jsonl",
            "synthetic_esg.exporters.supplier_excel",
            "synthetic_esg.exporters.field_notes",
            "synthetic_esg.exporters.email_dump",
            "synthetic_esg.exporters.manual_uploads",
            "synthetic_esg.noise.missingness",
            "synthetic_esg.noise.duplicates",
            "synthetic_esg.noise.unit_errors",
            "synthetic_esg.noise.period_errors",
            "synthetic_esg.noise.site_aliases",
            "synthetic_esg.noise.outliers",
            "synthetic_esg.noise.boundary_errors",
            "synthetic_esg.reports.manifest",
            "synthetic_esg.reports.generation_report",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))


if __name__ == "__main__":
    unittest.main()
