"""
LinkedIn Connections Scraper
Phase 1 — read LinkedIn's official data export CSV (data/Connections.csv)
           → reliable, no bot detection, gives name + company + title + URL
Phase 2 — visit each profile with Playwright to enrich with education,
           tenure, seniority, mutual connections, etc.
Writes incrementally to data/connections.csv (crash-safe)
Updates data/connections_progress.json for the Streamlit dashboard

HOW TO GET data/Connections.csv:
  1. linkedin.com/mypreferences/d/data-privacy
  2. "Get a copy of your data" → select "Connections" only → Request archive
  3. Download arrives by email in ~10 minutes
  4. Unzip → place Connections.csv at job-alert-agent/data/Connections.csv
"""
from __future__ import annotations

import asyncio
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

ROOT = Path(__file__).parent.parent
COOKIES_PATH = ROOT / "data" / "linkedin_cookies.json"
EXPORT_CSV_PATH = ROOT / "data" / "Connections.csv"   # LinkedIn official export
CSV_PATH = ROOT / "data" / "connections.csv"           # our enriched output
PROGRESS_PATH = ROOT / "data" / "connections_progress.json"

DELAY_BETWEEN_PROFILES = 2.5   # seconds — keep LinkedIn happy
STALE_DAYS = 30                # re-scrape profiles older than this

CSV_FIELDS = [
    "name", "profile_url", "headline",
    "current_company", "current_title", "months_in_role",
    "seniority", "location",
    "institutes", "degree", "grad_year",
    "total_exp_years", "mutual_connections",
    "scraped_at",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def write_progress(done: int, total: int, status: str, current: str = "") -> None:
    PROGRESS_PATH.write_text(json.dumps({
        "done": done,
        "total": total,
        "status": status,   # "phase1" | "phase2" | "done" | "error"
        "current": current,
        "updated_at": datetime.now().isoformat(),
    }, indent=2))


def derive_seniority(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["chief", "cxo", "cto", "ceo", "coo", "cpo"]):
        return "C-Suite"
    if any(x in t for x in ["vp ", "vice president", "head of", "head,"]):
        return "VP/Head"
    if "director" in t:
        return "Director"
    if any(x in t for x in ["principal", "staff "]):
        return "Principal/Staff"
    if any(x in t for x in ["manager", " lead", "lead "]):
        return "Manager/Lead"
    if any(x in t for x in ["senior", "sr."]):
        return "Senior IC"
    if any(x in t for x in ["intern", "trainee", "apprentice"]):
        return "Intern"
    return "IC"


def months_since(date_str: str) -> Optional[int]:
    """Parse 'Jan 2023' or '2023' and return months elapsed."""
    for fmt in ("%b %Y", "%B %Y", "%Y"):
        try:
            start = datetime.strptime(date_str.strip(), fmt)
            now = datetime.now()
            return (now.year - start.year) * 12 + (now.month - start.month)
        except ValueError:
            continue
    return None


async def load_cookies(context: BrowserContext) -> None:
    raw = json.loads(COOKIES_PATH.read_text())
    playwright_cookies = []
    for c in raw:
        cookie: dict = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".linkedin.com"),
            "path": c.get("path", "/"),
        }
        if "expirationDate" in c:
            cookie["expires"] = int(c["expirationDate"])
        if "secure" in c:
            cookie["secure"] = c["secure"]
        if "httpOnly" in c:
            cookie["httpOnly"] = c["httpOnly"]
        ss = c.get("sameSite", "")
        if ss in ("Strict", "Lax", "None"):
            cookie["sameSite"] = ss
        playwright_cookies.append(cookie)
    await context.add_cookies(playwright_cookies)


# ── Phase 1: read LinkedIn official export CSV ────────────────────────────────

def load_connections_from_export() -> list[dict]:
    """
    Parse LinkedIn's official Connections.csv export.
    Columns vary slightly by export date but always include:
      First Name, Last Name, URL, Email Address, Company, Position, Connected On
    Returns list of dicts with keys: name, profile_url, headline
    """
    print("Phase 1: reading LinkedIn export CSV…", flush=True)
    write_progress(0, 0, "phase1", "Reading Connections.csv…")

    if not EXPORT_CSV_PATH.exists():
        raise FileNotFoundError(
            f"LinkedIn export CSV not found at {EXPORT_CSV_PATH}\n"
            "Download it from: linkedin.com/mypreferences/d/data-privacy\n"
            "→ 'Get a copy of your data' → Connections only → wait ~10 min → drop Connections.csv in data/"
        )

    connections: list[dict] = []
    # LinkedIn export has a 3-line notes header before the actual CSV — skip it
    with open(EXPORT_CSV_PATH, newline="", encoding="utf-8-sig") as f:
        content = f.read()

    # Find where the actual CSV header starts
    lines = content.splitlines()
    header_idx = 0
    for i, line in enumerate(lines):
        if "First Name" in line or "first name" in line.lower():
            header_idx = i
            break

    csv_content = "\n".join(lines[header_idx:])
    reader = csv.DictReader(csv_content.splitlines())

    for row in reader:
        # Normalise column names (LinkedIn sometimes changes capitalisation)
        norm = {k.strip().lower(): v.strip() for k, v in row.items()}

        first = norm.get("first name", "")
        last = norm.get("last name", "")
        name = f"{first} {last}".strip()

        url = norm.get("url", "") or norm.get("profile url", "")
        # Ensure full URL
        if url and not url.startswith("http"):
            url = "https://www.linkedin.com" + url
        url = url.split("?")[0].rstrip("/")

        company = norm.get("company", "")
        position = norm.get("position", "")
        headline = f"{position} at {company}" if position and company else (position or company)

        if name and url:
            connections.append({
                "name": name,
                "profile_url": url,
                "headline": headline,
                # Pre-fill from export so even un-enriched rows have basics
                "current_company": company,
                "current_title": position,
            })

    print(f"Loaded {len(connections)} connections from export", flush=True)
    return connections


# ── Phase 1 (fallback): headful browser when export CSV not available ─────────

async def scrape_connections_headful(page: Page) -> list[dict]:
    """
    Fallback Phase 1 using a visible (non-headless) browser.
    headless=False bypasses LinkedIn's bot detection on the connections page.
    """
    print("Phase 1 (browser): opening connections page in visible browser…", flush=True)
    print("NOTE: A Chrome window will open — do not close it.", flush=True)
    write_progress(0, 0, "phase1", "Opening browser — do not close the Chrome window…")

    await page.goto(
        "https://www.linkedin.com/mynetwork/invite-manager/connections/",
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    await asyncio.sleep(4)

    # Check if we landed on a login page
    current_url = page.url
    if "login" in current_url or "checkpoint" in current_url:
        raise RuntimeError(
            "LinkedIn redirected to login — cookies are expired. "
            "Re-export cookies from the LinkedIn Setup tab."
        )

    connections: list[dict] = []
    seen_urls: set[str] = set()
    no_change_rounds = 0

    while no_change_rounds < 5:
        cards = await page.query_selector_all(".mn-connection-card")
        added = 0
        for card in cards:
            try:
                link_el = await card.query_selector("a.mn-connection-card__link")
                if not link_el:
                    continue
                href = (await link_el.get_attribute("href")) or ""
                profile_url = ("https://www.linkedin.com" + href if href.startswith("/") else href)
                profile_url = profile_url.split("?")[0].rstrip("/")
                if not profile_url or profile_url in seen_urls:
                    continue
                seen_urls.add(profile_url)

                name_el = await card.query_selector(".mn-connection-card__name")
                name = (await name_el.inner_text()).strip() if name_el else ""

                occ_el = await card.query_selector(".mn-connection-card__occupation")
                headline = (await occ_el.inner_text()).strip() if occ_el else ""

                connections.append({"name": name, "profile_url": profile_url, "headline": headline})
                added += 1
            except Exception:
                continue

        no_change_rounds = 0 if added else no_change_rounds + 1
        write_progress(0, len(connections), "phase1", f"Found {len(connections)} connections…")
        await page.evaluate("window.scrollBy(0, 3000)")
        await asyncio.sleep(1.5)

    print(f"Found {len(connections)} connections via browser", flush=True)
    return connections


# ── Phase 2: individual profile ───────────────────────────────────────────────

async def scrape_profile(page: Page, profile_url: str) -> dict:
    data: dict = {
        "current_company": "",
        "current_title": "",
        "months_in_role": None,
        "seniority": "",
        "location": "",
        "institutes": "",
        "degree": "",
        "grad_year": None,
        "total_exp_years": None,
        "mutual_connections": None,
    }

    try:
        await page.goto(profile_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(2)

        # ── Location ──────────────────────────────────────────────────────────
        for sel in [
            ".text-body-small.inline.t-black--light.break-words",
            "[data-field='location_name']",
        ]:
            loc_el = await page.query_selector(sel)
            if loc_el:
                data["location"] = (await loc_el.inner_text()).strip()
                break

        # ── Mutual connections ────────────────────────────────────────────────
        for sel in [
            "a[href*='facetNetwork'] span.t-bold",
            "a[href*='mutual'] span.t-bold",
            "span.t-bold",  # broad fallback — will filter by text
        ]:
            els = await page.query_selector_all(sel)
            for el in els:
                text = (await el.inner_text()).strip()
                if re.search(r"\d", text) and "mutual" in (await el.evaluate("el => el.closest('a')?.href || ''")).lower():
                    nums = re.findall(r"\d+", text)
                    if nums:
                        data["mutual_connections"] = int(nums[0])
                    break
            if data["mutual_connections"] is not None:
                break

        # ── Experience ────────────────────────────────────────────────────────
        exp_section = await page.query_selector("#experience")
        if exp_section:
            exp_items = await exp_section.query_selector_all("li.artdeco-list__item")
            all_start_years: list[int] = []

            if exp_items:
                first = exp_items[0]

                # Title — first aria-hidden span
                for title_sel in [
                    "div.display-flex.align-items-center span[aria-hidden='true']",
                    "span.mr1.t-bold span[aria-hidden='true']",
                    "span[aria-hidden='true']",
                ]:
                    title_el = await first.query_selector(title_sel)
                    if title_el:
                        data["current_title"] = (await title_el.inner_text()).strip()
                        break
                data["seniority"] = derive_seniority(data["current_title"])

                # Company
                for co_sel in [
                    "span.t-14.t-normal span[aria-hidden='true']",
                    "span.t-14.t-black.t-normal span[aria-hidden='true']",
                ]:
                    co_el = await first.query_selector(co_sel)
                    if co_el:
                        co_text = (await co_el.inner_text()).strip()
                        # strip "· Full-time" / "· Contract" suffixes
                        co_text = re.sub(r"\s*·\s*(Full[-\s]?time|Part[-\s]?time|Contract|Freelance|Self-employed).*$", "", co_text, flags=re.IGNORECASE).strip()
                        if co_text:
                            data["current_company"] = co_text
                            break

                # Role start date → months_in_role
                for date_sel in [
                    ".pvs-entity__caption-wrapper span[aria-hidden='true']",
                    "span.t-14.t-black--light.t-normal span[aria-hidden='true']",
                ]:
                    date_el = await first.query_selector(date_sel)
                    if date_el:
                        date_text = (await date_el.inner_text()).strip()
                        start_match = re.match(r"([A-Za-z]+\s+\d{4}|\d{4})", date_text)
                        if start_match:
                            data["months_in_role"] = months_since(start_match.group(1))
                        break

                # Collect all years for total_exp_years
                for item in exp_items:
                    for d_sel in [
                        ".pvs-entity__caption-wrapper span[aria-hidden='true']",
                        "span.t-14.t-black--light.t-normal span[aria-hidden='true']",
                    ]:
                        d_el = await item.query_selector(d_sel)
                        if d_el:
                            d_text = (await d_el.inner_text()).strip()
                            year_matches = re.findall(r"\b(19|20)\d{2}\b", d_text)
                            all_start_years.extend(int(y) for y in year_matches)
                            break

            if all_start_years:
                data["total_exp_years"] = datetime.now().year - min(all_start_years)

        # ── Education ─────────────────────────────────────────────────────────
        edu_section = await page.query_selector("#education")
        if edu_section:
            edu_items = await edu_section.query_selector_all("li.artdeco-list__item")
            institutes: list[str] = []
            grad_years: list[int] = []

            for edu in edu_items:
                # Institute name (first aria-hidden span in item)
                inst_el = await edu.query_selector("span[aria-hidden='true']")
                if inst_el:
                    inst = (await inst_el.inner_text()).strip()
                    if inst:
                        institutes.append(inst)

                # Degree (second span — "B.Tech · Computer Science")
                deg_els = await edu.query_selector_all("span.t-14.t-normal span[aria-hidden='true']")
                if deg_els and not data["degree"]:
                    data["degree"] = (await deg_els[0].inner_text()).strip()

                # Grad year
                date_el = await edu.query_selector(".pvs-entity__caption-wrapper span[aria-hidden='true']")
                if date_el:
                    d_text = (await date_el.inner_text()).strip()
                    year_matches = re.findall(r"\b(19|20)\d{2}\b", d_text)
                    grad_years.extend(int(y) for y in year_matches)

            data["institutes"] = "; ".join(institutes)
            if grad_years:
                data["grad_year"] = max(grad_years)

    except Exception as e:
        print(f"  ⚠ Error on {profile_url}: {e}", flush=True)

    return data


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    use_export = EXPORT_CSV_PATH.exists()

    if not use_export and not COOKIES_PATH.exists():
        print("ERROR: Neither Connections.csv nor LinkedIn cookies found.", flush=True)
        write_progress(0, 0, "error", "Need either Connections.csv or LinkedIn cookies")
        sys.exit(1)

    # Phase 1 ── two paths depending on what's available
    connections: list[dict] = []

    if use_export:
        # Fast path: official export CSV (no browser)
        try:
            connections = load_connections_from_export()
        except Exception as e:
            print(f"ERROR reading export CSV: {e}", flush=True)
            write_progress(0, 0, "error", str(e))
            sys.exit(1)
    else:
        # Fallback: headful browser (visible Chrome window — bypasses bot detection)
        print("Connections.csv not found — falling back to browser-based scraping.", flush=True)
        print("A Chrome window will open. Do not close it.", flush=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)   # visible = no bot detection
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            await load_cookies(context)
            page = await context.new_page()
            try:
                connections = await scrape_connections_headful(page)
            except RuntimeError as e:
                print(f"ERROR: {e}", flush=True)
                write_progress(0, 0, "error", str(e))
                await browser.close()
                sys.exit(1)
            await browser.close()

    if not connections:
        print("ERROR: No connections found.", flush=True)
        write_progress(0, 0, "error", "No connections found")
        sys.exit(1)

    # Load already-enriched fresh profiles (skip re-scraping)
    existing: dict[str, dict] = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                scraped_at = row.get("scraped_at", "")
                if scraped_at:
                    try:
                        age_days = (datetime.now() - datetime.fromisoformat(scraped_at)).days
                        if age_days <= STALE_DAYS:
                            existing[row["profile_url"]] = row
                    except ValueError:
                        pass

    to_scrape = [c for c in connections if c["profile_url"] not in existing]
    cached = [c for c in connections if c["profile_url"] in existing]
    print(f"Phase 2: {len(to_scrape)} profiles to enrich, {len(cached)} already cached", flush=True)

    all_rows: list[dict] = [existing[c["profile_url"]] for c in cached]
    done = len(cached)
    total = len(connections)

    if not to_scrape:
        write_progress(total, total, "done", "All profiles up to date")
        print("All profiles already cached. Done.", flush=True)
        return

    # Phase 2: profile enrichment — headless is fine for individual profiles
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        await load_cookies(context)
        page = await context.new_page()

        for conn in to_scrape:
            write_progress(done, total, "phase2", conn["name"])
            print(f"  [{done+1}/{total}] {conn['name']}", flush=True)

            profile_data = await scrape_profile(page, conn["profile_url"])
            row = {**conn, **profile_data, "scraped_at": datetime.now().isoformat()}
            all_rows.append(row)
            done += 1

            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_rows)

            await asyncio.sleep(DELAY_BETWEEN_PROFILES)

        await browser.close()

    write_progress(total, total, "done", "Complete")
    print(f"\nDone! {total} connections saved to {CSV_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
