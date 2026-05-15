"use client";

import { Play, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState, useTransition } from "react";

export function CreateRunPanel() {
  const router = useRouter();
  const [seed, setSeed] = useState("42");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function submitRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const parsedSeed = Number(seed);
    if (!Number.isInteger(parsedSeed)) {
      setError("Seed must be an integer.");
      return;
    }

    startTransition(async () => {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ seed: parsedSeed }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload.error ?? payload.run?.error ?? "Run failed.");
        return;
      }
      router.push(`/runs/${payload.run.runId}`);
      router.refresh();
    });
  }

  return (
    <section className="panel create-panel" aria-labelledby="create-run-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">New Run</p>
          <h2 id="create-run-title">Smoke generator</h2>
        </div>
        <span className="profile-chip">lges_smoke.yaml</span>
      </div>

      <form className="run-form" onSubmit={submitRun}>
        <label className="field">
          <span>Seed</span>
          <input
            inputMode="numeric"
            name="seed"
            onChange={(event) => setSeed(event.target.value)}
            value={seed}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending} type="submit">
            {isPending ? <RotateCcw aria-hidden="true" size={18} /> : <Play aria-hidden="true" size={18} />}
            {isPending ? "Running" : "Run smoke"}
          </button>
        </div>
      </form>

      {error ? <p className="form-error">{error}</p> : null}
    </section>
  );
}
