import { createSmokeRun } from "@/lib/python-runner";
import { getRepoRootFromWebCwd, listRuns } from "@/lib/run-registry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const repoRoot = getRepoRootFromWebCwd();
  const runs = await listRuns(repoRoot);
  return Response.json({ runs });
}

export async function POST(request: Request): Promise<Response> {
  const repoRoot = getRepoRootFromWebCwd();
  let body: unknown = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  try {
    const run = await createSmokeRun(repoRoot, body && typeof body === "object" ? body : {});
    return Response.json({ run }, { status: run.status === "succeeded" ? 201 : 500 });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 },
    );
  }
}
