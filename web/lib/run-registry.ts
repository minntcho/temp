import { randomBytes } from "node:crypto";
import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

export const WEB_RUNS_RELATIVE_DIR = "out/web-runs";
export const DEFAULT_RUN_ID_TIME_ZONE = "Asia/Seoul";

export type WebRunStatus = "running" | "succeeded" | "failed";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export type WebRun = {
  runId: string;
  status: WebRunStatus;
  profile: string;
  profileName: string;
  seed: number;
  command: string;
  visualizeCommand: string;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  runDir: string;
  manifestPath: string;
  generationReportPath: string;
  visualReportPath: string;
  stdout: string;
  stderr: string;
  error?: string;
};

export type RunFile = {
  path: string;
  size: number;
};

export type RunBundle = {
  run: WebRun;
  manifest: JsonObject | null;
  generationReport: JsonObject | null;
  files: RunFile[];
};

export function getRepoRootFromWebCwd(cwd = process.cwd()): string {
  return path.resolve(cwd, "..");
}

export function buildRunId({
  now,
  seed,
  timeZone = process.env.SYNTHETIC_ESG_RUN_TIME_ZONE ?? DEFAULT_RUN_ID_TIME_ZONE,
  uniqueSuffix = randomBytes(3).toString("hex"),
}: {
  now: Date;
  seed: number;
  timeZone?: string;
  uniqueSuffix?: string;
}): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "2-digit",
    second: "2-digit",
    timeZone,
    year: "numeric",
  }).formatToParts(now);
  const byType = new Map(parts.map((part) => [part.type, part.value]));
  const timestamp = `${byType.get("year")}${byType.get("month")}${byType.get("day")}-${byType.get("hour")}${byType.get("minute")}${byType.get("second")}`;
  const millisecond = String(now.getMilliseconds()).padStart(3, "0");
  if (!/^[A-Za-z0-9]+$/.test(uniqueSuffix)) {
    throw new Error("Run id suffix must be alphanumeric");
  }
  return `${timestamp}-${millisecond}-seed${seed}-${uniqueSuffix}`;
}

export function isValidRunId(runId: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(runId);
}

export function getWebRunsDir(repoRoot: string): string {
  return path.join(repoRoot, WEB_RUNS_RELATIVE_DIR);
}

export function getRunDir(repoRoot: string, runId: string): string {
  if (!isValidRunId(runId)) {
    throw new Error(`Invalid run id: ${runId}`);
  }
  const runsDir = getWebRunsDir(repoRoot);
  const runDir = path.resolve(runsDir, runId);
  const relative = path.relative(runsDir, runDir);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Invalid run id: ${runId}`);
  }
  return runDir;
}

export function getRunFilePath(runDir: string, relativePath: string): string {
  if (path.isAbsolute(relativePath)) {
    throw new Error(`Invalid run file path: ${relativePath}`);
  }
  const resolvedPath = path.resolve(runDir, relativePath);
  const relative = path.relative(runDir, resolvedPath);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Invalid run file path: ${relativePath}`);
  }
  return resolvedPath;
}

export async function hasRunFile(repoRoot: string, run: WebRun, relativePath: string): Promise<boolean> {
  try {
    const runDir = getRunDir(repoRoot, run.runId);
    const filePath = getRunFilePath(runDir, relativePath);
    const info = await stat(filePath);
    return info.isFile();
  } catch {
    return false;
  }
}

export async function writeWebRun(repoRoot: string, run: WebRun): Promise<void> {
  const runDir = getRunDir(repoRoot, run.runId);
  await mkdir(runDir, { recursive: true });
  await writeFile(path.join(runDir, "web_run.json"), `${JSON.stringify(run, null, 2)}\n`, "utf-8");
}

export async function readWebRun(repoRoot: string, runId: string): Promise<WebRun> {
  const runDir = getRunDir(repoRoot, runId);
  const payload = await readJsonFile(path.join(runDir, "web_run.json"));
  return payload as WebRun;
}

export async function listRuns(repoRoot: string): Promise<WebRun[]> {
  const runsDir = getWebRunsDir(repoRoot);
  let entries: string[];
  try {
    entries = await readdir(runsDir);
  } catch {
    return [];
  }

  const runs: WebRun[] = [];
  for (const entry of entries) {
    if (!isValidRunId(entry)) {
      continue;
    }
    try {
      const run = await readWebRun(repoRoot, entry);
      runs.push(run);
    } catch {
      continue;
    }
  }

  return runs.sort((a, b) => Date.parse(b.startedAt) - Date.parse(a.startedAt));
}

export async function readRunBundle(repoRoot: string, runId: string): Promise<RunBundle> {
  const run = await readWebRun(repoRoot, runId);
  const runDir = getRunDir(repoRoot, runId);
  const [manifest, generationReport, files] = await Promise.all([
    readOptionalJsonFile(getRunFilePath(runDir, run.manifestPath)),
    readOptionalJsonFile(getRunFilePath(runDir, run.generationReportPath)),
    listRunFiles(runDir),
  ]);

  return {
    run,
    manifest,
    generationReport,
    files,
  };
}

export async function listRunFiles(runDir: string): Promise<RunFile[]> {
  const files: RunFile[] = [];

  async function visit(currentDir: string): Promise<void> {
    let entries;
    try {
      entries = await readdir(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await visit(absolutePath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      const info = await stat(absolutePath);
      files.push({
        path: toPosixPath(path.relative(runDir, absolutePath)),
        size: info.size,
      });
    }
  }

  await visit(runDir);
  return files.sort((a, b) => a.path.localeCompare(b.path));
}

async function readOptionalJsonFile(filePath: string): Promise<JsonObject | null> {
  try {
    return await readJsonFile(filePath);
  } catch {
    return null;
  }
}

async function readJsonFile(filePath: string): Promise<JsonObject> {
  return JSON.parse(await readFile(filePath, "utf-8")) as JsonObject;
}

function toPosixPath(value: string): string {
  return value.split(path.sep).join("/");
}
