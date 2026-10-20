"use client";

import { useState, useTransition } from "react";

import { savePreferences } from "@/app/actions";
import type { Settings } from "@/lib/settings-shared";

export function AlertsForm({ initial }: { initial: Settings }) {
  const [s, setS] = useState(initial);
  const [pending, start] = useTransition();
  const [saved, setSaved] = useState(false);

  function field<K extends keyof Settings>(key: K, value: string) {
    setS((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  return (
    <form
      action={(fd) =>
        start(async () => {
          await savePreferences(fd);
          setSaved(true);
        })
      }
    >
      {/* The toggles aren't on this form, so carry them through unchanged —
          savePreferences writes every source toggle explicitly. */}
      {(["ENABLE_IIMJOBS", "ENABLE_MYCAREERSFUTURE", "ENABLE_LINKEDIN", "ENABLE_GOOGLE_JOBS"] as const).map(
        (k) => (
          <input key={k} type="hidden" name={k} value={s[k]} />
        ),
      )}

      <label className="mb-5 block">
        <span className="mb-1.5 block text-xs font-medium text-dim">
          Minimum score to include in the email:{" "}
          <span className="text-amber tabular-nums">
            {Number(s.RELEVANCE_SCORE_THRESHOLD).toFixed(1)}
          </span>
        </span>
        <input
          type="range"
          name="RELEVANCE_SCORE_THRESHOLD"
          min={0}
          max={10}
          step={0.5}
          value={s.RELEVANCE_SCORE_THRESHOLD}
          className="w-full accent-[#d97706]"
          onChange={(e) => field("RELEVANCE_SCORE_THRESHOLD", e.target.value)}
        />
      </label>

      <label className="mb-5 block">
        <span className="mb-1.5 block text-xs font-medium text-dim">
          Max jobs per email:{" "}
          <span className="text-amber tabular-nums">{s.MAX_JOBS_IN_EMAIL}</span>
        </span>
        <input
          type="range"
          name="MAX_JOBS_IN_EMAIL"
          min={3}
          max={20}
          value={s.MAX_JOBS_IN_EMAIL}
          className="w-full accent-[#d97706]"
          onChange={(e) => field("MAX_JOBS_IN_EMAIL", e.target.value)}
        />
      </label>

      <button type="submit" disabled={pending} className="btn-primary px-5 py-2.5 text-sm">
        {pending ? "Saving…" : "💾 Save Alert Settings"}
      </button>

      {saved ? <p className="mt-3 text-sm text-[#6ee7b7]">✅ Saved.</p> : null}
    </form>
  );
}
