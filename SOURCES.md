# Source strategy

Which job portals this agent scrapes, in what order, and — just as importantly —
which ones it deliberately does not. Derived from the owner's per-geography
portal research. **Read this before adding a scraper.**

Target roles: Product Manager, AI Product Manager.
Target geographies, in the owner's priority order:

> UAE → Singapore → UK → Ireland → Thailand → Malaysia → Vietnam

The build order below is *not* the same as the geography order, because some
geographies are far cheaper to cover than others. One SEEK parser buys three
countries; UAE is priority 1 but has no free API behind it at all.

## The ranking principle

Sources are ranked by **signal per unit of maintenance**, in this order:

1. **Official structured APIs** — can't break on a CSS change, no anti-bot arms
   race, legally unambiguous. Always preferred, even at lower volume.
2. **One parser, many markets** — shared infrastructure across countries means a
   single well-tested parser covers several geographies.
3. **Server-rendered HTML with schema markup** — JSON-LD `JobPosting` blocks are
   a contract the site maintains for Google, so they're far more stable than
   scraped CSS selectors.
4. **Everything else** — generic crawl plus LLM extraction, accepted only where
   nothing above exists.

Raw volume is explicitly *not* a ranking input. A board that returns 5,000
listings of which four are relevant is worse than one that returns forty good
ones, because every listing costs scoring tokens and dilutes the digest.

## Tier 1 — build first

| # | Source | Geographies | Why it's first |
|---|--------|-------------|----------------|
| 1 | **MyCareersFuture** | Singapore | Open government API, **no key required**. Singapore law requires every Employment Pass / S Pass–eligible role to be posted here for 14 days, which makes it the most complete legal record of foreign-hire-eligible roles in the market — exactly the subset that matters for someone relocating. Structured, free, and cannot be rate-limited out from under us. |
| 2 | **SEEK family** — JobStreet SG, JobStreet MY, JobsDB TH | Singapore, Malaysia, Thailand | One parser, three geographies. SEEK runs shared infrastructure across all of them, so per-country differences are configuration, not code. Best coverage-per-unit-of-work of any source available. |
| 3 | **Bayt** | UAE | UAE is priority-1 geography and has no free API. Bayt is the largest MENA board, server-rendered, and publishes JSON-LD `JobPosting` markup — so extraction keys off a stable schema rather than fragile selectors. |

## Tier 2 — next

| # | Source | Geographies | Why |
|---|--------|-------------|-----|
| 4 | **GulfTalent** | UAE | Best signal-to-noise in MENA for mid-senior and managerial roles. Lower volume than Bayt, higher hit rate. |
| 5 | **Welcome to the Jungle** (formerly Otta) | UK, Ireland | Purpose-built for curated tech and product roles. The single best PM-specific source in the UK, and it covers Dublin too. |
| 6 | **IrishJobs.ie** | Ireland | Most established indigenous Irish board. Structured and moderate to parse. |
| 7 | **Naukrigulf** | UAE | Naukri-family, so it shares structure with a site family we already understand, and it indexes India→UAE relocation roles specifically — directly relevant to this candidate's profile. |

## Tier 3 — opportunistic

Added through the **generic portal adapter** (below) rather than as bespoke
modules, so each one costs a config entry rather than a new file: Wellfound,
NodeFlair, Glints, Jobs.ie, Hiredly, ITviec.

## The fallback layer — and why it isn't Google Jobs

**The fallback is a generic crawl-and-extract adapter**: Crawl4AI renders a
portal's search page, hands the markdown to Claude Haiku, and Claude returns
`JobCard` fields. Adding a portal becomes a config entry naming a URL pattern
and a couple of hints. It is open source and self-hosted, so it runs free on the
GitHub Actions minutes we already use, and it degrades gracefully: when a
bespoke parser breaks, the generic adapter still returns usable rows.

**Google Jobs is explicitly rejected as the fallback**, despite being the
obvious candidate:

- `scrapers/google_jobs.py` already drives headless Chromium against Google's
  jobs SERP, and it is already disabled (`ENABLE_GOOGLE_JOBS=false`). GitHub
  Actions runners have datacenter IPs, which Google CAPTCHAs aggressively.
- It offers no reliable geography control, which is the entire point of this
  work — we need results *for Dubai*, not results that mention Dubai.
- The free SERP API tiers that would fix both problems don't fit: SerpApi gives
  250 searches/month against roughly 1,200 needed, and the owner has ruled out
  paid APIs.

`google_jobs.py` should be retired rather than repaired. See
`project_job_alert_crawl_stack` reasoning: Careerjet, Jooble, Firecrawl and
Adzuna were each evaluated and rejected for this use.

## Deliberately not scraped

Don't add these without the owner asking — each was considered and dropped.

- **Indeed (all geographies).** ToS explicitly prohibits automated access,
  Indeed has pursued legal action, and it actively blocks scrapers. In the
  owner's own research it ranks only as a "volume backup" in every market — so
  it carries the highest legal and breakage risk of any source in exchange for
  the least differentiated data.
- **Raw LinkedIn scraping.** Heavy anti-bot, and ToS prohibits it. The existing
  `scrapers/linkedin.py` runs against the owner's *own* logged-in session for
  personal use and stays as-is; do not generalise it into a multi-geography
  scraper or run it from CI.
- **Vietnam via the existing Apify scraper.** Works, but costs roughly $1.50 per
  1,000 jobs. The owner has ruled out paid services.
- **JobThai, TopCV.** Primarily Thai- and Vietnamese-language, needing bilingual
  parsing, for geographies ranked 5th and 7th. Poor effort-to-value until the
  higher-priority markets are done.
- **hackajob.** Profile-gated; there is no public listing surface to parse.

## Adding a source

1. Check it isn't in "Deliberately not scraped" above.
2. Prefer an official API. If one exists, use it even if volume is lower.
3. If the site publishes JSON-LD `JobPosting` markup, key off that, not CSS.
4. Otherwise use the generic adapter — don't hand-write a parser for a Tier 3
   board.
5. Set `geo` on every `JobCard` you emit. Scoring and the job board both
   filter on it.
6. Record what you actually saw come back in the PR — how many jobs, which
   query, which country. CI cannot verify a scraper for you.
