"""
Entry point for the job alert agent.
Run manually:  python main.py
Run via cron:  see .github/workflows/job_alert.yml
"""
from __future__ import annotations

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from config import cfg
from db import init_db, save_job, update_job, get_unalerted, mark_alerted
from intelligence.relevance_scorer import score_relevance_batch


async def run() -> None:
    logger.info("Job alert agent starting…")

    # 1. Ensure DB exists
    init_db(cfg.database_url)

    # 2. Scrape from all enabled sources
    all_jobs = []

    if cfg.enable_iimjobs:
        from scrapers.iimjobs import IIMJobsScraper
        logger.info("Scraping IIMJobs…")
        scraper = IIMJobsScraper(
            max_jobs_per_query=cfg.max_jobs_per_query,
            days_since_posted=cfg.days_since_posted,
        )
        jobs = await scraper.scrape(cfg.target_roles, cfg.target_locations, dsn=cfg.database_url)
        logger.info(f"IIMJobs: {len(jobs)} jobs scraped")
        all_jobs.extend(jobs)

    if cfg.enable_linkedin:
        from scrapers.linkedin import LinkedInScraper
        logger.info("Scraping LinkedIn…")
        scraper = LinkedInScraper(
            max_jobs_per_query=cfg.max_jobs_per_query,
            days_since_posted=cfg.days_since_posted,
        )
        jobs = await scraper.scrape(cfg.target_roles, cfg.target_locations, dsn=cfg.database_url)
        logger.info(f"LinkedIn: {len(jobs)} jobs scraped")
        all_jobs.extend(jobs)

    if cfg.enable_mycareersfuture:
        from scrapers.mycareersfuture import MyCareersFutureScraper
        logger.info("Scraping MyCareersFuture (Singapore)…")
        scraper = MyCareersFutureScraper(
            max_jobs_per_query=cfg.max_jobs_per_query,
            days_since_posted=cfg.days_since_posted,
        )
        jobs = await scraper.scrape(cfg.target_roles, cfg.target_locations, dsn=cfg.database_url)
        logger.info(f"MyCareersFuture: {len(jobs)} jobs scraped")
        all_jobs.extend(jobs)

    if cfg.enable_google_jobs:
        from scrapers.google_jobs import GoogleJobsScraper
        logger.info("Scraping Google Jobs…")
        scraper = GoogleJobsScraper(
            max_jobs_per_query=cfg.max_jobs_per_query,
            days_since_posted=cfg.days_since_posted,
        )
        jobs = await scraper.scrape(cfg.target_roles, cfg.target_locations, dsn=cfg.database_url)
        logger.info(f"Google Jobs: {len(jobs)} jobs scraped")
        all_jobs.extend(jobs)

    if not any(
        [cfg.enable_iimjobs, cfg.enable_linkedin, cfg.enable_google_jobs, cfg.enable_mycareersfuture]
    ):
        logger.warning(
            "No scrapers enabled. Set one of ENABLE_IIMJOBS / ENABLE_LINKEDIN / "
            "ENABLE_MYCAREERSFUTURE / ENABLE_GOOGLE_JOBS in .env"
        )
        return

    logger.info(f"Total scraped: {len(all_jobs)} jobs across all sources")

    # 3. Deduplicate — only pass truly new jobs to scorer
    new_jobs = []
    for job in all_jobs:
        if save_job(cfg.database_url, job):
            new_jobs.append(job)
    logger.info(f"{len(new_jobs)} new jobs (not seen before)")

    if not new_jobs:
        logger.info("No new jobs to score — checking for pending email alerts…")

    if new_jobs:
        # 4. Score new jobs in batches (much cheaper + faster than one-at-a-time)
        scored = await score_relevance_batch(new_jobs)
        for job in scored:
            update_job(cfg.database_url, job)

        # 5. Report
        above_threshold = [j for j in scored if j.relevance_score >= cfg.relevance_threshold]
        logger.info(
            f"Scoring complete — {len(above_threshold)}/{len(scored)} jobs "
            f"above threshold ({cfg.relevance_threshold})"
        )
        for job in above_threshold:
            logger.info(
                f"  [{job.relevance_score:.1f}] {job.title} @ {job.company} "
                f"({job.location}) — {job.job_url}"
            )

    # 6. Send email digest (if Resend configured)
    if cfg.resend_api_key and cfg.resend_api_key != "re_...":
        unalerted = get_unalerted(cfg.database_url, min_score=cfg.relevance_threshold)
        if unalerted:
            logger.info(f"Sending email digest for {len(unalerted)} unalerted jobs…")
            from outputs.email_digest import send_digest
            sent_ids = await send_digest(unalerted[: cfg.max_jobs_in_email])
            if sent_ids:
                mark_alerted(cfg.database_url, sent_ids)
                logger.info(f"Email sent — marked {len(sent_ids)} jobs as alerted")
        else:
            logger.info("No unalerted jobs above threshold — skipping email")
    else:
        logger.info("Resend not configured — skipping email alert")

    logger.info("Done.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
