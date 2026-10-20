import { boolean, doublePrecision, index, jsonb, pgTable, text, timestamp } from "drizzle-orm/pg-core";

/**
 * One scraped job posting, at every stage of its life.
 *
 * This table is written by the Python pipeline (`db.py`) and read by this app.
 * Drizzle owns the schema — `npm run db:push` is what creates it — but Python
 * writes to it with plain SQL, so **column names here are a contract**. Renaming
 * one without changing `db.py` in the same commit breaks the nightly run
 * silently: the scrape succeeds and nothing is ever stored.
 */
export const jobs = pgTable(
  "jobs",
  {
    /** sha1("<source>:<url>") — computed at scrape time. See SOURCES.md. */
    id: text("id").primaryKey(),
    title: text("title").notNull(),
    company: text("company").notNull(),
    location: text("location").notNull().default(""),
    /**
     * ISO 3166-1 alpha-2, uppercased: AE, SG, GB, IE, TH, MY, VN, IN.
     * Set by the scraper, never inferred here — a scraper knows which country
     * it queried, whereas "Bangalore, Remote" tells the reader nothing.
     */
    geo: text("geo").notNull().default("IN"),
    jobUrl: text("job_url").notNull(),
    description: text("description").notNull().default(""),
    source: text("source").notNull(),

    postedDate: timestamp("posted_date", { withTimezone: true }),
    scrapedAt: timestamp("scraped_at", { withTimezone: true }).notNull().defaultNow(),

    /** 0–10, from the batched Claude scorer. 0 means "not scored yet". */
    relevanceScore: doublePrecision("relevance_score").notNull().default(0),
    roleType: text("role_type"),
    orgStage: text("org_stage"),

    recommendedCv: text("recommended_cv"),
    cvTweaks: jsonb("cv_tweaks").$type<string[]>().notNull().default([]),
    referee: jsonb("referee").$type<{ name: string; role: string; linkedin_url: string } | null>(),
    mustHaveSkills: jsonb("must_have_skills").$type<string[]>().notNull().default([]),
    resumeGaps: jsonb("resume_gaps").$type<string[]>().notNull().default([]),

    /** True once included in a sent digest. Set only after a send succeeds. */
    alerted: boolean("alerted").notNull().default(false),

    /**
     * What the owner did with it: new | saved | applied | dismissed.
     * Written by this app only — the pipeline never touches it, so a re-scrape
     * can't resurrect something already dismissed.
     */
    status: text("status").notNull().default("new"),
    statusAt: timestamp("status_at", { withTimezone: true }),
  },
  (t) => [
    // The board's default view: unrejected, best first, newest first.
    index("jobs_score_idx").on(t.relevanceScore, t.scrapedAt),
    index("jobs_geo_idx").on(t.geo),
    index("jobs_status_idx").on(t.status),
  ],
);

export type Job = typeof jobs.$inferSelect;

/**
 * Preferences the board writes and the Python pipeline reads.
 *
 * dashboard.py edited `.env` in place, which has no equivalent on Vercel — and
 * wouldn't reach a GitHub Actions run anyway. A row here does: `config.py`
 * reads this table first and falls back to the environment.
 *
 * **Preferences only, never secrets.** API keys live in GitHub Secrets and
 * Vercel env, because those are what the scheduled run actually reads; a key
 * pasted into a web form would look saved and silently never be used.
 */
export const settings = pgTable("settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull().default(""),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export type Setting = typeof settings.$inferSelect;
