import { TabHeader } from "@/components/Character";
import { AlertsForm } from "@/components/AlertsForm";
import { Note } from "@/components/ui";
import { TAB_CHARACTERS } from "@/lib/characters";
import { secretStatuses } from "@/lib/env-status";
import { boardStats } from "@/lib/jobs";
import { loadSettings } from "@/lib/settings";

export const dynamic = "force-dynamic";

export default async function AlertsPage() {
  const [settings, stats] = await Promise.all([loadSettings(), boardStats()]);
  const secrets = secretStatuses().filter((s) => s.key !== "GITHUB_DISPATCH_TOKEN");

  return (
    <>
      <TabHeader title="Alerts & Email" character={TAB_CHARACTERS.alerts} />

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold">📐 Alert Rules</h3>
          <AlertsForm initial={settings} />

          <div className="mt-6 rounded-lg border border-line bg-surface p-4">
            <p className="text-xs text-dim">
              <span className="text-amber tabular-nums">{stats.goodFit}</span> jobs currently sit
              above 7.0, and{" "}
              <span className="text-amber tabular-nums">{stats.alerted}</span> have already been
              emailed. The digest only ever sends a job once — `alerted` is set after a successful
              send, so a crash mid-send re-sends rather than dropping it.
            </p>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">🔑 API Keys</h3>
          <div className="mb-4">
            <Note>
              Keys aren&apos;t editable here on purpose. The scheduled run reads them from GitHub
              Secrets, so a key saved in this app would look stored and never be used by the thing
              that needs it.
            </Note>
          </div>

          <div className="flex flex-col gap-3">
            {secrets.map((s) => (
              <div key={s.key} className="rounded-lg border border-line bg-surface p-3.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-text">{s.label}</span>
                  <span
                    className={`score-pill ${s.configured ? "score-high" : "score-low"}`}
                  >
                    {s.configured ? "set" : "not set"}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-faint">{s.why}</p>
                <p className="mt-1.5 text-[11px] text-faint">
                  Set it in: <code className="text-amber">{s.where}</code>
                </p>
              </div>
            ))}
          </div>

          <h3 className="mt-6 mb-3 text-sm font-semibold">🕐 Schedule</h3>
          <Note>
            8:00 AM and 6:00 PM IST, every day, via{" "}
            <code className="text-amber">.github/workflows/job_alert.yml</code>. Change the cron
            there — it isn&apos;t a setting, because the schedule lives in the workflow file.
          </Note>
        </div>
      </div>
    </>
  );
}
