import "server-only";

import { and, asc, desc, eq, gte, ilike, inArray, lte, ne, or, sql } from "drizzle-orm";

import { db } from "./db";
import type { JobStatus } from "./jobs-shared";
import { jobs, type Job } from "./db/schema";

export * from "./jobs-shared";

export interface BoardFilters {
  search?: string;
  minScore?: number;
  maxScore?: number;
  geos?: string[];
  sources?: string[];
  statuses?: JobStatus[];
  limit?: number;
}

/**
 * The board query.
 *
 * Ordering happens in SQL so `limit` means "the best N", not "N arbitrary rows
 * then sorted". Unscored jobs (score 0) still appear — they're newly scraped,
 * not bad, and hiding them would make the board look empty after a fresh run.
 */
export async function listJobs(filters: BoardFilters = {}): Promise<Job[]> {
  const {
    search,
    minScore = 0,
    maxScore = 10,
    geos = [],
    sources = [],
    statuses = [],
    limit = 300,
  } = filters;

  const where = [gte(jobs.relevanceScore, minScore), lte(jobs.relevanceScore, maxScore)];

  if (geos.length > 0) where.push(inArray(jobs.geo, geos));
  if (sources.length > 0) where.push(inArray(jobs.source, sources));

  if (statuses.length > 0) {
    where.push(inArray(jobs.status, statuses));
  } else {
    // Dismissed jobs are hidden unless asked for by name. Nothing deletes them —
    // they still suppress re-alerts — they just don't clutter the default view.
    where.push(ne(jobs.status, "dismissed"));
  }

  if (search) {
    const term = `%${search}%`;
    const match = or(ilike(jobs.title, term), ilike(jobs.company, term), ilike(jobs.location, term));
    if (match) where.push(match);
  }

  return db
    .select()
    .from(jobs)
    .where(and(...where))
    .orderBy(desc(jobs.relevanceScore), desc(jobs.scrapedAt))
    .limit(limit);
}

export async function setJobStatus(id: string, status: JobStatus): Promise<void> {
  await db.update(jobs).set({ status, statusAt: new Date() }).where(eq(jobs.id, id));
}

export interface BoardStats {
  total: number;
  newCount: number;
  scored: number;
  highFit: number;
  goodFit: number;
  alerted: number;
  saved: number;
  lastRun: Date | null;
}

/** One round trip for every counter the sidebar and tabs display. */
export async function boardStats(): Promise<BoardStats> {
  const [row] = await db
    .select({
      total: sql<number>`count(*)::int`,
      newCount: sql<number>`count(*) filter (where ${jobs.status} = 'new')::int`,
      scored: sql<number>`count(*) filter (where ${jobs.relevanceScore} > 0)::int`,
      highFit: sql<number>`count(*) filter (where ${jobs.relevanceScore} >= 8)::int`,
      goodFit: sql<number>`count(*) filter (where ${jobs.relevanceScore} >= 7)::int`,
      alerted: sql<number>`count(*) filter (where ${jobs.alerted})::int`,
      saved: sql<number>`count(*) filter (where ${jobs.status} = 'saved')::int`,
      lastRun: sql<Date | null>`max(${jobs.scrapedAt})`,
    })
    .from(jobs);

  return {
    total: Number(row?.total ?? 0),
    newCount: Number(row?.newCount ?? 0),
    scored: Number(row?.scored ?? 0),
    highFit: Number(row?.highFit ?? 0),
    goodFit: Number(row?.goodFit ?? 0),
    alerted: Number(row?.alerted ?? 0),
    saved: Number(row?.saved ?? 0),
    lastRun: row?.lastRun ? new Date(row.lastRun) : null,
  };
}

export interface Facet {
  value: string;
  total: number;
}

/** Counts per geography and per source, for the filter chips. */
export async function facets(): Promise<{ geos: Facet[]; sources: Facet[] }> {
  const [geoRows, sourceRows] = await Promise.all([
    db
      .select({ value: jobs.geo, total: sql<number>`count(*)::int` })
      .from(jobs)
      .where(ne(jobs.status, "dismissed"))
      .groupBy(jobs.geo),
    db
      .select({ value: jobs.source, total: sql<number>`count(*)::int` })
      .from(jobs)
      .where(ne(jobs.status, "dismissed"))
      .groupBy(jobs.source)
      .orderBy(asc(jobs.source)),
  ]);

  return {
    geos: geoRows.map((r) => ({ value: r.value, total: Number(r.total) })),
    sources: sourceRows.map((r) => ({ value: r.value, total: Number(r.total) })),
  };
}
