from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


class RowGenerationTests(unittest.TestCase):
    def test_generate_populates_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "rows"
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
                    "17",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater(row_count(out_dir / "master" / "sites.csv"), 0)
            self.assertGreater(row_count(out_dir / "master" / "meters.csv"), 0)
            self.assertGreater(row_count(out_dir / "truth" / "canonical_activity.csv"), 0)
            self.assertGreater(row_count(out_dir / "truth" / "canonical_emissions.csv"), 0)
            self.assertTrue(any((out_dir / "raw_sources" / "erp").glob("*.csv")))
            self.assertTrue(any((out_dir / "raw_sources" / "ems").glob("*.jsonl")))
            report = json.loads((out_dir / "generation_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["quality_checks"]["rows_generated"], "ok")


if __name__ == "__main__":
    unittest.main()
