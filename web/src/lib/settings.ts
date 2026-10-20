import "server-only";

import { eq, sql } from "drizzle-orm";

import { db } from "./db";
import { settings } from "./db/schema";
import { SETTING_KEYS, DEFAULTS, isSettingKey, type Settings } from "./settings-shared";

export * from "./settings-shared";

export async function loadSettings(): Promise<Settings> {
  const rows = await db.select().from(settings);
  const stored = new Map(rows.map((r) => [r.key, r.value]));
  return Object.fromEntries(
    SETTING_KEYS.map((k) => [k, stored.get(k) ?? DEFAULTS[k]]),
  ) as Settings;
}

/** Upsert, so saving twice doesn't need a read first. */
export async function saveSettings(updates: Partial<Settings>): Promise<void> {
  const rows = Object.entries(updates)
    .filter(([k]) => isSettingKey(k))
    .map(([key, value]) => ({ key, value: String(value ?? "") }));

  if (rows.length === 0) return;

  await db
    .insert(settings)
    .values(rows)
    .onConflictDoUpdate({
      target: settings.key,
      set: { value: sql`excluded.value`, updatedAt: sql`now()` },
    });
}

/**
 * LinkedIn session cookies, stored apart from the preference keys above.
 *
 * This *is* a credential, unlike everything else in this table — it grants
 * access to the account. It lives here because there is nowhere else it can
 * reach a CI runner from: dashboard.py wrote it to a local file that only
 * existed on the laptop, which is why ENABLE_LINKEDIN is false in the workflow.
 *
 * Reachable only with DATABASE_URL, which is itself a Vercel/GitHub secret.
 * Deliberately excluded from DEFAULTS so no form ever renders it.
 */
export const LINKEDIN_COOKIES_KEY = "LINKEDIN_COOKIES";

export interface CookieStatus {
  present: boolean;
  count: number;
  hasSessionToken: boolean;
  savedAt: Date | null;
  /** Days since they were saved — computed here so render stays pure. */
  ageDays: number;
  /** Cookies expire in roughly 30 days; warn once we're past three weeks. */
  stale: boolean;
}

export async function linkedInCookieStatus(): Promise<CookieStatus> {
  const [row] = await db
    .select()
    .from(settings)
    .where(eq(settings.key, LINKEDIN_COOKIES_KEY))
    .limit(1);

  if (!row?.value) {
    return { present: false, count: 0, hasSessionToken: false, savedAt: null, ageDays: 0, stale: false };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(row.value);
  } catch {
    return { present: true, count: 0, hasSessionToken: false, savedAt: row.updatedAt, ageDays: 0, stale: false };
  }

  const list = Array.isArray(parsed) ? (parsed as { name?: string }[]) : [];
  const ageDays = (Date.now() - row.updatedAt.getTime()) / 86_400_000;

  return {
    present: true,
    count: list.length,
    hasSessionToken: list.some((c) => c.name === "li_at"),
    savedAt: row.updatedAt,
    ageDays: Math.floor(ageDays),
    stale: ageDays > 21,
  };
}

export interface CookieSaveResult {
  ok: boolean;
  message: string;
}

export async function saveLinkedInCookies(raw: string): Promise<CookieSaveResult> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    return { ok: false, message: `Invalid JSON: ${(e as Error).message}` };
  }

  if (!Array.isArray(parsed)) {
    return { ok: false, message: "Expected a JSON array, the shape Cookie-Editor exports." };
  }

  const list = parsed as { name?: string }[];
  if (!list.some((c) => c.name === "li_at")) {
    // Without li_at the scrape silently returns nothing, so reject it here
    // rather than at 8 AM.
    return { ok: false, message: "No `li_at` cookie found — make sure you were logged in when exporting." };
  }

  await db
    .insert(settings)
    .values({ key: LINKEDIN_COOKIES_KEY, value: JSON.stringify(parsed) })
    .onConflictDoUpdate({
      target: settings.key,
      set: { value: sql`excluded.value`, updatedAt: sql`now()` },
    });

  return { ok: true, message: `Saved ${list.length} cookies.` };
}
