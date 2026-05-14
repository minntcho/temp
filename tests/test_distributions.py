from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_generation_report_includes_distribution_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "distributed"
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
                    "--meters",
                    "80",
                    "--seed",
                    "31",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            report = json.loads((out_dir / "generation_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["quality_checks"]["distribution_stats_recorded"], "ok")
            self.assertTrue(report["distribution_stats"])

            for stats in report["distribution_stats"].values():
                self.assertGreater(stats["count"], 0)
                self.assertGreaterEqual(stats["p50"], stats["min"])
                self.assertGreaterEqual(stats["p95"], stats["p50"])
                self.assertGreaterEqual(stats["p99"], stats["p95"])
                self.assertGreaterEqual(stats["max"], stats["p99"])


if __name__ == "__main__":
    unittest.main()
