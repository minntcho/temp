from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VisualizationTests(unittest.TestCase):
    def test_visualize_creates_plotly_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            generate = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "synthetic_esg",
                    "generate",
                    "--profile",
                    "profiles/lges_smoke.yaml",
                    "--out-dir",
                    str(run_dir),
                    "--meters",
                    "40",
                    "--seed",
                    "41",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generate.returncode, 0, generate.stderr)

            visualize = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "synthetic_esg",
                    "visualize",
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(visualize.returncode, 0, visualize.stderr)

            report_path = run_dir / "reports" / "distribution_dashboard.html"
            self.assertTrue(report_path.exists())
            html = report_path.read_text(encoding="utf-8").lower()
            self.assertIn("synthetic esg distribution report", html)
            self.assertIn("plotly", html)
            self.assertIn("activity amount distribution", html)
            self.assertIn("analysis reading guide", html)
            self.assertIn("analysis-guide", html)
            self.assertIn("activity amount histogram", html)
            self.assertIn("activity amount box plot", html)
            self.assertIn("site type distribution", html)
            self.assertIn("monthly activity trend", html)
            self.assertIn("why-run-this", html)
            self.assertIn("how-to-read-this", html)
            self.assertIn("what-to-check-next", html)
            self.assertIn("term-trigger", html)
            self.assertIn("data-term", html)
            self.assertIn("developer-drawer", html)
            self.assertIn("developer information", html)
            self.assertIn("aria-expanded", html)
            self.assertIn("toggledeveloperdrawer", html)
            self.assertIn("closetermpopover", html)
            self.assertNotIn("non-expert", html)
            self.assertNotIn("beginner", html)


if __name__ == "__main__":
    unittest.main()
