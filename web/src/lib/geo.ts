/**
 * The target geographies, in the owner's priority order.
 *
 * Framework-free on purpose so it can be tested directly, and so both the board
 * and the scoring prompt read the same ordering. `SOURCES.md` at the repo root
 * explains which portals cover which country.
 */

export type GeoCode = "AE" | "SG" | "GB" | "IE" | "TH" | "MY" | "VN" | "IN";

export interface Geo {
  code: GeoCode;
  label: string;
  flag: string;
  /** 1 is highest. Drives ranking ties and the filter bar's order. */
  priority: number;
}

/** Ordered highest-priority first. Do not re-sort — the order is the meaning. */
export const GEOS: readonly Geo[] = [
  { code: "AE", label: "UAE", flag: "🇦🇪", priority: 1 },
  { code: "SG", label: "Singapore", flag: "🇸🇬", priority: 2 },
  { code: "GB", label: "UK", flag: "🇬🇧", priority: 3 },
  { code: "IE", label: "Ireland", flag: "🇮🇪", priority: 4 },
  { code: "TH", label: "Thailand", flag: "🇹🇭", priority: 5 },
  { code: "MY", label: "Malaysia", flag: "🇲🇾", priority: 6 },
  { code: "VN", label: "Vietnam", flag: "🇻🇳", priority: 7 },
  // India is home, not a target market — it ranks last so local roles never
  // outrank an international one at the same relevance score.
  { code: "IN", label: "India", flag: "🇮🇳", priority: 99 },
] as const;

const BY_CODE = new Map<string, Geo>(GEOS.map((g) => [g.code, g]));

/** Unknown codes sort last rather than throwing — a scraper can emit anything. */
export function geoFor(code: string | null | undefined): Geo {
  if (!code) return UNKNOWN_GEO;
  return BY_CODE.get(code.toUpperCase()) ?? { ...UNKNOWN_GEO, code: code.toUpperCase() as GeoCode };
}

export const UNKNOWN_GEO: Geo = { code: "IN", label: "Unknown", flag: "🌍", priority: 100 };

export function isTargetGeo(code: string | null | undefined): boolean {
  const geo = geoFor(code);
  return geo.priority <= 7;
}

/**
 * Sort key for the board: better score first, then higher-priority geography.
 *
 * Score dominates deliberately. A 9.0 in India is still a better job than a 6.0
 * in Dubai, and burying it would make the board lie about what it found.
 */
export function rankKey(job: { relevanceScore: number; geo: string }): [number, number] {
  return [-job.relevanceScore, geoFor(job.geo).priority];
}

export function compareJobs(
  a: { relevanceScore: number; geo: string },
  b: { relevanceScore: number; geo: string },
): number {
  const [aScore, aGeo] = rankKey(a);
  const [bScore, bGeo] = rankKey(b);
  return aScore - bScore || aGeo - bGeo;
}

/**
 * Flag + name for a filter chip.
 *
 * Lives here rather than beside the filter component because the board renders
 * the chip labels on the server — a "use client" module can't export a function
 * the server calls, only a component it renders.
 */
export function geoLabel(code: string): string {
  const geo = geoFor(code);
  const known = GEOS.some((g) => g.code === code.toUpperCase());
  return known ? `${geo.flag} ${geo.label}` : `🌍 ${code}`;
}
