import { TabHeader } from "@/components/Character";
import { JobFilters } from "@/components/JobFilters";
import { JobRow, type JobView } from "@/components/JobRow";
import { Metric, Note } from "@/components/ui";
import { TAB_CHARACTERS } from "@/lib/characters";
import { geoLabel } from "@/lib/geo";
import { boardStats, facets, isJobStatus, listJobs, sourceLabel, type JobStatus } from "@/lib/jobs";

export const dynamic = "force-dynamic";

function csv(raw: string | undefined): string[] {
  return (raw ?? "").split(",").filter(Boolean);
}

export default async function JobBoardPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; min?: string; geo?: string; source?: string; status?: string }>;
}) {
  const params = await searchParams;
  const minScore = Number.isFinite(Number(params.min)) ? Number(params.min) : 0;
  const statuses = csv(params.status).filter(isJobStatus) as JobStatus[];

  const [rows, { geos, sources }, stats] = await Promise.all([
    listJobs({
      search: params.q,
      minScore,
      geos: csv(params.geo),
      sources: csv(params.source),
      statuses,
    }),
    facets(),
    boardStats(),
  ]);

  const jobs: JobView[] = rows.map((j) => ({
    id: j.id,
    title: j.title,
    company: j.company,
    location: j.location,
    geo: j.geo,
    jobUrl: j.jobUrl,
    source: j.source,
    sourceLabel: sourceLabel(j.source),
    relevanceScore: j.relevanceScore,
    roleType: j.roleType,
    orgStage: j.orgStage,
    mustHaveSkills: j.mustHaveSkills ?? [],
    postedDate: j.postedDate ? j.postedDate.toISOString() : null,
    scrapedAt: j.scrapedAt.toISOString(),
    status: j.status,
    alerted: j.alerted,
  }));

  const shown = jobs.length;
  const high = jobs.filter((j) => j.relevanceScore >= 8).length;
  const good = jobs.filter((j) => j.relevanceScore >= 7).length;

  return (
    <>
      <TabHeader title="Job Board" character={TAB_CHARACTERS.board} />

      {stats.total === 0 ? (
        <Note>
          No jobs yet. Go to <strong className="text-amber">▶️ Run Agent</strong> to scrape your
          first batch.
        </Note>
      ) : (
        <>
          <JobFilters
            geoFacets={geos.map((g) => ({ value: g.value, label: geoLabel(g.value), total: g.total }))}
            sourceFacets={sources.map((s) => ({
              value: s.value,
              label: sourceLabel(s.value),
              total: s.total,
            }))}
          />

          <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-5">
            <Metric label="Showing" value={shown} />
            <Metric label="🔥 High-fit (≥8)" value={high} />
            <Metric label="✅ Good-fit (≥7)" value={good} />
            <Metric label="📬 Alerted" value={stats.alerted} />
            <Metric label="📌 Saved" value={stats.saved} />
          </div>

          {stats.scored === 0 ? (
            <div className="mb-5">
              <Note tone="warn">
                Nothing has been scored yet, so every job shows 0.0. That happens when{" "}
                <code className="text-amber">ANTHROPIC_API_KEY</code> is missing or rejected —
                scraping still works, scoring silently doesn&apos;t.
              </Note>
            </div>
          ) : null}

          {jobs.length === 0 ? (
            <Note>No jobs match your filters.</Note>
          ) : (
            <div className="flex flex-col gap-2.5">
              {jobs.map((job) => (
                <JobRow key={job.id} job={job} />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
