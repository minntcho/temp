import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";
import { getRunDir, writeWebRun, type WebRun } from "@/lib/run-registry";
import { VISUAL_REPORT_TEMPLATE_MARKER } from "@/lib/visual-report";

describe("run report route", () => {
  let repoRoot: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    repoRoot = await mkdtemp(path.join(os.tmpdir(), "synthetic-esg-report-route-"));
    cwdSpy = vi.spyOn(process, "cwd").mockReturnValue(path.join(repoRoot, "web"));
  });

  afterEach(async () => {
    cwdSpy.mockRestore();
    await rm(repoRoot, { recursive: true, force: true });
  });

  it("serves an existing Plotly report", async () => {
    const run = makeRun("ready-run", "succeeded");
    await writeWebRun(repoRoot, run);
    const reportPath = path.join(getRunDir(repoRoot, run.runId), "reports", "distribution_dashboard.html");
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(
      reportPath,
      `<!doctype html><html><head><meta ${VISUAL_REPORT_TEMPLATE_MARKER}></head><body>report ready</body></html>`,
      "utf-8",
    );

    const response = await GET(new Request("http://localhost/api/runs/ready-run/report"), {
      params: Promise.resolve({ runId: run.runId }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/html");
    await expect(response.text()).resolves.toContain("report ready");
  });

  it("shows a report-unavailable page for a known run without a report file", async () => {
    const run = makeRun("failed-run", "failed", "spawn python ENOENT");
    await writeWebRun(repoRoot, run);

    const response = await GET(new Request("http://localhost/api/runs/failed-run/report"), {
      params: Promise.resolve({ runId: run.runId }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/html");
    const html = await response.text();
    expect(html).toContain("리포트를 열 수 없습니다");
  });
});

function makeRun(runId: string, status: WebRun["status"], error?: string): WebRun {
  return {
    runId,
    status,
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
    error,
  };
}
