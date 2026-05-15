import { describe, expect, it } from "vitest";

import { buildSmokeRunPlan, normalizeRunRequest } from "@/lib/python-runner";

describe("python runner", () => {
  it("normalizes empty create-run requests to the smoke profile and seed 42", () => {
    expect(normalizeRunRequest({})).toEqual({
      profile: "profiles/lges_smoke.yaml",
      profileName: "lges_smoke",
      seed: 42,
    });
  });

  it("rejects non-integer seeds before spawning Python", () => {
    expect(() => normalizeRunRequest({ seed: 1.5 })).toThrow("seed must be an integer");
    expect(() => normalizeRunRequest({ seed: "abc" })).toThrow("seed must be an integer");
  });

  it("builds the generate and visualize commands for a reusable run directory", () => {
    const plan = buildSmokeRunPlan({
      repoRoot: "C:\\repo",
      now: new Date("2026-05-15T05:30:12.345Z"),
      seed: 7,
    });

    expect(plan.run.runId).toBe("20260515-143012-seed7");
    expect(plan.run.runDir).toBe("out/web-runs/20260515-143012-seed7");
    expect(plan.run.visualReportPath).toBe("reports/distribution_dashboard.html");
    expect(plan.generate).toEqual({
      command: "python",
      args: [
        "-m",
        "synthetic_esg",
        "generate",
        "--profile",
        "profiles/lges_smoke.yaml",
        "--out-dir",
        "out/web-runs/20260515-143012-seed7",
        "--seed",
        "7",
      ],
      cwd: "C:\\repo",
    });
    expect(plan.visualize.args).toEqual([
      "-m",
      "synthetic_esg",
      "visualize",
      "--run-dir",
      "out/web-runs/20260515-143012-seed7",
      "--out-dir",
      "out/web-runs/20260515-143012-seed7/reports",
      "--plotly-js",
      "cdn",
    ]);
  });

  it("uses an explicit Python command when the server process has a minimal PATH", () => {
    const plan = buildSmokeRunPlan({
      repoRoot: "C:\\repo",
      now: new Date("2026-05-15T05:30:12.345Z"),
      pythonCommand: "C:\\Python311\\python.exe",
      seed: 7,
    });

    expect(plan.generate.command).toBe("C:\\Python311\\python.exe");
    expect(plan.visualize.command).toBe("C:\\Python311\\python.exe");
    expect(plan.run.command.startsWith("C:\\Python311\\python.exe -m synthetic_esg generate")).toBe(true);
  });
});
