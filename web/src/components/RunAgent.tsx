"use client";

import { useState, useTransition } from "react";

import { triggerRun } from "@/app/actions";

export function RunAgentButton({ repo }: { repo: string }) {
  const [pending, start] = useTransition();
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  return (
    <div>
      <button
        type="button"
        disabled={pending}
        className="btn-primary w-full px-5 py-3 text-sm sm:w-auto"
        onClick={() =>
          start(async () => {
            setResult(await triggerRun());
          })
        }
      >
        {pending ? "⚡ Queueing…" : "▶️ Run Now"}
      </button>

      {result ? (
        <div
          className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
            result.ok ? "border-[#10b981]/40 text-[#6ee7b7]" : "border-amber/40 text-amber"
          }`}
        >
          {result.ok ? "✅ " : "⚠️ "}
          {result.message}
          {result.ok ? (
            <a
              href={`https://github.com/${repo}/actions/workflows/job_alert.yml`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1.5 block underline underline-offset-4"
            >
              Watch the run on GitHub →
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
