"""
Central config — load .env once, expose typed constants everywhere.
Import: from config import cfg
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"


# ── DB-backed preferences ─────────────────────────────────────────────────────
# dashboard.py edited .env in place. That has no equivalent on a Vercel-hosted
# board, and wouldn't reach a GitHub Actions run even if it did — so preferences
# live in a `settings` table the board writes and this module reads.
#
# Precedence is deliberate and split:
#   preferences (roles, geos, thresholds, toggles) → DB first, then env
#   secrets and infrastructure (API keys, DATABASE_URL) → env only
#
# A key pasted into a web form would look saved and never be used by the
# scheduled run, so the board doesn't offer to store one.
_SETTINGS_CACHE: dict = {}


def _load_settings() -> dict:
    """
    Read the settings table once, at import.

    Never raises: a database that's unreachable or predates the table falls back
    to environment variables, because a pipeline that runs with default targets
    is better than one that won't start.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        return {}
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=10) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {k: v for k, v in rows if v not in (None, "")}
    except Exception as exc:  # noqa: BLE001 — any failure means "use the env"
        logging.getLogger(__name__).info(
            "Settings table unavailable (%s); using environment defaults.", exc
        )
        return {}


def _pref(key: str, default: str = "") -> str:
    """A preference: the board's stored value wins, then env, then the default."""
    return _SETTINGS_CACHE.get(key) or os.getenv(key, default)


def _pref_bool(key: str, default: bool) -> bool:
    return _pref(key, str(default).lower()).strip().lower() == "true"


def _pref_list(key: str, default: str = "") -> List[str]:
    return [item.strip() for item in _pref(key, default).split(",") if item.strip()]


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required env var '{key}' is not set. Check your .env file.")
    return value


def _csv_list(key: str, default: str = "") -> List[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Config:
    # LLM
    anthropic_api_key: str = field(default_factory=lambda: _require("ANTHROPIC_API_KEY"))
    llm_model: str = field(default_factory=lambda: _pref("LLM_MODEL", "claude-haiku-4-5"))

    # Email (optional — only needed for email alerts)
    resend_api_key: str = field(default_factory=lambda: os.getenv("RESEND_API_KEY", ""))
    resend_from_email: str = field(default_factory=lambda: os.getenv("RESEND_FROM_EMAIL", ""))
    alert_to_email: str = field(default_factory=lambda: os.getenv("ALERT_TO_EMAIL", ""))

    # Enrichment
    crunchbase_api_key: str = field(default_factory=lambda: os.getenv("CRUNCHBASE_API_KEY", ""))

    # Google Sheets
    google_sheets_id: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEETS_ID", ""))
    google_service_account_json: Path = field(
        default_factory=lambda: Path(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "data/google_credentials.json")
        )
    )

    # LinkedIn
    linkedin_email: str = field(default_factory=lambda: os.getenv("LINKEDIN_EMAIL", ""))
    linkedin_password: str = field(default_factory=lambda: os.getenv("LINKEDIN_PASSWORD", ""))

    # Scraper toggles
    enable_iimjobs: bool = field(
        default_factory=lambda: _pref_bool("ENABLE_IIMJOBS", True)
    )
    enable_linkedin: bool = field(
        default_factory=lambda: _pref_bool("ENABLE_LINKEDIN", False)
    )
    enable_google_jobs: bool = field(
        default_factory=lambda: _pref_bool("ENABLE_GOOGLE_JOBS", False)
    )
    enable_mycareersfuture: bool = field(
        default_factory=lambda: _pref_bool("ENABLE_MYCAREERSFUTURE", True)
    )

    # Scraper settings
    max_jobs_per_query: int = field(
        default_factory=lambda: int(_pref("MAX_JOBS_PER_QUERY", "30"))
    )
    days_since_posted: int = field(
        default_factory=lambda: int(_pref("DAYS_SINCE_POSTED", "14"))
    )

    # Search preferences
    target_roles: List[str] = field(
        default_factory=lambda: _pref_list("TARGET_ROLES", "Product Manager,AI Product Manager")
    )
    target_locations: List[str] = field(
        default_factory=lambda: _pref_list("TARGET_LOCATIONS", "Singapore,Dubai,London,Dublin,Remote")
    )
    # Target geographies as ISO-3166 alpha-2, highest priority first.
    # Mirrors web/src/lib/geo.ts — see SOURCES.md for which portals cover which.
    target_geos: List[str] = field(
        default_factory=lambda: [g.upper() for g in _pref_list("TARGET_GEOS", "AE,SG,GB,IE,TH,MY,VN")]
    )
    relevance_threshold: float = field(
        default_factory=lambda: float(_pref("RELEVANCE_SCORE_THRESHOLD", "7.0"))
    )

    # Email alert settings
    max_jobs_in_email: int = field(
        default_factory=lambda: int(_pref("MAX_JOBS_IN_EMAIL", "10"))
    )

    # Storage — Neon Postgres, shared with the web board.
    # Required: there is no local fallback, because a pipeline writing to a
    # different store than the board reads is worse than one that refuses to run.
    database_url: str = field(default_factory=lambda: _require("DATABASE_URL"))


_SETTINGS_CACHE = _load_settings()
cfg = Config()
