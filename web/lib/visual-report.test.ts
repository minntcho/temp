import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { getRunDir, writeWebRun, type WebRun } from "@/lib/run-registry";
import {
  isCurrentVisualReportHtml,
  readCurrentVisualReportHtml,
  VISUAL_REPORT_TEMPLATE_MARKER,
} from "@/lib/visual-report";

describe("visual report freshness", () => {
  let repoRoot: string;

  beforeEach(async () => {
    repoRoot = await mkdtemp(path.join(os.tmpdir(), "synthetic-esg-visual-report-"));
  });

  afterEach(async () => {
    await rm(repoRoot, { recursive: true, force: true });
  });

  it("detects reports generated from the current template", () => {
    expect(isCurrentVisualReportHtml(`<!doctype html><meta ${VISUAL_REPORT_TEMPLATE_MARKER}>`)).toBe(true);
    expect(isCurrentVisualReportHtml("<!doctype html><h1>old report</h1>")).toBe(false);
  });

  it("treats v1 CDN reports as stale even when they have a template marker", () => {
    const oldCdnHtml = [
      "<!doctype html>",
      '<meta name="synthetic-esg-report-template" content="explainable-ko-v1">',
      '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
    ].join("");

    expect(isCurrentVisualReportHtml(oldCdnHtml)).toBe(false);
  });

  it("refreshes stale report HTML before returning it", async () => {
    const run = makeRun("stale-run");
    await writeWebRun(repoRoot, run);
    const reportPath = path.join(getRunDir(repoRoot, run.runId), run.visualReportPath);
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(reportPath, "<!doctype html><h1>old report</h1>", "utf-8");

    const html = await readCurrentVisualReportHtml(repoRoot, run, async () => {
      await writeFile(reportPath, `<!doctype html><meta ${VISUAL_REPORT_TEMPLATE_MARKER}><h1>fresh report</h1>`, "utf-8");
    });

    expect(html).toContain("fresh report");
    await expect(readFile(reportPath, "utf-8")).resolves.toContain(VISUAL_REPORT_TEMPLATE_MARKER);
  });

  it("regenerates v1 CDN report HTML into the current local-bundle template", async () => {
    const run = makeRun("old-cdn-run");
    await writeWebRun(repoRoot, run);
    const reportPath = path.join(getRunDir(repoRoot, run.runId), run.visualReportPath);
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(
      reportPath,
      [
        "<!doctype html>",
        '<meta name="synthetic-esg-report-template" content="explainable-ko-v1">',
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
        "<h1>old report</h1>",
      ].join(""),
      "utf-8",
    );

    const html = await readCurrentVisualReportHtml(repoRoot, run, async () => {
      await writeFile(
        reportPath,
        `<!doctype html><meta ${VISUAL_REPORT_TEMPLATE_MARKER}><script src="plotly.min.js"></script><h1>fresh report</h1>`,
        "utf-8",
      );
    });

    expect(html).toContain('src="plotly.min.js"');
    expect(html).not.toContain("https://cdn.plot.ly");
  });

  it("treats v2 report-drawer HTML as stale", () => {
    const oldDrawerHtml = [
      "<!doctype html>",
      '<meta name="synthetic-esg-report-template" content="explainable-ko-v2-local-plotly">',
      '<script src="plotly.min.js"></script>',
      '<aside class="developer-drawer" id="developer-drawer">',
      '<button class="developer-toggle">개발자 정보</button>',
      "</aside>",
    ].join("");

    expect(isCurrentVisualReportHtml(oldDrawerHtml)).toBe(false);
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
