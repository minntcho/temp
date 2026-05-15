import { getRepoRootFromWebCwd, readWebRun, type WebRun } from "@/lib/run-registry";
import { readCurrentVisualReportHtml } from "@/lib/visual-report";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, context: RouteContext): Promise<Response> {
  const { runId } = await context.params;
  const repoRoot = getRepoRootFromWebCwd();

  let run: WebRun | null = null;
  try {
    run = await readWebRun(repoRoot, runId);
    const html = await readCurrentVisualReportHtml(repoRoot, run);
    return new Response(html, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "x-content-type-options": "nosniff",
      },
    });
  } catch (error) {
    if (!run) {
      return Response.json({ error: "run not found" }, { status: 404 });
    }
    return new Response(renderMissingReportPage(run, error), {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "x-content-type-options": "nosniff",
      },
    });
  }
}

function renderMissingReportPage(run: WebRun, error?: unknown): string {
  const message = error instanceof Error ? error.message : run.error;
  const detail = message ? `<p class="error">${escapeHtml(message)}</p>` : "";
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>리포트를 열 수 없습니다</title>
  <style>
    body {
      align-items: center;
      background: #f5f7f4;
      color: #202421;
      display: grid;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      min-height: 100vh;
      padding: 24px;
    }
    main {
      background: #ffffff;
      border: 1px solid #d7dfd8;
      border-radius: 8px;
      box-shadow: 0 16px 40px rgba(32, 36, 33, 0.08);
      margin: 0 auto;
      max-width: 620px;
      padding: 22px;
      width: 100%;
    }
    h1 { font-size: 1.5rem; margin: 0 0 8px; }
    p { color: #657064; line-height: 1.55; margin: 0; }
    .error {
      background: #fee4e2;
      border: 1px solid #f5b8b1;
      border-radius: 8px;
      color: #912018;
      margin-top: 14px;
      padding: 12px;
      word-break: break-word;
    }
  </style>
</head>
<body>
  <main>
    <h1>리포트를 열 수 없습니다</h1>
    <p>이 run은 등록되어 있지만 현재 Plotly HTML 리포트를 생성하거나 갱신하지 못했습니다. 실행 상태와 Python 경로 설정을 확인해 주세요.</p>
    ${detail}
  </main>
</body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#x27;");
}
