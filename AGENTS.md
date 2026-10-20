# Working on this repo (for any coding agent)

This project is developed by its owner using more than one coding agent (Claude
Code and ChatGPT Codex, switched between depending on which has usage quota
available). This file is the shared contract so agents don't clobber each
other's work. Read it before making any change.

## What this is

A personal job-hunting agent for a PM/Strategy candidate in India. It scrapes
job boards, scores each posting for relevance with Claude, stores everything in
a local SQLite file, and emails a digest of what's worth looking at.

Two entry points:

- **`main.py`** — the headless pipeline. Scrape → dedupe → score → email.
  This is what GitHub Actions runs on a schedule.
- **`dashboard.py`** — a Streamlit UI over the same database
  (`streamlit run dashboard.py`). Preferences, a job board, email settings,
  a manual run button, LinkedIn cookie setup, and a connections/referrals tab.

The pipeline is the product; the dashboard is a window onto it. A behaviour
change belongs in the pipeline modules, not in `dashboard.py`.

## Start of session

1. `git fetch origin && git log origin/main -5` — see what actually landed most
   recently. Don't trust a stale summary in your own context; another agent may
   have merged work since you last looked.
2. `git checkout main && git pull origin main` before branching.
3. Read `README.md` for setup and how to run things.

## Branching and merging — never push directly to `main`

**This is a convention, not a guardrail.** GitHub branch protection needs a Pro
plan on a private repo, so nothing technically rejects a push to `main` here —
which means the discipline has to come from you. If the owner upgrades or makes
the repo public, enable protection and delete this paragraph.

1. Create a branch before making any change:
   `git checkout -b <agent>/<short-kebab-description>`
   — e.g. `claude/linkedin-feed-scraper`, `codex/instahyre-scraper`.
2. Make the change, run the checks below, and commit with a message that
   explains *why*, not just what — lead with the symptom, name the root cause,
   name what you verified.
3. `git push -u origin <branch>`, then `gh pr create`. CI
   (`.github/workflows/ci.yml`) must pass before it's mergeable.
4. Do not merge your own PR unless the owner has explicitly said to.

## Before calling anything done

- `python -m pytest` — the suite must pass. Add tests for new behaviour rather
  than leaving it unverified.
- `python -m ruff check .` — catches syntax errors and undefined names. The
  config in `pyproject.toml` is deliberately narrow: it is a correctness gate,
  not a style police. Don't widen it to make a point about formatting.
- Never commit `.env`, `data/linkedin_cookies.json`, `data/jobs.db`, or any
  real key. `.env.example` documents every variable; keep it current when you
  add one.
- **Scrapers can't be verified by CI.** Every scraper hits a live site that
  requires a browser, and in LinkedIn's case a logged-in session. If you change
  one, run it locally and say in the PR what you actually saw come back — how
  many jobs, from which query. Don't claim a scraper works because the code
  type-checks.

## Architecture, and the decisions behind it

**Which portals we scrape is a decided question — see `SOURCES.md`.** It ranks
every source per geography, names the ones deliberately excluded (Indeed, raw
LinkedIn) and why, and explains why Google Jobs is *not* the fallback. Don't add
a scraper without reading it; don't re-litigate an exclusion without the owner.

**`JobCard` in `models.py` is the one shape everything speaks.** Scrapers emit
it, the scorer enriches it, the DB stores it, the digest renders it. A new
source means a new scraper that returns `JobCard`s — not a new shape that the
rest of the pipeline has to learn about.

**Deduplication is by stable ID, computed at scrape time.** Each scraper builds
`sha1("<source>:<url>")` — and LinkedIn normalises the URL down to the job ID
first, because LinkedIn appends tracking params that would otherwise make the
same job look new every run. `save_job` refuses to overwrite an existing row and
returns `False`, so `main.py` only pays for scoring jobs it has never seen.
**Keep the ID derivation stable**: changing how an ID is computed silently
re-alerts the entire history.

**Scoring is batched on purpose.** `score_relevance_batch` sends 10 jobs per
Claude call on Haiku. One-at-a-time on a bigger model was ~50× the cost for the
same ranking. If you add fields to the scorer's JSON contract, keep the batch
shape — don't revert to per-job calls for convenience.

**`alerted` is the email idempotency flag, and it's set only after a send
succeeds.** `send_digest` returns the IDs it actually sent; `mark_alerted` is
called with those. A crash mid-send re-sends rather than silently dropping
jobs — that's the intended trade.

**No ORM.** `db.py` is plain `sqlite3` and is the only module that touches the
database. JSON-shaped columns (`cv_tweaks`, `referee`, `must_have_skills`,
`resume_gaps`) are serialised there and nowhere else. If you need a new query,
add a function to `db.py` rather than opening a connection elsewhere.

**`config.py` is read once at import and frozen.** `cfg` is a frozen dataclass
built from `.env`. `_require("ANTHROPIC_API_KEY")` raises at import time if the
key is missing — which is why `models.py` and `db.py` deliberately do **not**
import `config`. That's what makes them testable without secrets. Keep it that
way: if a module you're writing needs to be tested in CI, don't reach for `cfg`.

**`intelligence/relevance_scorer.py` constructs its Anthropic client at module
scope.** That means importing it requires a real key, so it can't be imported in
CI. This is a known wart, not a pattern to copy — new modules should take their
client or config as an argument.

**Scrapers are async and Playwright-based** because both IIMJobs and LinkedIn
render their results client-side; `requests` gets you an empty shell. They take
a `db_path` so they can skip detail-page visits for jobs already known
(`get_known_ids`) — the detail page is the expensive part, not the search page.

## Known constraints — don't "fix" these

- **LinkedIn needs hand-exported cookies.** There is no login automation and
  there shouldn't be; LinkedIn challenges scripted logins. Cookies are exported
  from the browser into `data/linkedin_cookies.json` (see the dashboard's
  LinkedIn Setup tab) and go stale after roughly a week. `ENABLE_LINKEDIN` is
  `false` in the scheduled workflow for exactly this reason — the runner has no
  cookies. Don't turn it on in CI.
- **The scheduled run's database lives in the Actions cache**, keyed by run ID
  with a `jobs-db-` prefix restore. This is a deliberate cheap-and-cheerful
  choice, and it can lose history if the cache is evicted. If dedupe starts
  misbehaving in the scheduled run, this is the first thing to check — the fix
  is a real hosted database, not a bigger cache.
- **`data/*.db-wal` can get large.** SQLite is in WAL mode; the `-wal` and
  `-shm` sidecars are ignored by git on purpose. Don't commit them and don't
  switch journal modes to avoid them.

## Scope discipline

`intelligence/org_classifier.py`, `intelligence/resume_gap.py`,
`cv_engine/*`, `referee/connection_lookup.py`, `outputs/sheets_logger.py`, and
`scrapers/instahyre.py` are stubs — a docstring and a signature. The `JobCard`
fields they would fill (`org_stage`, `resume_gaps`, `recommended_cv`,
`cv_tweaks`, `referee`) already exist and are already persisted, so filling one
in is a contained change. **Don't implement one speculatively.** Ask the owner
which is next.
