import { CheckCircle2, Clock3, XCircle } from "lucide-react";

import type { WebRunStatus } from "@/lib/run-registry";

export function RunStatusPill({ status }: { status: WebRunStatus }) {
  const icon =
    status === "succeeded" ? (
      <CheckCircle2 aria-hidden="true" size={16} />
    ) : status === "failed" ? (
      <XCircle aria-hidden="true" size={16} />
    ) : (
      <Clock3 aria-hidden="true" size={16} />
    );

  return (
    <span className={`status-pill status-${status}`}>
      {icon}
      {status}
    </span>
  );
}
