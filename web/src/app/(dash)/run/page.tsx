import { TabHeader } from "@/components/Character";
import { RunAgentButton } from "@/components/RunAgent";
import { Metric, Note } from "@/components/ui";
import { TAB_CHARACTERS } from "@/lib/characters";
import { GITHUB_REPO, secretStatuses } from "@/lib/env-status";
import { boardStats } from "@/lib/jobs";
import { estimateQueries, loadSettings } from "@/lib/settings";

export const dynamic = "force-dynamic";

const SOURCE_LABELS: Record<string, string> = {
  ENABLE_MYCAREERSFUTURE: "MyCareersFuture",
  ENABLE_IIMJOBS: "IIMJobs",
  ENABLE_LINKEDIN: "LinkedIn",
  ENABLE_GOOGLE_JOBS: "Google Jobs",
};

export default async function RunPage() {
  const [settings, stats] = await Promise.all([loadSettings(), boardStats()]);
  const dispatch = secretStatuses().find((s) => s.key === "GITHUB_DISPATCH_TOKEN");

  const active = (Object.keys(SOURCE_LABELS) as (keyof typeof settings)[]).filter(
    (k) => settings[k] === "true",
  );
  const queries = estimateQueries(settings);

  return (
    <>
      <TabHeader title="Run Agent" character={TAB_CHARACTERS.run} />

      <div className="grid gap-8 lg:grid-cols-[1fr_2fr]">
        <div>
          <h3 className="mb-3 text-sm font-semibold">📊 Current Stats</h3>
          <div className="flex flex-col gap-2">
            <Metric label="Total in DB" value={stats.total} />
            <Metric label="Scored" value={stats.scored} />
            <Metric label={`Above ${settings.RELEVANCE_SCORE_THRESHOLD}`} value={stats.goodFit} />
          </div>
          {stats.lastRun ? (
            <p className="mt-3 text-[11px] text-faint">
              🕐 Last scrape: {stats.lastRun.toISOString().slice(0, 16).replace("T", " ")} UTC
            </p>
          ) : null}

          <h3 className="mt-6 mb-3 text-sm font-semibold">📡 Active Sources</h3>
          <div className="flex flex-col gap-1.5">
            {active.length === 0 ? (
              <p className="text-xs text-faint">None enabled — see Preferences.</p>
            ) : (
              active.map((k) => (
                <p key={k} className="text-sm text-[#6ee7b7]">
                  ✅ {SOURCE_LABELS[k]}
                </p>
              ))
            )}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">🚀 Launch</h3>

          {dispatch?.configured ? null : (
            <div className="mb-4">
              <Note tone="warn">
                The button needs a <code className="text-amber">GITHUB_DISPATCH_TOKEN</code> in
                Vercel&apos;s environment variables — a fine-grained token with{" "}
                <strong>Actions: write</strong> scoped to this repo only. Until then, run it from{" "}
                <a
                  href={`https://github.com/${GITHUB_REPO}/actions/workflows/job_alert.yml`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4"
                >
                  the Actions tab
                </a>
                .
              </Note>
            </div>
          )}

          <RunAgentButton repo={GITHUB_REPO} />

          <h3 className="mt-7 mb-3 text-sm font-semibold">🤖 Automation</h3>
          <Note>
            Runs on its own at <strong className="text-text">8 AM</strong> and{" "}
            <strong className="text-text">6 PM IST</strong> via{" "}
            <code className="text-amber">.github/workflows/job_alert.yml</code>. This button fires
            the same workflow early — the pipeline drives a browser for up to twenty minutes, which
            is why it runs there rather than inside this page.
          </Note>

          <p className="mt-4 text-xs text-dim">
            <strong className="text-text">Estimated run:</strong>{" "}
            <code className="text-amber">{queries} queries</code> ·{" "}
            <code className="text-amber">~10–20 min</code> ·{" "}
            <code className="text-amber">~${(queries * 0.001).toFixed(2)}</code> per run
          </p>
        </div>
      </div>
    </>
  );
}
