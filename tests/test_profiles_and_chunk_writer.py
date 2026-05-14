from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from synthetic_esg.exporters.chunk_writer import write_csv_chunks


ROOT = Path(__file__).resolve().parents[1]


class ProfileAndChunkWriterTests(unittest.TestCase):
    def test_standard_profiles_generate_manifest_metadata(self) -> None:
        profiles = [
            "profiles/lges_smoke.yaml",
            "profiles/lges_enterprise.yaml",
            "profiles/lges_large.yaml",
            "profiles/lges_stress.yaml",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            for profile in profiles:
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
