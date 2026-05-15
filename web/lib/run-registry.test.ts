import { mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  buildRunId,
  getRunFilePath,
  isValidRunId,
  listRuns,
  readRunBundle,
  writeWebRun,
  type WebRun,
} from "@/lib/run-registry";

describe("run registry", () => {
  let repoRoot: string;

  beforeEach(async () => {
    repoRoot = await mkdtemp(path.join(os.tmpdir(), "synthetic-esg-runs-"));
  });

  afterEach(async () => {
    await rm(repoRoot, { recursive: true, force: true });
  });

  it("builds stable run ids from timestamp and seed", () => {
    const runId = buildRunId({
      now: new Date("2026-05-15T05:30:12.345Z"),
      seed: 42,
      uniqueSuffix: "abc123",
    });

    expect(runId).toBe("20260515-143012-345-seed42-abc123");
  });

  it("keeps run ids unique for repeated runs in the same second with the same seed", () => {
    const now = new Date("2026-05-15T05:30:12.345Z");

    const runIds = new Set([
      buildRunId({ now, seed: 42 }),
      buildRunId({ now, seed: 42 }),
      buildRunId({ now, seed: 42 }),
    ]);

    expect(runIds.size).toBe(3);
  });

  it("rejects path traversal run ids", () => {
    expect(isValidRunId("20260515-053012-seed42")).toBe(true);
    expect(isValidRunId("../20260515-053012-seed42")).toBe(false);
    expect(isValidRunId("20260515/053012-seed42")).toBe(false);
  });

  it("resolves run files only when they stay inside the run directory", () => {
    const runDir = path.join(repoRoot, "out", "web-runs", "safe-run");

    expect(getRunFilePath(runDir, "reports/distribution_dashboard.html")).toBe(
      path.join(runDir, "reports", "distribution_dashboard.html"),
    );
    expect(() => getRunFilePath(runDir, "../secret.txt")).toThrow("Invalid run file path");
    expect(() => getRunFilePath(runDir, "reports/../../secret.txt")).toThrow("Invalid run file path");
  });

  it("lists persisted runs newest first", async () => {
    await writeWebRun(repoRoot, makeRun("older", "2026-05-15T01:00:00.000Z"));
    await writeWebRun(repoRoot, makeRun("newer", "2026-05-15T02:00:00.000Z"));

    const runs = await listRuns(repoRoot);

    expect(runs.map((run) => run.runId)).toEqual(["newer", "older"]);
  });

  it("reads a run bundle with generated metadata when files exist", async () => {
    const run = makeRun("bundle", "2026-05-15T03:00:00.000Z");
    await writeWebRun(repoRoot, run);

    const runDir = path.join(repoRoot, run.runDir);
    await writeFile(
      path.join(runDir, "manifest.json"),
      JSON.stringify({ seed: 7, outputs: { master_files: ["sites.csv"] } }),
    );
    await writeFile(
      path.join(runDir, "generation_report.json"),
      JSON.stringify({ status: "created", record_counts: { "master/sites.csv": 3 } }),
    );

    const bundle = await readRunBundle(repoRoot, "bundle");

    expect(bundle.run.runId).toBe("bundle");
    expect(bundle.manifest?.seed).toBe(7);
    expect(bundle.generationReport?.record_counts).toEqual({ "master/sites.csv": 3 });
  });
});

function makeRun(runId: string, startedAt: string): WebRun {
  return {
    runId,
    status: "succeeded",
    profile: "profiles/lges_smoke.yaml",
    profileName: "lges_smoke",
    seed: 7,
    command: "python -m synthetic_esg generate --profile profiles/lges_smoke.yaml",
    visualizeCommand: "python -m synthetic_esg visualize --run-dir out/web-runs/" + runId,
    startedAt,
    finishedAt: startedAt,
    durationMs: 1000,
    runDir: `out/web-runs/${runId}`,
    manifestPath: "manifest.json",
    generationReportPath: "generation_report.json",
    visualReportPath: "reports/distribution_dashboard.html",
    stdout: "",
    stderr: "",
  };
}
