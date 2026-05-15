import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RunPage from "./page";
import { getRunDir, writeWebRun, type WebRun } from "@/lib/run-registry";

describe("run detail page", () => {
  let repoRoot: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    repoRoot = await mkdtemp(path.join(os.tmpdir(), "synthetic-esg-run-page-"));
    cwdSpy = vi.spyOn(process, "cwd").mockReturnValue(path.join(repoRoot, "web"));
  });

  afterEach(async () => {
    cwdSpy.mockRestore();
    await rm(repoRoot, { recursive: true, force: true });
  });

  it("keeps the report as the main content and groups developer-only sections in a separate rail", async () => {
    const run = makeRun("ready-run");
    await writeWebRun(repoRoot, run);
    const runDir = getRunDir(repoRoot, run.runId);
    await writeFile(path.join(runDir, "manifest.json"), JSON.stringify({ seed: 7, outputs: ["sites.csv"] }), "utf-8");
    await writeFile(path.join(runDir, "generation_report.json"), JSON.stringify({ record_counts: { sites: 3 } }), "utf-8");
    const reportPath = path.join(runDir, "reports", "distribution_dashboard.html");
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(reportPath, "<!doctype html><html><body>report</body></html>", "utf-8");

    const markup = renderToStaticMarkup(await RunPage({ params: Promise.resolve({ runId: run.runId }) }));

    expect(markup).toContain('class="report-workspace"');
    expect(markup).toContain('class="developer-rail panel"');
    expect(markup.indexOf('id="report-title"')).toBeLessThan(markup.indexOf('id="developer-title"'));

    const developerRail = markup.slice(markup.indexOf('id="developer-title"'));
    expect(developerRail).toContain("Artifact");
    expect(developerRail).toContain("Run files");
    expect(developerRail).toContain("Web Run");
    expect(developerRail).toContain("Execution metadata");
    expect(developerRail).toContain("Manifest");
    expect(developerRail).toContain("Generation contract");
  });
});

function makeRun(runId: string): WebRun {
  return {
    runId,
    status: "succeeded",
    profile: "profiles/lges_smoke.yaml",
    profileName: "lges_smoke",
    seed: 7,
    command: "python -m synthetic_esg generate --profile profiles/lges_smoke.yaml",
    visualizeCommand: "python -m synthetic_esg visualize --run-dir out/web-runs/" + runId,
    startedAt: "2026-05-15T03:00:00.000Z",
    finishedAt: "2026-05-15T03:00:01.000Z",
    durationMs: 1000,
    runDir: `out/web-runs/${runId}`,
    manifestPath: "manifest.json",
    generationReportPath: "generation_report.json",
    visualReportPath: "reports/distribution_dashboard.html",
    stdout: "",
    stderr: "",
  };
}
