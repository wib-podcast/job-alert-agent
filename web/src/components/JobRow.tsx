"use client";

import { useTransition } from "react";

import { updateStatus } from "@/app/actions";
import { geoFor } from "@/lib/geo";
import { JOB_STATUSES, type JobStatus } from "@/lib/jobs-shared";

import { Pill, ScorePill, scoreDot } from "./ui";

export interface JobView {
  id: string;
  title: string;
  company: string;
  location: string;
  geo: string;
  jobUrl: string;
  source: string;
  sourceLabel: string;
  relevanceScore: number;
  roleType: string | null;
  orgStage: string | null;
  mustHaveSkills: string[];
  postedDate: string | null;
  scrapedAt: string;
  status: string;
  alerted: boolean;
}

function day(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

/**
 * One job, collapsed to a summary line and expandable for detail — the
 * st.expander from dashboard.py, with the same summary format:
 * dot · score · title @ company · location · source
 */
export function JobRow({ job }: { job: JobView }) {
  const [pending, start] = useTransition();
  const geo = geoFor(job.geo);

  function change(status: JobStatus) {
    if (status === job.status) return;
    start(async () => {
      await updateStatus(job.id, status);
    });
  }

  return (
    <details className={`card ${pending ? "opacity-50" : ""}`}>
      <summary>
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm">
          <span aria-hidden>{scoreDot(job.relevanceScore)}</span>
          <ScorePill score={job.relevanceScore} />
          <span className="font-medium text-text">{job.title}</span>
          <span className="text-faint">@</span>
          <span className="font-semibold text-text">{job.company}</span>
          <span className="text-faint">·</span>
          <span className="text-dim">
            {geo.flag} {job.location || geo.label}
          </span>
          <span className="text-faint">·</span>
          <span className="text-dim">{job.sourceLabel}</span>
          {job.alerted ? <span title="Included in a sent digest">📬</span> : null}
        </div>
      </summary>

      <div className="card-body">
        <div className="flex flex-col gap-4 sm:flex-row sm:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-xs text-dim">
              <span className="text-faint">Role type:</span>{" "}
              <Pill>{job.roleType || "—"}</Pill>
              {job.orgStage ? (
                <>
                  {" "}
                  <span className="text-faint">Stage:</span> <Pill>{job.orgStage}</Pill>
                </>
              ) : null}
            </p>

            {job.mustHaveSkills.length > 0 ? (
              <p className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs text-faint">
                <span>Key skills:</span>
                {job.mustHaveSkills.slice(0, 8).map((s) => (
                  <Pill key={s}>{s}</Pill>
                ))}
              </p>
            ) : null}

            <p className="mt-2.5 text-[11px] text-faint">
              📅 Posted: {day(job.postedDate)} · Scraped: {day(job.scrapedAt)}
            </p>

            <a
              href={job.jobUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary mt-3 inline-block px-4 py-2 text-xs"
            >
              🔗 Open Job →
            </a>
          </div>

          <div className="sm:w-40">
            <span className="mb-1.5 block text-[11px] text-faint">Status</span>
            <select
              className="field w-full px-2.5 py-2 text-xs"
              value={job.status}
              disabled={pending}
              onChange={(e) => change(e.target.value as JobStatus)}
              aria-label={`Status for ${job.title}`}
            >
              {JOB_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </details>
  );
}
