/** Small shared primitives, so every tab renders a metric or a field the same way. */

export function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="metric">
      <div className="metric-value tabular-nums">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

export function ScorePill({ score }: { score: number }) {
  const cls = score >= 8 ? "score-high" : score >= 6 ? "score-mid" : "score-low";
  return <span className={`score-pill ${cls}`}>{score.toFixed(1)}</span>;
}

/** 🟢 ≥8, 🟡 ≥6, 🔴 below — the score_color() traffic light. */
export function scoreDot(score: number): string {
  if (score >= 8) return "🟢";
  if (score >= 6) return "🟡";
  return "🔴";
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h3 className="mb-3 text-sm font-semibold text-text">{title}</h3>
      {children}
    </section>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="mb-4 block">
      <span className="mb-1.5 block text-xs font-medium text-dim">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] text-faint">{hint}</span> : null}
    </label>
  );
}

export function Note({
  children,
  tone = "info",
}: {
  children: React.ReactNode;
  tone?: "info" | "warn" | "good";
}) {
  const border =
    tone === "warn"
      ? "border-amber/40"
      : tone === "good"
        ? "border-[#10b981]/40"
        : "border-line-strong";
  return (
    <div className={`rounded-lg border ${border} bg-surface px-4 py-3 text-sm text-dim`}>
      {children}
    </div>
  );
}

export function Pill({ children }: { children: React.ReactNode }) {
  return <span className="pill">{children}</span>;
}
