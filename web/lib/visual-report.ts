import { readFile } from "node:fs/promises";

import { refreshVisualReport } from "@/lib/python-runner";
import { getRunDir, getRunFilePath, type WebRun } from "@/lib/run-registry";

export const VISUAL_REPORT_TEMPLATE_VERSION = "explainable-ko-v3-no-report-drawer";
export const VISUAL_REPORT_TEMPLATE_MARKER = `name="synthetic-esg-report-template" content="${VISUAL_REPORT_TEMPLATE_VERSION}"`;

export type VisualReportRefresher = (repoRoot: string, run: WebRun) => Promise<void>;

export function isCurrentVisualReportHtml(html: string): boolean {
  return html.includes(VISUAL_REPORT_TEMPLATE_MARKER);
}

export async function readCurrentVisualReportHtml(
  repoRoot: string,
  run: WebRun,
  refresh: VisualReportRefresher = refreshVisualReport,
): Promise<string> {
  const runDir = getRunDir(repoRoot, run.runId);
  const reportPath = getRunFilePath(runDir, run.visualReportPath);

  try {
    const html = await readFile(reportPath, "utf-8");
    if (isCurrentVisualReportHtml(html)) {
      return html;
    }
  } catch {
    // Missing reports are regenerated below when the run artifacts are available.
  }

  await refresh(repoRoot, run);
  const refreshedHtml = await readFile(reportPath, "utf-8");
  if (!isCurrentVisualReportHtml(refreshedHtml)) {
    throw new Error("visual report was regenerated without the current template marker");
  }
  return refreshedHtml;
}
