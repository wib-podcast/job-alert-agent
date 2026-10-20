"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState, useTransition } from "react";

import { JOB_STATUSES } from "@/lib/jobs-shared";

export interface FilterFacet {
  value: string;
  label: string;
  total: number;
}

/**
 * Filters live in the query string rather than client state, so a filtered
 * board is a shareable URL and survives a reload — the one thing the Streamlit
 * version couldn't do.
 */
export function JobFilters({
  geoFacets,
  sourceFacets,
}: {
  geoFacets: FilterFacet[];
  sourceFacets: FilterFacet[];
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  const [search, setSearch] = useState(params.get("q") ?? "");

  const push = useCallback(
    (next: URLSearchParams) => {
      const qs = next.toString();
      start(() => router.replace(qs ? `/?${qs}` : "/", { scroll: false }));
    },
    [router],
  );

  const set = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(params);
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
      push(next);
    },
    [params, push],
  );

  const toggleIn = useCallback(
    (key: string, value: string) => {
      const current = new Set((params.get(key) ?? "").split(",").filter(Boolean));
      if (current.has(value)) current.delete(value);
      else current.add(value);
      set(key, [...current].join(","));
    },
    [params, set],
  );

  const activeIn = (key: string) => new Set((params.get(key) ?? "").split(",").filter(Boolean));

  const activeGeos = activeIn("geo");
  const activeSources = activeIn("source");
  const activeStatuses = activeIn("status");
  const minScore = params.get("min") ?? "0";

  return (
    <div className={`mb-5 rounded-xl border border-line bg-surface p-4 ${pending ? "opacity-70" : ""}`}>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-dim">🔍 Search title / company</span>
          <input
            className="field w-full px-3 py-2 text-sm"
            value={search}
            placeholder="e.g. TikTok, Fintech, AI…"
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") set("q", search);
            }}
            onBlur={() => set("q", search)}
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-dim">
            🏆 Minimum score: <span className="text-amber tabular-nums">{Number(minScore).toFixed(1)}</span>
          </span>
          <input
            type="range"
            min={0}
            max={10}
            step={0.5}
            value={minScore}
            className="w-full accent-[#d97706]"
            onChange={(e) => set("min", e.target.value === "0" ? null : e.target.value)}
          />
        </label>
      </div>

      <FilterChips
        label="🌍 Geography"
        options={geoFacets}
        active={activeGeos}
        onToggle={(v) => toggleIn("geo", v)}
      />
      <FilterChips
        label="📡 Source"
        options={sourceFacets}
        active={activeSources}
        onToggle={(v) => toggleIn("source", v)}
      />
      <FilterChips
        label="📌 Status"
        options={JOB_STATUSES.map((s) => ({ value: s, label: s, total: -1 }))}
        active={activeStatuses}
        onToggle={(v) => toggleIn("status", v)}
        hint="Dismissed jobs are hidden until you select them."
      />
    </div>
  );
}

function FilterChips({
  label,
  options,
  active,
  onToggle,
  hint,
}: {
  label: string;
  options: FilterFacet[];
  active: Set<string>;
  onToggle: (value: string) => void;
  hint?: string;
}) {
  if (options.length === 0) return null;

  return (
    <div className="mt-4">
      <span className="mb-2 block text-xs font-medium text-dim">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = active.has(o.value);
          return (
            <button
              key={o.value}
              type="button"
              onClick={() => onToggle(o.value)}
              aria-pressed={on}
              className={`rounded-full border px-3 py-1 text-xs capitalize transition-colors ${
                on
                  ? "border-amber text-amber"
                  : "border-line text-dim hover:border-amber/40 hover:text-text"
              }`}
            >
              {o.label}
              {o.total >= 0 ? <span className="ml-1.5 tabular-nums opacity-60">{o.total}</span> : null}
            </button>
          );
        })}
      </div>
      {hint ? <p className="mt-1.5 text-[11px] text-faint">{hint}</p> : null}
    </div>
  );
}
