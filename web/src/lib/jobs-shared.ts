/** Job vocabulary shared by server queries and client components. */

export type JobStatus = "new" | "saved" | "applied" | "dismissed";

export const JOB_STATUSES: readonly JobStatus[] = ["new", "saved", "applied", "dismissed"] as const;

export function isJobStatus(value: unknown): value is JobStatus {
  return typeof value === "string" && (JOB_STATUSES as readonly string[]).includes(value);
}

/** How each source is labelled on the board. */
export const SOURCE_LABELS: Record<string, string> = {
  mycareersfuture: "🇸🇬 MyCareersFuture",
  iimjobs: "🟣 IIMJobs",
  linkedin: "🔵 LinkedIn",
  naukri: "🟠 Naukri",
  bayt: "🟡 Bayt",
  jobstreet: "🔴 JobStreet",
  google_jobs: "🔴 Google",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}
