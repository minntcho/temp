import { ArrowLeft, BarChart3, FileText, FolderTree } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { RunStatusPill } from "@/app/components/RunStatusPill";
import { getRepoRootFromWebCwd, readRunBundle, type RunBundle } from "@/lib/run-registry";

export const dynamic = "force-dynamic";

type RunPageProps = {
  params: Promise<{ runId: string }>;
};

export default async function RunPage({ params }: RunPageProps) {
  const { runId } = await params;
  const repoRoot = getRepoRootFromWebCwd();
  let bundle: RunBundle;
  try {
    bundle = await readRunBundle(repoRoot, runId);
  } catch {
    notFound();
  }

  const reportReady = bundle.files.some((file) => file.path === bundle.run.visualReportPath);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Run Detail</p>
          <h1>{bundle.run.runId}</h1>
          <p className="subtitle">
            seed {bundle.run.seed} · {bundle.run.profileName} · {formatDate(bundle.run.startedAt)}
          </p>
        </div>
        <div className="top-actions">
          <Link className="icon-link" href="/">
            <ArrowLeft aria-hidden="true" size={18} />
            Runs
          </Link>
        </div>
      </header>

      <section className="overview-grid" aria-label="Run detail summary">
        <div className="metric">
          <FileText aria-hidden="true" size={22} />
          <strong>{bundle.files.length}</strong>
          <span>Files</span>
        </div>
        <div className="metric">
          <BarChart3 aria-hidden="true" size={22} />
          <strong>{reportReady ? "ready" : "missing"}</strong>
          <span>Plotly report</span>
        </div>
        <div className="metric">
          <FolderTree aria-hidden="true" size={22} />
          <strong>{recordCountTotal(bundle)}</strong>
          <span>Rows recorded</span>
        </div>
        <div className="metric">
          <RunStatusPill status={bundle.run.status} />
          <strong>{formatDuration(bundle.run.durationMs ?? 0)}</strong>
          <span>Duration</span>
        </div>
      </section>

      <section className="detail-grid">
        <div className="split-stack">
          <section className="panel" aria-labelledby="report-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Distribution</p>
                <h2 id="report-title">Plotly report</h2>
              </div>
            </div>
            {reportReady ? (
              <iframe className="report-frame" src={`/api/runs/${bundle.run.runId}/report`} title="Plotly distribution report" />
            ) : (
              <div className="empty-state">Report not available.</div>
            )}
          </section>

          <section className="panel" aria-labelledby="manifest-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Manifest</p>
                <h2 id="manifest-title">Generation contract</h2>
              </div>
            </div>
            <pre className="json-panel">{JSON.stringify(bundle.manifest ?? {}, null, 2)}</pre>
          </section>
        </div>

        <aside className="split-stack">
          <section className="panel" aria-labelledby="files-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Artifact</p>
                <h2 id="files-title">Run files</h2>
              </div>
            </div>
            <div className="file-table">
              {bundle.files.map((file) => (
                <div className="file-row" key={file.path}>
                  <code>{file.path}</code>
                  <span className="file-size">{formatBytes(file.size)}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel" aria-labelledby="web-run-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Web Run</p>
                <h2 id="web-run-title">Execution metadata</h2>
              </div>
            </div>
            <pre className="json-panel">{JSON.stringify(bundle.run, null, 2)}</pre>
          </section>
        </aside>
      </section>
    </main>
  );
}

function recordCountTotal(bundle: RunBundle): number {
  const counts = bundle.generationReport?.record_counts;
  if (!counts || typeof counts !== "object" || Array.isArray(counts)) {
    return 0;
  }
  let total = 0;
  for (const value of Object.values(counts)) {
    if (typeof value === "number") {
      total += value;
    }
  }
  return total;
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(durationMs: number): string {
  if (!durationMs) {
    return "-";
  }
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  return `${(durationMs / 1000).toFixed(1)}s`;
}
