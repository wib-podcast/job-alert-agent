"""
Build and send the daily email digest via Resend.

Sends an HTML email with top-scoring jobs that haven't been alerted yet.
Returns the list of job IDs that were included, so the caller can mark them alerted.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import resend

from config import cfg
from models import JobCard

logger = logging.getLogger(__name__)

_SOURCE_LABELS = {
    "iimjobs": "IIMJobs",
    "linkedin": "LinkedIn",
    "google_jobs": "Google Jobs",
    "instahyre": "Instahyre",
}

_SOURCE_ICONS = {
    "iimjobs": "🏛",
    "linkedin": "💼",
    "google_jobs": "🔍",
    "instahyre": "⚡",
}

_ROLE_BADGE_COLORS = {
    "IC":       ("#b45309", "#fcd34d"),
    "Manager":  ("#065f46", "#6ee7b7"),
    "Director": ("#1e3a5f", "#93c5fd"),
    "VP":       ("#4c1d95", "#c4b5fd"),
}


def _role_badge(role_type: str | None) -> str:
    bg, fg = _ROLE_BADGE_COLORS.get(role_type or "IC", ("#374151", "#d1d5db"))
    label = role_type or "IC"
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 9px;border-radius:20px;'
        f'font-size:11px;font-weight:600;letter-spacing:0.5px">{label}</span>'
    )


def _score_bar(score: float) -> str:
    """Colour-coded score badge."""
    if score >= 9:
        bg, label = "#065f46", "🔥 PERFECT FIT"
    elif score >= 8:
        bg, label = "#b45309", "⭐ GREAT FIT"
    elif score >= 7:
        bg, label = "#1e3a5f", "✓ GOOD FIT"
    else:
        bg, label = "#374151", "~ OK"
    return (
        f'<div style="text-align:center;background:{bg};border-radius:8px;'
        f'padding:6px 4px;margin-bottom:8px">'
        f'<div style="font-size:22px;font-weight:800;color:#f59e0b;line-height:1">{score:.1f}</div>'
        f'<div style="font-size:9px;color:#fcd34d;letter-spacing:1px;margin-top:2px">{label}</div>'
        f'</div>'
    )


def _skills_html(skills: list[str]) -> str:
    if not skills:
        return ""
    pills = "".join(
        f'<span style="display:inline-block;background:#1f2937;color:#d1d5db;'
        f'border:1px solid #374151;border-radius:4px;padding:2px 8px;'
        f'margin:2px;font-size:11px">{s}</span>'
        for s in skills[:6]
    )
    return f'<div style="margin-top:8px">{pills}</div>'


def _job_card_html(job: JobCard, rank: int) -> str:
    source_label = _SOURCE_LABELS.get(job.source, job.source.capitalize())
    source_icon  = _SOURCE_ICONS.get(job.source, "📌")
    posted = job.posted_date.strftime("%-d %b") if job.posted_date else ""

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;border-collapse:collapse">
  <tr>
    <td style="background:#1a1d24;border:1px solid rgba(245,158,11,0.2);border-radius:10px;padding:0;overflow:hidden">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <!-- Score column -->
          <td width="72" valign="top" style="padding:14px 10px 14px 14px">
            {_score_bar(job.relevance_score)}
            <div style="text-align:center;font-size:11px;color:#6b7280">#{rank}</div>
          </td>
          <!-- Main content -->
          <td valign="top" style="padding:14px 14px 14px 6px">
            <div style="margin-bottom:4px">
              <span style="font-size:15px;font-weight:700;color:#f3f4f6">{job.title}</span>
              &nbsp;{_role_badge(job.role_type)}
            </div>
            <div style="font-size:13px;color:#9ca3af;margin-bottom:2px">
              🏢 <strong style="color:#d1d5db">{job.company}</strong>
              &nbsp;·&nbsp; 📍 {job.location}
              {f'&nbsp;·&nbsp; 🕐 {posted}' if posted else ''}
            </div>
            <div style="font-size:12px;color:#6b7280;margin-bottom:6px">
              {source_icon} {source_label}
            </div>
            {_skills_html(job.must_have_skills or [])}
            <div style="margin-top:10px">
              <a href="{job.job_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#b45309,#d97706);
                        color:#fff;padding:7px 18px;border-radius:6px;
                        text-decoration:none;font-size:12px;font-weight:600">
                View Job →
              </a>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""


def _build_html(jobs: List[JobCard]) -> str:
    cards = "".join(_job_card_html(j, i + 1) for i, j in enumerate(jobs))
    count = len(jobs)
    now   = datetime.now().strftime("%d %b %Y, %I:%M %p")
    perfect = sum(1 for j in jobs if j.relevance_score >= 9)
    great   = sum(1 for j in jobs if 8 <= j.relevance_score < 9)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Job Alert Digest</title>
</head>
<body style="margin:0;padding:0;background:#0d0f14;font-family:Arial,Helvetica,sans-serif">

<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" style="padding:24px 16px">

      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;border-radius:12px;overflow:hidden;
                    border:1px solid rgba(245,158,11,0.2)">

        <!-- ── HEADER ── -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d0f14 0%,#1a1208 100%);
                     padding:28px 28px 20px;border-bottom:2px solid #f59e0b">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="font-size:11px;color:#f59e0b;letter-spacing:2px;
                               font-weight:600;margin-bottom:4px">JOB ALERT AGENT</div>
                  <div style="font-size:22px;font-weight:800;color:#f3f4f6;line-height:1.2">
                    ⚡ {count} New Role{'' if count == 1 else 's'} Found
                  </div>
                  <div style="font-size:12px;color:#6b7280;margin-top:4px">{now}</div>
                </td>
                <td width="100" align="right">
                  <table cellpadding="0" cellspacing="4">
                    <tr>
                      <td style="background:#065f46;border-radius:6px;
                                  padding:4px 10px;text-align:center">
                        <div style="font-size:16px;font-weight:800;color:#6ee7b7">{perfect}</div>
                        <div style="font-size:9px;color:#34d399;letter-spacing:1px">PERFECT</div>
                      </td>
                      <td style="background:#b45309;border-radius:6px;
                                  padding:4px 10px;text-align:center">
                        <div style="font-size:16px;font-weight:800;color:#fcd34d">{great}</div>
                        <div style="font-size:9px;color:#fbbf24;letter-spacing:1px">GREAT</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- Quote -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px">
              <tr>
                <td style="border-left:3px solid #f59e0b;padding:8px 12px;
                            background:rgba(245,158,11,0.06);border-radius:0 6px 6px 0">
                  <div style="font-size:12px;color:#d97706;font-style:italic">
                    "I have no fear of death. It means I can fight without holding back."
                  </div>
                  <div style="font-size:11px;color:#92400e;margin-top:3px">— Yoriichi Tsugikuni</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── JOBS ── -->
        <tr>
          <td style="background:#111318;padding:20px 20px 8px">
            {cards}
          </td>
        </tr>

        <!-- ── FOOTER ── -->
        <tr>
          <td style="background:#0d0f14;border-top:1px solid rgba(245,158,11,0.15);
                     padding:16px 24px;text-align:center">
            <div style="font-size:11px;color:#4b5563;letter-spacing:0.5px">
              Job Alert Agent · Sorted by relevance score · Only scores ≥ {cfg.relevance_threshold:.0f} shown
            </div>
            <div style="font-size:10px;color:#374151;margin-top:4px">
              Power comes in response to a need, not a desire. — Goku
            </div>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>
"""


async def send_digest(jobs: List[JobCard]) -> List[str]:
    """
    Send email digest for the given jobs.
    Returns list of job IDs included in the email (to be marked as alerted).
    """
    if not jobs:
        logger.info("No jobs to send in digest")
        return []

    if not cfg.resend_api_key or not cfg.alert_to_email:
        logger.error("Resend not configured — set RESEND_API_KEY and ALERT_TO_EMAIL in .env")
        return []

    resend.api_key = cfg.resend_api_key

    html_body = _build_html(jobs)
    count = len(jobs)
    subject = f"⚡ {count} PM Job{'s' if count != 1 else ''} · Job Alert Digest"

    try:
        params = {
            "from": cfg.resend_from_email,
            "to": [cfg.alert_to_email],
            "subject": subject,
            "html": html_body,
        }
        response = resend.Emails.send(params)
        logger.info(f"Email sent: {response}")
        return [j.id for j in jobs]
    except Exception as exc:
        logger.error(f"Failed to send email digest: {exc}")
        return []
