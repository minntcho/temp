import { BarChart3, Database, FolderClock, History } from "lucide-react";
import Link from "next/link";

import { CreateRunPanel } from "@/app/components/CreateRunPanel";
import { RunStatusPill } from "@/app/components/RunStatusPill";
import { getRepoRootFromWebCwd, hasRunFile, listRuns, type WebRun } from "@/lib/run-registry";

export const dynamic = "force-dynamic";

export default async function Home() {
  const repoRoot = getRepoRootFromWebCwd();
  const runs = await listRuns(repoRoot);
  const succeededRuns = runs.filter((run) => run.status === "succeeded").length;
  const latestReportRun = await findLatestReportRun(repoRoot, runs);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Synthetic ESG</p>
          <h1>Run dashboard</h1>
          <p className="subtitle">
            Smoke profile 실행 이력을 보관하고, 생성된 manifest와 Plotly distribution report를 run 단위로 다시 엽니다.
          </p>
        </div>
        <div className="top-actions">
          {latestReportRun ? (
            <Link className="icon-link" href={`/runs/${latestReportRun.runId}`}>
              <BarChart3 aria-hidden="true" size={18} />
              Latest report
            </Link>
          ) : null}
        </div>
      </header>

      <section className="overview-grid" aria-label="Run summary">
        <Metric icon={<History aria-hidden="true" size={22} />} label="Total runs" value={runs.length} />
        <Metric icon={<Database aria-hidden="true" size={22} />} label="Succeeded" value={succeededRuns} />
        <Metric icon={<FolderClock aria-hidden="true" size={22} />} label="Profile" value="smoke" />
        <Metric icon={<BarChart3 aria-hidden="true" size={22} />} label="Report" value={latestReportRun ? "ready" : "missing"} />
      </section>

      <section className="workspace-grid">
        <CreateRunPanel />
        <section className="panel" aria-labelledby="recent-runs-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">History</p>
              <h2 id="recent-runs-title">Reusable runs</h2>
            </div>
          </div>
          {runs.length > 0 ? (
            <div className="run-list">
              {runs.map((run) => (
                <RunRow key={run.runId} run={run} />
              ))}
            </div>
          ) : (
            <div className="empty-state">No runs yet.</div>
          )}
        </section>
      </section>
    </main>
  );
}

async function findLatestReportRun(repoRoot: string, runs: WebRun[]): Promise<WebRun | null> {
  for (const run of runs) {
    if (run.status !== "succeeded") {
      continue;
    }
    if (await hasRunFile(repoRoot, run, run.visualReportPath)) {
      return run;
    }
  }
  return null;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="metric">
      {icon}
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function RunRow({ run }: { run: WebRun }) {
  return (
    <Link className="run-row" href={`/runs/${run.runId}`}>
      <span className="run-main">
        <span className="run-id">{run.runId}</span>
        <span className="run-meta">
          <span>seed {run.seed}</span>
          <span>{formatDate(run.startedAt)}</span>
          {run.durationMs ? <span>{formatDuration(run.durationMs)}</span> : null}
        </span>
      </span>
      <RunStatusPill status={run.status} />
    </Link>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  return `${(durationMs / 1000).toFixed(1)}s`;
}
