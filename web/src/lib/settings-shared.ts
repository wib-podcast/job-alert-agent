/**
 * Preference shapes and pure helpers.
 *
 * Deliberately free of `server-only` and of any database import: the
 * Preferences and Alerts forms are client components and need these. Anything
 * that touches the database belongs in `settings.ts` instead.
 */

export const DEFAULTS = {
  TARGET_ROLES: "Product Manager,AI Product Manager,Senior Product Manager",
  TARGET_LOCATIONS: "Singapore,Dubai,London,Dublin,Remote",
  TARGET_GEOS: "AE,SG,GB,IE,TH,MY,VN",
  RELEVANCE_SCORE_THRESHOLD: "7.0",
  MAX_JOBS_PER_QUERY: "30",
  DAYS_SINCE_POSTED: "14",
  MAX_JOBS_IN_EMAIL: "10",
  LLM_MODEL: "claude-haiku-4-5",
  ENABLE_IIMJOBS: "true",
  ENABLE_MYCAREERSFUTURE: "true",
  ENABLE_LINKEDIN: "false",
  ENABLE_GOOGLE_JOBS: "false",
} as const;

export type SettingKey = keyof typeof DEFAULTS;
export type Settings = Record<SettingKey, string>;

export const SETTING_KEYS = Object.keys(DEFAULTS) as SettingKey[];

export function isSettingKey(k: string): k is SettingKey {
  // Object.hasOwn, not `in`: `"__proto__" in DEFAULTS` is true via the
  // prototype chain, so `in` would let a form field named __proto__ through
  // and into the settings table.
  return Object.hasOwn(DEFAULTS, k);
}

export const SOURCE_TOGGLE_KEYS = [
  "ENABLE_IIMJOBS",
  "ENABLE_MYCAREERSFUTURE",
  "ENABLE_LINKEDIN",
  "ENABLE_GOOGLE_JOBS",
] as const;

export function csvToList(raw: string): string[] {
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}

export function listToCsv(items: string[]): string {
  return items.map((s) => s.trim()).filter(Boolean).join(",");
}

/**
 * Queries one scheduled run will issue: roles × locations × enabled sources.
 *
 * MyCareersFuture ignores locations (it is Singapore by definition), so it
 * counts once per role rather than once per role-location pair. Getting this
 * wrong overstates the estimate by roughly the location count.
 */
export function estimateQueries(s: Settings): number {
  const roles = csvToList(s.TARGET_ROLES).length;
  const locations = Math.max(csvToList(s.TARGET_LOCATIONS).length, 1);

  const perLocationSources = [s.ENABLE_IIMJOBS, s.ENABLE_LINKEDIN, s.ENABLE_GOOGLE_JOBS].filter(
    (v) => v === "true",
  ).length;
  const perRoleSources = [s.ENABLE_MYCAREERSFUTURE].filter((v) => v === "true").length;

  return roles * locations * perLocationSources + roles * perRoleSources;
}
