# Job Alert Agent

> **From the What I Built (WIB) podcast, Episode 01.** This is a clean public copy of the
> agent shown on the show. It contains no keys: bring your own. Copy `.env.example` to
> `.env` (and `web/.env.example` to `web/.env.local`), add your repository secrets, then
> uncomment the `schedule:` block in `.github/workflows/job_alert.yml` to run it twice a day.
> The only paid piece is the Anthropic API; GitHub Actions, Vercel, Neon and Resend have free tiers.


A personal job-hunting agent. It scrapes job boards for PM/Strategy roles,
scores every posting against your profile with Claude, remembers what it has
already seen, and emails you a digest of the handful worth opening.

Built to run unattended twice a day, with a local dashboard for the times you
want to look around yourself.

## How a run works

```
scrape  →  dedupe  →  score  →  digest
```

1. **Scrape** — each enabled source returns `JobCard`s. IIMJobs and LinkedIn are
   Playwright-driven because both render results client-side.
2. **Dedupe** — every card carries a stable `sha1("<source>:<url>")` ID.
   `save_job` refuses duplicates, so only genuinely new jobs move on.
3. **Score** — new jobs go to Claude Haiku in batches of ten and come back with
   a 0–10 relevance score, a role type, and an org stage.
4. **Digest** — anything above `RELEVANCE_SCORE_THRESHOLD` that hasn't been
   alerted yet goes out in one email via Resend, and is marked as alerted.

Everything lands in `data/jobs.db` (SQLite, WAL mode).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env     # then fill it in
```

At minimum you need `ANTHROPIC_API_KEY`. Email is optional — without
`RESEND_API_KEY` the run scrapes and scores but skips the digest.

## Running it

```bash
python main.py                  # one full pipeline run
streamlit run dashboard.py      # the dashboard
```

The dashboard has six tabs: Preferences (edits `.env` in place), Job Board,
Alerts & Email, Run Agent, LinkedIn Setup, and Connections & Referrals.

## Sources

The agent targets PM and AI PM roles across UAE, Singapore, UK, Ireland,
Thailand, Malaysia and Vietnam. **`SOURCES.md` is the decision record** — which
portals are built first, which are deliberately excluded, and why.

| Source          | Status  | Geography       | Notes                                   |
| --------------- | ------- | --------------- | --------------------------------------- |
| MyCareersFuture | Planned | Singapore       | Open government API, no key required.    |
| SEEK family     | Planned | SG, MY, TH      | One parser, three markets.               |
| Bayt            | Planned | UAE             | JSON-LD job schema.                      |
| IIMJobs         | Working | India           | Default-on. No auth needed.              |
| LinkedIn        | Working | All             | Hand-exported cookies; off in CI.        |
| Naukri          | Written | India           | Not wired into `main.py`.                |
| Google Jobs     | Retired | —               | CAPTCHA'd from CI; see `SOURCES.md`.     |
| Instahyre       | Stub    | India           | Signature only.                          |

### LinkedIn cookies

There's no login automation on purpose — LinkedIn challenges scripted logins.
Export your session cookies with a browser extension into
`data/linkedin_cookies.json` (the dashboard's LinkedIn Setup tab walks through
it). They go stale after roughly a week.

## Scheduled runs

`.github/workflows/job_alert.yml` runs the pipeline at 8 AM and 6 PM IST, and
on manual dispatch. It needs these repository secrets:

`ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `ALERT_TO_EMAIL`,
`TARGET_ROLES`, `TARGET_LOCATIONS`

The database is carried between runs in the Actions cache. LinkedIn is disabled
there because the runner has no cookies.

## Working on this

`npm`-free, but the same idea: `pytest` and `ruff check .` before anything is
done. **Read `AGENTS.md` first** — it's the contract for both the humans and
the coding agents that work on this repo, and it explains why the pieces are
shaped the way they are.

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```
