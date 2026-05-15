import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

import {
  WEB_RUNS_RELATIVE_DIR,
  buildRunId,
  getRunDir,
  type WebRun,
  writeWebRun,
} from "@/lib/run-registry";

export type CreateRunRequest = {
  seed?: unknown;
};

export type NormalizedRunRequest = {
  profile: "profiles/lges_smoke.yaml";
  profileName: "lges_smoke";
  seed: number;
};

export type CommandSpec = {
  command: string;
  args: string[];
  cwd: string;
};

export type SmokeRunPlan = {
  run: WebRun;
  generate: CommandSpec;
  visualize: CommandSpec;
};

const SMOKE_PROFILE = "profiles/lges_smoke.yaml";
const SMOKE_PROFILE_NAME = "lges_smoke";
const VISUAL_REPORT_PATH = "reports/distribution_dashboard.html";

export function normalizeRunRequest(input: CreateRunRequest): NormalizedRunRequest {
  const rawSeed = input.seed ?? 42;
  const seed = typeof rawSeed === "string" && rawSeed.trim() !== "" ? Number(rawSeed) : rawSeed;
  if (!Number.isInteger(seed)) {
    throw new Error("seed must be an integer");
  }

  return {
    profile: SMOKE_PROFILE,
    profileName: SMOKE_PROFILE_NAME,
    seed: seed as number,
  };
}

export function buildSmokeRunPlan({
  repoRoot,
  now,
  pythonCommand,
  seed,
  uniqueSuffix,
}: {
  repoRoot: string;
  now: Date;
  pythonCommand?: string;
  seed: number;
  uniqueSuffix?: string;
}): SmokeRunPlan {
  const runId = buildRunId({ now, seed, uniqueSuffix });
  const runDir = `${WEB_RUNS_RELATIVE_DIR}/${runId}`;
  const python = resolvePythonCommand(pythonCommand);
  const generateArgs = [
    "-m",
    "synthetic_esg",
    "generate",
    "--profile",
    SMOKE_PROFILE,
    "--out-dir",
    runDir,
    "--seed",
    String(seed),
  ];
  const visualizeArgs = [
    "-m",
    "synthetic_esg",
    "visualize",
    "--run-dir",
    runDir,
    "--out-dir",
    `${runDir}/reports`,
    "--plotly-js",
    "cdn",
  ];

  return {
    run: {
      runId,
      status: "running",
      profile: SMOKE_PROFILE,
      profileName: SMOKE_PROFILE_NAME,
      seed,
      command: commandToString(python, generateArgs),
      visualizeCommand: commandToString(python, visualizeArgs),
      startedAt: now.toISOString(),
      runDir,
      manifestPath: "manifest.json",
      generationReportPath: "generation_report.json",
      visualReportPath: VISUAL_REPORT_PATH,
      stdout: "",
      stderr: "",
    },
    generate: {
      command: python,
      args: generateArgs,
      cwd: repoRoot,
    },
    visualize: {
      command: python,
      args: visualizeArgs,
      cwd: repoRoot,
    },
  };
}

export async function createSmokeRun(repoRoot: string, input: CreateRunRequest): Promise<WebRun> {
  const request = normalizeRunRequest(input);
  const plan = buildSmokeRunPlan({ repoRoot, now: new Date(), seed: request.seed });
  const runDir = getRunDir(repoRoot, plan.run.runId);
  const startedAtMs = Date.now();

  await mkdir(runDir, { recursive: true });
  await writeWebRun(repoRoot, plan.run);

  let stdout = "";
  let stderr = "";
  try {
    const generateResult = await runCommand(plan.generate);
    stdout += generateResult.stdout;
    stderr += generateResult.stderr;

    const visualizeResult = await runCommand(plan.visualize);
    stdout += visualizeResult.stdout;
    stderr += visualizeResult.stderr;

    const finished: WebRun = {
      ...plan.run,
      status: "succeeded",
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - startedAtMs,
      stdout,
      stderr,
    };
    await writeWebRun(repoRoot, finished);
    return finished;
  } catch (error) {
    const failed: WebRun = {
      ...plan.run,
      status: "failed",
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - startedAtMs,
      stdout,
      stderr,
      error: error instanceof Error ? error.message : String(error),
    };
    await writeWebRun(repoRoot, failed);
    return failed;
  }
}

export async function refreshVisualReport(repoRoot: string, run: WebRun): Promise<void> {
  await runCommand({
    command: resolvePythonCommand(),
    args: [
      "-m",
      "synthetic_esg",
      "visualize",
      "--run-dir",
      run.runDir,
      "--out-dir",
      `${run.runDir}/reports`,
      "--plotly-js",
      "cdn",
    ],
    cwd: repoRoot,
  });
}

function runCommand(commandSpec: CommandSpec): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(commandSpec.command, commandSpec.args, {
      cwd: commandSpec.cwd,
      shell: false,
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf-8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      reject(new Error(`${commandSpec.command} exited with code ${code}: ${stderr || stdout}`));
    });
  });
}

function resolvePythonCommand(explicitCommand?: string): string {
  return explicitCommand ?? process.env.SYNTHETIC_ESG_PYTHON ?? process.env.PYTHON ?? "python";
}

function commandToString(command: string, args: string[]): string {
  return [command, ...args].join(" ");
}
