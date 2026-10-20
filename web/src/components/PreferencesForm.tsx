"use client";

import { useState, useTransition } from "react";

import { savePreferences } from "@/app/actions";
import { GEOS } from "@/lib/geo";
import { csvToList, estimateQueries, listToCsv, type Settings } from "@/lib/settings-shared";

const MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"];
const DAY_OPTIONS = [1, 3, 7, 14, 30];

const SOURCE_TOGGLES = [
  { key: "ENABLE_MYCAREERSFUTURE", label: "MyCareersFuture (Singapore)", hint: "Open government API — no key needed." },
  { key: "ENABLE_IIMJOBS", label: "IIMJobs (India)", hint: "No auth needed." },
  { key: "ENABLE_LINKEDIN", label: "LinkedIn Jobs", hint: "Needs session cookies — see LinkedIn Setup." },
  { key: "ENABLE_GOOGLE_JOBS", label: "Google Jobs", hint: "Retired: CAPTCHA'd from CI, no geo control." },
] as const;

export function PreferencesForm({ initial }: { initial: Settings }) {
  const [s, setS] = useState<Settings>(initial);
  const [pending, start] = useTransition();
  const [saved, setSaved] = useState(false);

  function field<K extends keyof Settings>(key: K, value: string) {
    setS((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  const queries = estimateQueries(s);
  const perRun = queries * 0.001;

  function onSubmit(formData: FormData) {
    start(async () => {
      await savePreferences(formData);
      setSaved(true);
    });
  }

  return (
    <form action={onSubmit}>
      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div>
          <label className="mb-5 block">
            <span className="mb-1.5 block text-xs font-medium text-dim">🎯 Target Roles</span>
            <textarea
              name="TARGET_ROLES_TEXT"
              className="field h-44 w-full resize-y px-3 py-2 text-sm"
              value={csvToList(s.TARGET_ROLES).join("\n")}
              onChange={(e) => field("TARGET_ROLES", listToCsv(e.target.value.split("\n")))}
            />
            <input type="hidden" name="TARGET_ROLES" value={s.TARGET_ROLES} />
            <span className="mt-1 block text-[11px] text-faint">
              One role per line. Sent as a search query to each source.
            </span>
          </label>

          <label className="mb-5 block">
            <span className="mb-1.5 block text-xs font-medium text-dim">📍 Target Locations</span>
            <textarea
              name="TARGET_LOCATIONS_TEXT"
              className="field h-32 w-full resize-y px-3 py-2 text-sm"
              value={csvToList(s.TARGET_LOCATIONS).join("\n")}
              onChange={(e) => field("TARGET_LOCATIONS", listToCsv(e.target.value.split("\n")))}
            />
            <input type="hidden" name="TARGET_LOCATIONS" value={s.TARGET_LOCATIONS} />
            <span className="mt-1 block text-[11px] text-faint">
              One per line. Ignored by sources that are single-country by definition.
            </span>
          </label>

          <div className="mb-5">
            <span className="mb-2 block text-xs font-medium text-dim">🌍 Target Geographies</span>
            <div className="flex flex-wrap gap-2">
              {GEOS.filter((g) => g.priority <= 7).map((g) => {
                const on = csvToList(s.TARGET_GEOS).includes(g.code);
                return (
                  <button
                    key={g.code}
                    type="button"
                    onClick={() => {
                      const cur = new Set(csvToList(s.TARGET_GEOS));
                      if (cur.has(g.code)) cur.delete(g.code);
                      else cur.add(g.code);
                      field("TARGET_GEOS", listToCsv([...cur]));
                    }}
                    aria-pressed={on}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      on ? "border-amber text-amber" : "border-line text-dim hover:text-text"
                    }`}
                  >
                    {g.flag} {g.label}
                  </button>
                );
              })}
            </div>
            <input type="hidden" name="TARGET_GEOS" value={s.TARGET_GEOS} />
            <span className="mt-1.5 block text-[11px] text-faint">
              Priority order, highest first. Ties at the same score break this way.
            </span>
          </div>

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-dim">
              🏆 Relevance threshold — email above{" "}
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
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">📡 Sources</h3>
          <div className="mb-6 flex flex-col gap-2.5">
            {SOURCE_TOGGLES.map((t) => (
              <label key={t.key} className="flex cursor-pointer items-start gap-2.5">
                <input
                  type="checkbox"
                  checked={s[t.key] === "true"}
                  onChange={(e) => field(t.key, e.target.checked ? "true" : "false")}
                  className="mt-0.5 accent-[#d97706]"
                />
                <span>
                  <span className="block text-sm text-text">{t.label}</span>
                  <span className="block text-[11px] text-faint">{t.hint}</span>
                </span>
                <input type="hidden" name={t.key} value={s[t.key]} />
              </label>
            ))}
          </div>

          <h3 className="mb-3 text-sm font-semibold">🔧 Scraper Settings</h3>
          <label className="mb-4 block">
            <span className="mb-1.5 block text-xs text-dim">
              Max jobs per query:{" "}
              <span className="text-amber tabular-nums">{s.MAX_JOBS_PER_QUERY}</span>
            </span>
            <input
              type="range"
              name="MAX_JOBS_PER_QUERY"
              min={5}
              max={50}
              step={5}
              value={s.MAX_JOBS_PER_QUERY}
              className="w-full accent-[#d97706]"
              onChange={(e) => field("MAX_JOBS_PER_QUERY", e.target.value)}
            />
          </label>

          <label className="mb-6 block">
            <span className="mb-1.5 block text-xs text-dim">Jobs posted within</span>
            <select
              name="DAYS_SINCE_POSTED"
              className="field w-full px-3 py-2 text-sm"
              value={s.DAYS_SINCE_POSTED}
              onChange={(e) => field("DAYS_SINCE_POSTED", e.target.value)}
            >
              {DAY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  Last {d} days
                </option>
              ))}
            </select>
          </label>

          <h3 className="mb-3 text-sm font-semibold">🤖 LLM Model</h3>
          <label className="block">
            <span className="mb-1.5 block text-xs text-dim">Scoring model</span>
            <select
              name="LLM_MODEL"
              className="field w-full px-3 py-2 text-sm"
              value={s.LLM_MODEL}
              onChange={(e) => field("LLM_MODEL", e.target.value)}
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-[11px] text-faint">
              Haiku is roughly 5× cheaper and ranks about as well. Scoring is batched either way.
            </span>
          </label>
        </div>
      </div>

      <hr className="my-6 border-line" />

      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <button type="submit" disabled={pending} className="btn-primary px-5 py-2.5 text-sm">
          {pending ? "Saving…" : "💾 Save Preferences"}
        </button>
        <p className="text-xs text-dim">
          {csvToList(s.TARGET_ROLES).length} roles × {csvToList(s.TARGET_LOCATIONS).length} locations ·{" "}
          <span className="text-amber tabular-nums">{queries}</span> queries per run · Haiku est. ~$
          {perRun.toFixed(2)}/run, ~${(perRun * 60).toFixed(1)}/month at 2×/day
        </p>
      </div>

      {saved ? (
        <p className="mt-3 text-sm text-[#6ee7b7]">
          ✅ Saved. Takes effect on the next run — including the scheduled one.
        </p>
      ) : null}
    </form>
  );
}
