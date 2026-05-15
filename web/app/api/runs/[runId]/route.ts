import { readRunBundle } from "@/lib/run-registry";
import { getRepoRootFromWebCwd } from "@/lib/run-registry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, context: RouteContext): Promise<Response> {
  const { runId } = await context.params;
  const repoRoot = getRepoRootFromWebCwd();

  try {
    const bundle = await readRunBundle(repoRoot, runId);
    return Response.json(bundle);
  } catch {
    return Response.json({ error: "run not found" }, { status: 404 });
  }
}
