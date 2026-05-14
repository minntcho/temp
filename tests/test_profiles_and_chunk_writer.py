from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from synthetic_esg.config import SCALE_PRESETS
from synthetic_esg.exporters.chunk_writer import write_csv_chunks
from synthetic_esg.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]


class ProfileAndChunkWriterTests(unittest.TestCase):
    def test_default_profile_generates_manifest_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = "profiles/lges_smoke.yaml"
            out_dir = Path(tmp) / Path(profile).stem
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "synthetic_esg",
                    "generate",
                    "--profile",
                    profile,
                    "--out-dir",
                    str(out_dir),
                    "--seed",
                    "9",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, f"{profile}: {result.stderr}")
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["company"]["profile"], Path(profile).stem)
            self.assertIn("chunk_size", manifest["output"])
            self.assertTrue(manifest["output"]["partition_by_month"])
            self.assertTrue(manifest["output"]["include_ground_truth"])

    def test_non_default_profiles_parse_without_generation(self) -> None:
        profiles = [
            "profiles/lges_enterprise.yaml",
            "profiles/experimental/lges_large.yaml",
            "profiles/experimental/lges_stress.yaml",
        ]

        for profile in profiles:
            profile_data = load_profile(ROOT / profile)
            self.assertEqual(profile_data["company"]["profile"], Path(profile).stem)

    def test_large_and_stress_are_not_default_scale_presets(self) -> None:
        self.assertNotIn("large", SCALE_PRESETS)
        self.assertNotIn("stress", SCALE_PRESETS)

    def test_chunk_writer_splits_csv_rows_with_headers(self) -> None:
        rows = [
            {"id": "1", "period": "2026-01", "amount": 10},
            {"id": "2", "period": "2026-01", "amount": 20},
            {"id": "3", "period": "2026-02", "amount": 30},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            written = write_csv_chunks(
                out_dir=Path(tmp),
                file_stem="activity",
                headers=["id", "period", "amount"],
                rows=rows,
                chunk_size=2,
            )

            self.assertEqual([p.name for p in written], ["activity_part_0001.csv", "activity_part_0002.csv"])
            with written[0].open("r", encoding="utf-8", newline="") as f:
                first_rows = list(csv.DictReader(f))
            with written[1].open("r", encoding="utf-8", newline="") as f:
                second_rows = list(csv.DictReader(f))

            self.assertEqual([row["id"] for row in first_rows], ["1", "2"])
            self.assertEqual([row["id"] for row in second_rows], ["3"])
            self.assertEqual(written[0].read_text(encoding="utf-8").splitlines()[0], "id,period,amount")


if __name__ == "__main__":
    unittest.main()
