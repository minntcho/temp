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
    def test_module_generate_creates_output_contract(self) -> None:
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
            self.assertEqual(manifest["phase"], "phase5_quality_metadata")
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

    def test_generate_creates_fixed_master_truth_and_raw_source_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "contract"

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
                    "11",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            expected_master_files = {
                "legal_entities.csv": "entity_id,entity_name,country,ownership_type,reporting_included",
                "business_units.csv": "business_unit_id,business_unit_name,entity_id",
                "sites.csv": "site_id,site_name,entity_id,country,site_type,reporting_included",
                "production_lines.csv": "line_id,line_name,site_id,line_type",
                "products.csv": "product_id,product_name,product_category,main_line_id",
                "suppliers.csv": "supplier_id,supplier_name,country,supplier_tier",
                "meters.csv": "meter_id,meter_name,site_id,activity_type,unit",
                "reporting_calendar.csv": "period_id,year,month,quarter,fiscal_year",
                "emission_factors.csv": "factor_id,activity_type,unit,scope_category,emission_factor,factor_unit",
                "unit_conversions.csv": "conversion_id,activity_type,from_unit,to_unit,multiplier,offset",
            }
            for filename, header in expected_master_files.items():
                path = out_dir / "master" / filename
                self.assertTrue(path.is_file(), filename)
                self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0], header)

            expected_truth_files = {
                "canonical_activity.csv": "truth_activity_id,period_id,entity_id,site_id,activity_type,standardized_amount,standardized_unit",
                "canonical_emissions.csv": "truth_emission_id,truth_activity_id,scope_category,co2e_kg,factor_id",
                "source_to_truth_map.csv": "source_type,source_ref,source_row_id,truth_activity_id",
                "injected_anomalies.csv": "anomaly_id,source_type,source_ref,source_row_id,truth_activity_id,anomaly_type",
            }
            for filename, header in expected_truth_files.items():
                path = out_dir / "truth" / filename
                self.assertTrue(path.is_file(), filename)
                self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0], header)

            for dirname in ("erp", "mes", "ems", "suppliers", "manual", "field_notes", "emails"):
                self.assertTrue((out_dir / "raw_sources" / dirname).is_dir(), dirname)

            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["phase"], "phase5_quality_metadata")
            self.assertEqual(set(manifest["outputs"]["master_files"]), set(expected_master_files))
            self.assertEqual(set(manifest["outputs"]["truth_files"]), set(expected_truth_files))
            self.assertEqual(
                manifest["outputs"]["raw_source_dirs"],
                ["erp", "mes", "ems", "suppliers", "manual", "field_notes", "emails"],
            )

    def test_same_seed_and_profile_produce_same_reproducibility_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first_out = Path(tmp) / "first"
            second_out = Path(tmp) / "second"

            for out_dir in (first_out, second_out):
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
                        "42",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            first_manifest = json.loads((first_out / "manifest.json").read_text(encoding="utf-8"))
            second_manifest = json.loads((second_out / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(
                first_manifest["reproducibility"]["config_hash"],
                second_manifest["reproducibility"]["config_hash"],
            )
            self.assertEqual(first_manifest["reproducibility"]["seed"], 42)
            self.assertEqual(first_manifest["reproducibility"]["profile"], "lges_smoke")

    def test_manifest_declares_truth_relationships_and_noise_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "quality"

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

            self.assertEqual(
                manifest["truth_contract"]["relationships"]["source_to_truth_map.truth_activity_id"],
                "canonical_activity.truth_activity_id",
            )
            self.assertEqual(
                manifest["truth_contract"]["relationships"]["canonical_emissions.truth_activity_id"],
                "canonical_activity.truth_activity_id",
            )
            self.assertEqual(manifest["truth_contract"]["primary_keys"]["canonical_activity.csv"], "truth_activity_id")
            self.assertEqual(report["quality_checks"]["truth_relationships_declared"], "ok")
            self.assertEqual(report["quality_checks"]["noise_rates_valid"], "ok")
            self.assertAlmostEqual(report["noise"]["total_configured_rate"], 0.178)
            self.assertEqual(report["noise"]["rates"]["unit_error_rate"], 0.03)

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
            "synthetic_esg.exporters.chunk_writer",
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
