import { readFile } from "node:fs/promises";
import { getRepoRootFromWebCwd, getRunDir, getRunFilePath, readWebRun } from "@/lib/run-registry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, context: RouteContext): Promise<Response> {
  const { runId } = await context.params;
  const repoRoot = getRepoRootFromWebCwd();

  try {
    const run = await readWebRun(repoRoot, runId);
    const reportPath = getRunFilePath(getRunDir(repoRoot, runId), run.visualReportPath);
    const html = await readFile(reportPath, "utf-8");
    return new Response(html, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "x-content-type-options": "nosniff",
      },
    });
  } catch {
    return Response.json({ error: "report not found" }, { status: 404 });
  }
}
