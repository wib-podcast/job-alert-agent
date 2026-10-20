"""
Job Alert Agent — local dashboard.
Run: streamlit run dashboard.py
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"
DB_PATH = ROOT / "data" / "jobs.db"
COOKIES_PATH = ROOT / "data" / "linkedin_cookies.json"
IMAGES_DIR = ROOT / "data" / "images"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Alert Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ══ GLOBAL RESET ══ */
* { box-sizing: border-box; }

/* ══ BACKGROUND ══ */
[data-testid="stAppViewContainer"] {
    background-color: #111318;
    background-image: radial-gradient(ellipse at 20% 0%, rgba(245,158,11,0.06) 0%, transparent 50%),
                      radial-gradient(ellipse at 80% 100%, rgba(16,185,129,0.04) 0%, transparent 50%);
}
[data-testid="stSidebar"] {
    background-color: #0d0f14;
    border-right: 1px solid rgba(245,158,11,0.12);
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none; }

/* ══ GLOBAL TEXT ══ */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
label, .stMarkdown { color: #e5e7eb !important; }

/* ══ SIDEBAR TEXT ══ */
[data-testid="stSidebar"] * { color: #d1d5db !important; }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: #1a1d24;
    border-radius: 10px;
    padding: 4px 6px;
    border: 1px solid rgba(245,158,11,0.15);
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 13px;
    font-weight: 600;
    color: #9ca3af !important;
    border-radius: 7px;
    padding: 7px 14px;
    background: transparent;
    transition: all 0.15s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #b45309, #d97706) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(217,119,6,0.35);
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ══ METRICS ══ */
[data-testid="metric-container"] {
    background: #1a1d24;
    border: 1px solid rgba(245,158,11,0.18);
    border-radius: 10px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] { color: #f59e0b !important; font-size: 1.8rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #9ca3af !important; font-size: 0.8rem !important; }

/* ══ BUTTONS ══ */
button[kind="primary"], .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #b45309 0%, #d97706 100%) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 14px rgba(217,119,6,0.3) !important;
    transition: all 0.15s !important;
}
button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 20px rgba(217,119,6,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]) {
    background: #1e2130 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #d1d5db !important;
}

/* ══ INPUTS ══ */
input, textarea, [data-baseweb="textarea"] textarea {
    background-color: #1e2130 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 7px !important;
    color: #f3f4f6 !important;
    caret-color: #f59e0b !important;
}
input:focus, textarea:focus {
    border-color: #d97706 !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(217,119,6,0.15) !important;
}
[data-baseweb="input"] { background: #1e2130 !important; border-radius: 7px !important; }
[data-baseweb="input"] input { border: none !important; }

/* ══ SELECT / DROPDOWNS ══ */
[data-baseweb="select"] > div:first-child {
    background: #1e2130 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 7px !important;
    color: #f3f4f6 !important;
}
[data-baseweb="popover"] { background: #1e2130 !important; }
[data-baseweb="menu"] { background: #1e2130 !important; border: 1px solid rgba(255,255,255,0.08) !important; }
[role="option"] { color: #e5e7eb !important; }
[role="option"]:hover { background: rgba(245,158,11,0.12) !important; }

/* ══ MULTISELECT TAGS — replace red with gold ══ */
[data-baseweb="tag"] {
    background-color: rgba(180,83,9,0.35) !important;
    border: 1px solid rgba(245,158,11,0.4) !important;
    border-radius: 5px !important;
}
[data-baseweb="tag"] span { color: #fcd34d !important; }
[data-baseweb="tag"] svg { color: #f59e0b !important; fill: #f59e0b !important; }

/* ══ SLIDER ══ */
[data-testid="stSlider"] [role="slider"] {
    background: #d97706 !important;
    border: 2px solid #f59e0b !important;
}
[data-testid="stSlider"] [data-testid="stTickBar"] { color: #6b7280 !important; }
[data-testid="stSlider"] .rc-slider-track { background: #d97706 !important; }

/* ══ EXPANDER (job cards) ══ */
details > summary {
    background: #1a1d24 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 9px !important;
    color: #e5e7eb !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
    transition: border-color 0.15s !important;
    list-style: none !important;
}
details > summary:hover { border-color: rgba(245,158,11,0.35) !important; }
details[open] > summary { border-radius: 9px 9px 0 0 !important; border-color: rgba(245,158,11,0.3) !important; }
details > div {
    background: #151820 !important;
    border: 1px solid rgba(245,158,11,0.15) !important;
    border-top: none !important;
    border-radius: 0 0 9px 9px !important;
    padding: 12px 16px !important;
}

/* ══ CHECKBOXES ══ */
[data-testid="stCheckbox"] label { color: #d1d5db !important; }
[data-testid="stCheckbox"] [data-checked="true"] { background: #d97706 !important; border-color: #d97706 !important; }

/* ══ DIVIDER ══ */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 16px 0 !important; }

/* ══ ALERTS ══ */
[data-testid="stAlert"] { border-radius: 8px !important; border-width: 1px !important; }
[data-testid="stAlert"][data-baseweb="notification"] { background: #1a1d24 !important; }

/* ══ CODE BLOCKS ══ */
[data-testid="stCode"], .stCodeBlock pre {
    background: #0d0f14 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    color: #a3e635 !important;
}

/* ══ CUSTOM COMPONENTS ══ */
.glow-title {
    font-size: 1.9rem;
    font-weight: 900;
    background: linear-gradient(90deg, #f59e0b, #fbbf24, #fde68a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.5px;
}
.glow-subtitle {
    color: #6b7280 !important;
    font-size: 0.82rem;
    margin-top: 3px;
}
.character-quote {
    background: linear-gradient(90deg, rgba(180,83,9,0.15), rgba(180,83,9,0.05));
    border-left: 3px solid #d97706;
    border-radius: 0 8px 8px 0;
    padding: 10px 16px;
    margin: 10px 0 16px 0;
    font-style: italic;
    color: #d1d5db !important;
    font-size: 0.87rem;
    line-height: 1.5;
}
.score-badge-green {
    background: #065f46;
    color: #6ee7b7;
    border: 1px solid #10b981;
    padding: 1px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}
.score-badge-blue {
    background: #1e3a5f;
    color: #93c5fd;
    border: 1px solid #3b82f6;
    padding: 1px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}
.score-badge-gray {
    background: #1f2937;
    color: #9ca3af;
    border: 1px solid #374151;
    padding: 1px 9px;
    border-radius: 20px;
    font-size: 11px;
}
.char-frame {
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid rgba(245,158,11,0.3);
    box-shadow: 0 0 20px rgba(245,158,11,0.1);
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def read_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def write_env(updates: dict):
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(out) + "\n")


def get_conn():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'new'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    return conn


def load_jobs(conn, filters: dict) -> pd.DataFrame:
    if conn is None:
        return pd.DataFrame()
    q = "SELECT id, title, company, location, source, relevance_score, role_type, posted_date, scraped_at, job_url, must_have_skills, status, alerted FROM jobs WHERE 1=1"
    params = []
    if filters.get("min_score") is not None:
        q += " AND relevance_score >= ?"
        params.append(filters["min_score"])
    if filters.get("max_score") is not None:
        q += " AND relevance_score <= ?"
        params.append(filters["max_score"])
    if filters.get("sources"):
        placeholders = ",".join("?" * len(filters["sources"]))
        q += f" AND source IN ({placeholders})"
        params.extend(filters["sources"])
    if filters.get("role_types"):
        placeholders = ",".join("?" * len(filters["role_types"]))
        q += f" AND role_type IN ({placeholders})"
        params.extend(filters["role_types"])
    if filters.get("statuses"):
        placeholders = ",".join("?" * len(filters["statuses"]))
        q += f" AND (status IN ({placeholders}) OR (status IS NULL AND 'new' IN ({placeholders})))"
        params.extend(filters["statuses"] * 2)
    if filters.get("search"):
        q += " AND (title LIKE ? OR company LIKE ?)"
        term = f"%{filters['search']}%"
        params.extend([term, term])
    q += " ORDER BY relevance_score DESC, scraped_at DESC"
    df = pd.read_sql_query(q, conn, params=params)
    df["status"] = df["status"].fillna("new")
    return df


def score_color(score: float) -> str:
    if score >= 8:
        return "🟢"
    if score >= 6:
        return "🟡"
    return "🔴"


def score_badge_html(score: float) -> str:
    if score >= 8:
        cls = "score-badge-green"
    elif score >= 6:
        cls = "score-badge-blue"
    else:
        cls = "score-badge-gray"
    return f'<span class="{cls}">{score:.1f}</span>'


def update_status(conn, job_id: str, status: str):
    conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()


def show_character(image_name: str, fallback_emoji: str, width: int = 220):
    """Show a character image from data/images/ or a fallback emoji."""
    path = IMAGES_DIR / image_name
    if path.exists():
        st.image(str(path), width=width)
    else:
        st.markdown(
            f'<div style="font-size:5rem;text-align:center;filter:drop-shadow(0 0 20px rgba(150,100,255,0.8))">{fallback_emoji}</div>',
            unsafe_allow_html=True,
        )


def img_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Goku image or fallback
    goku_path = IMAGES_DIR / "goku.png"
    if goku_path.exists():
        st.image(str(goku_path), use_container_width=True)
    else:
        st.markdown(
            '<div style="text-align:center;font-size:4rem;filter:drop-shadow(0 0 30px gold)">⚡</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="glow-title">Job Alert<br>Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="glow-subtitle">Your personal PM job radar</p>', unsafe_allow_html=True)
    st.divider()

    conn = get_conn()
    if conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        new_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new' OR status IS NULL").fetchone()[0]
        high_fit = conn.execute("SELECT COUNT(*) FROM jobs WHERE relevance_score >= 8").fetchone()[0]
        col_a, col_b = st.columns(2)
        col_a.metric("Total", total)
        col_b.metric("New", new_count)
        st.metric("High-fit (≥8)", high_fit)
    else:
        st.info("No DB yet — run the agent first.")

    st.divider()
    st.markdown(
        '<div class="character-quote">"Power comes in response to a need, not a desire." — Goku</div>',
        unsafe_allow_html=True,
    )
    st.caption("v1.0 · IIMJobs + LinkedIn + Google Jobs")
    st.caption("💡 Drop images in `data/images/` to customise characters")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["⚙️ Preferences", "📋 Job Board", "📧 Alerts & Email", "▶️ Run Agent", "🔗 LinkedIn Setup", "👥 Connections & Referrals"])
tab_prefs, tab_jobs, tab_alerts, tab_run, tab_linkedin, tab_connections = tabs


# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ PREFERENCES  —  Levi Ackerman (precision, no wasted moves)
# ══════════════════════════════════════════════════════════════════════════════
with tab_prefs:
    env = read_env()

    # Header with character
    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">Search Preferences</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"The only time a soldier should doubt their decision is before they make it." — Levi Ackerman</div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("levi.png", "⚔️", width=160)

    st.markdown("These settings control **what jobs get scraped and scored** on every run.")
    st.divider()

    col1, col2 = st.columns([3, 2])

    with col1:
        roles_raw = env.get("TARGET_ROLES", "Product Manager,Senior PM,Associate PM,Growth Manager,Strategy Manager,AI Solutioning,AI Strategy Manager")
        roles_input = st.text_area(
            "🎯 Target Roles",
            value="\n".join(r.strip() for r in roles_raw.split(",") if r.strip()),
            height=200,
            help="One role per line. Sent as search queries to each job board.",
        )

        locations_raw = env.get("TARGET_LOCATIONS", "Bangalore,Hyderabad,Gurgaon,Mumbai,Pune")
        locations_input = st.text_area(
            "📍 Target Locations",
            value="\n".join(l.strip() for l in locations_raw.split(",") if l.strip()),
            height=140,
            help="One location per line.",
        )

        threshold = st.slider(
            "🏆 Relevance Threshold (email alert above this score)",
            min_value=0.0, max_value=10.0,
            value=float(env.get("RELEVANCE_SCORE_THRESHOLD", "7.0")),
            step=0.5,
        )

    with col2:
        st.markdown("#### 📡 Sources")
        enable_iimjobs = st.checkbox("IIMJobs", value=env.get("ENABLE_IIMJOBS", "true") == "true")
        enable_linkedin = st.checkbox(
            "LinkedIn Jobs",
            value=env.get("ENABLE_LINKEDIN", "false") == "true",
            help="Requires LinkedIn session cookies. See 'LinkedIn Setup' tab.",
        )
        enable_google = st.checkbox(
            "Google Jobs",
            value=env.get("ENABLE_GOOGLE_JOBS", "false") == "true",
        )

        st.markdown("#### 🔧 Scraper Settings")
        max_jobs = st.slider("Max jobs per query", 5, 50, int(env.get("MAX_JOBS_PER_QUERY", "30")))
        days_posted = st.select_slider(
            "Jobs posted within",
            options=[1, 3, 7, 14, 30],
            value=int(env.get("DAYS_SINCE_POSTED", "14")),
            format_func=lambda x: f"Last {x} days",
        )

        st.markdown("#### 🤖 LLM Model")
        model_opts = ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-6"]
        model_choice = st.selectbox(
            "Scoring model",
            options=model_opts,
            index=model_opts.index(env.get("LLM_MODEL", "claude-haiku-4-5")),
            help="Haiku ≈ $0.05/run · Sonnet ≈ $0.30/run",
        )

    st.divider()
    c_save, c_info = st.columns([1, 3])
    with c_save:
        if st.button("💾 Save Preferences", type="primary", use_container_width=True):
            roles_csv = ",".join(r.strip() for r in roles_input.splitlines() if r.strip())
            locs_csv = ",".join(l.strip() for l in locations_input.splitlines() if l.strip())
            write_env({
                "TARGET_ROLES": roles_csv,
                "TARGET_LOCATIONS": locs_csv,
                "RELEVANCE_SCORE_THRESHOLD": str(threshold),
                "ENABLE_IIMJOBS": str(enable_iimjobs).lower(),
                "ENABLE_LINKEDIN": str(enable_linkedin).lower(),
                "ENABLE_GOOGLE_JOBS": str(enable_google).lower(),
                "MAX_JOBS_PER_QUERY": str(max_jobs),
                "DAYS_SINCE_POSTED": str(days_posted),
                "LLM_MODEL": model_choice,
            })
            st.success("✅ Saved! Changes take effect on next run.")
    with c_info:
        roles_count = len([r for r in roles_input.splitlines() if r.strip()])
        locs_count = len([l for l in locations_input.splitlines() if l.strip()])
        sources_count = sum([enable_iimjobs, enable_linkedin, enable_google])
        queries = roles_count * locs_count * sources_count
        cost_per_run = queries * 0.001
        st.info(
            f"{roles_count} roles × {locs_count} locations × {sources_count} sources "
            f"= {queries} queries/run  ·  "
            f"Haiku est. ~${cost_per_run:.2f}/run  ·  ~${cost_per_run * 60:.1f}/month (2×/day)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 📋 JOB BOARD  —  Yoriichi (calm, laser focus)
# ══════════════════════════════════════════════════════════════════════════════
with tab_jobs:
    conn = get_conn()
    if conn is None:
        hcol1, hcol2 = st.columns([3, 1])
        with hcol1:
            st.markdown('<h2 class="glow-title">Job Board</h2>', unsafe_allow_html=True)
            st.info("No jobs yet. Go to **▶️ Run Agent** to scrape your first batch.")
        with hcol2:
            show_character("yoriichi.png", "🌅", width=160)
        st.stop()

    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">Job Board</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"I have no fear of death. It means I can fight without holding back." — Yoriichi Tsugikuni</div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("yoriichi.png", "🌅", width=160)

    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        search_term = st.text_input("🔍 Search title / company", placeholder="e.g. Meesho, Fintech, AI…")
    with fc2:
        score_range = st.slider("Score range", 0.0, 10.0, (5.0, 10.0), 0.5)
    with fc3:
        all_sources = ["iimjobs", "linkedin", "google_jobs"]
        sel_sources = st.multiselect("Source", all_sources, default=all_sources)
    with fc4:
        sel_statuses = st.multiselect(
            "Status", ["new", "saved", "applied", "dismissed"], default=["new", "saved"]
        )

    role_types = st.multiselect(
        "Role type", ["IC", "Manager", "Director", "VP", "Unknown"],
        default=["IC", "Manager", "Unknown"],
    )

    filters = {
        "min_score": score_range[0], "max_score": score_range[1],
        "sources": sel_sources or None, "role_types": role_types or None,
        "statuses": sel_statuses or None, "search": search_term or None,
    }
    df = load_jobs(conn, filters)

    # ── Metrics ───────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Showing", len(df))
    m2.metric("🔥 High-fit (≥8)", len(df[df["relevance_score"] >= 8]))
    m3.metric("✅ Good-fit (≥7)", len(df[df["relevance_score"] >= 7]))
    m4.metric("📬 Alerted", int(df["alerted"].sum()) if "alerted" in df.columns else 0)
    m5.metric("📌 Saved", len(df[df["status"] == "saved"]) if "status" in df.columns else 0)

    st.divider()

    if df.empty:
        st.info("No jobs match your filters.")
    else:
        source_labels = {"iimjobs": "🟣 IIMJobs", "linkedin": "🔵 LinkedIn", "google_jobs": "🔴 Google"}

        for _, row in df.iterrows():
            score = float(row["relevance_score"])
            icon = score_color(score)
            src_label = source_labels.get(row["source"], row["source"])

            with st.expander(
                f"{icon} **{score:.1f}** · {row['title']} @ **{row['company']}** · {row['location'] or '—'} · {src_label}",
                expanded=False,
            ):
                c_left, c_right = st.columns([4, 1])
                with c_left:
                    # Role type + source row
                    rt = row.get("role_type") or "—"
                    st.markdown(
                        f"**Role type:** `{rt}` &nbsp;|&nbsp; **Source:** {src_label}",
                        unsafe_allow_html=True,
                    )
                    # Skills
                    if row.get("must_have_skills"):
                        try:
                            skills = json.loads(row["must_have_skills"]) if isinstance(row["must_have_skills"], str) else row["must_have_skills"]
                            if skills:
                                pills = " ".join(f"`{s}`" for s in skills[:8])
                                st.markdown(f"**Key skills:** {pills}")
                        except Exception:
                            pass
                    scraped = (row.get("scraped_at") or "")[:10] or "—"
                    posted = (row.get("posted_date") or "")[:10] or "—"
                    st.caption(f"📅 Posted: {posted} · Scraped: {scraped}")
                    st.link_button("🔗 Open Job →", row["job_url"])

                with c_right:
                    current_status = row.get("status") or "new"
                    new_status = st.selectbox(
                        "Status",
                        ["new", "saved", "applied", "dismissed"],
                        index=["new", "saved", "applied", "dismissed"].index(current_status),
                        key=f"status_{row['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != current_status:
                        update_status(conn, row["id"], new_status)
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 📧 ALERTS & EMAIL  —  Spike Spiegel (smooth operator)
# ══════════════════════════════════════════════════════════════════════════════
with tab_alerts:
    env = read_env()

    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">Alerts & Email</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"Whatever happens, happens." — Spike Spiegel, Cowboy Bebop</div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("spike.png", "🚀", width=160)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✉️ Email")
        alert_to = st.text_input("Send alerts to", value=env.get("ALERT_TO_EMAIL", ""), placeholder="you@gmail.com")
        resend_from = st.text_input("From address", value=env.get("RESEND_FROM_EMAIL", ""), placeholder="onboarding@resend.dev")
        max_in_email = st.slider("Max jobs per email", 3, 20, int(env.get("MAX_JOBS_IN_EMAIL", "10")))

        st.markdown("#### 🔑 API Keys")
        anthropic_key = st.text_input("Anthropic API Key", value=env.get("ANTHROPIC_API_KEY", ""), type="password", help="console.anthropic.com")
        resend_key = st.text_input("Resend API Key", value=env.get("RESEND_API_KEY", ""), type="password", help="resend.com — 3,000 emails/month free")

    with col2:
        st.markdown("#### 📐 Alert Rules")
        alert_min_score = st.slider(
            "Min score to include in email", 0.0, 10.0,
            float(env.get("RELEVANCE_SCORE_THRESHOLD", "7.0")), 0.5,
        )
        st.selectbox(
            "Alert frequency",
            ["2× daily (8 AM + 6 PM IST)", "Daily (8 AM IST)", "Weekly"],
        )

        st.markdown("#### 📊 Google Sheets (optional)")
        sheets_id = st.text_input(
            "Spreadsheet ID",
            value=env.get("GOOGLE_SHEETS_ID", ""),
            placeholder="Paste the ID from your Sheet URL",
        )
        sa_path = st.text_input(
            "Service account JSON path",
            value=env.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "data/google_credentials.json"),
        )

    st.divider()
    c_save2, c_test = st.columns([1, 1])
    with c_save2:
        if st.button("💾 Save Alert Settings", type="primary", use_container_width=True):
            write_env({
                "ALERT_TO_EMAIL": alert_to,
                "RESEND_FROM_EMAIL": resend_from,
                "RESEND_API_KEY": resend_key,
                "ANTHROPIC_API_KEY": anthropic_key,
                "RELEVANCE_SCORE_THRESHOLD": str(alert_min_score),
                "MAX_JOBS_IN_EMAIL": str(max_in_email),
                "GOOGLE_SHEETS_ID": sheets_id,
                "GOOGLE_SERVICE_ACCOUNT_JSON_PATH": sa_path,
            })
            st.success("✅ Saved!")
    with c_test:
        if st.button("📬 Send Test Email", use_container_width=True):
            if not resend_key or resend_key.startswith("re_..."):
                st.error("Add your Resend API key first.")
            elif not alert_to:
                st.error("Add a destination email first.")
            else:
                import resend as _resend
                try:
                    _resend.api_key = resend_key
                    _resend.Emails.send({
                        "from": resend_from or "onboarding@resend.dev",
                        "to": [alert_to],
                        "subject": "🎯 Job Alert Agent — Test Email",
                        "html": "<h2>It works!</h2><p>Your Job Alert Agent email is set up correctly. Jobs above your score threshold will land here.</p>",
                    })
                    st.success(f"✅ Test email sent to {alert_to}!")
                except Exception as e:
                    st.error(f"Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ▶️ RUN AGENT  —  Goku (power up and go)
# ══════════════════════════════════════════════════════════════════════════════
with tab_run:
    env = read_env()

    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">Run Agent</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"I am the hope of the universe. I am the answer to all living things that cry out for peace." — Goku</div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("goku.png", "⚡", width=160)

    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### 📊 Current Stats")
        conn2 = get_conn()
        if conn2:
            total = conn2.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            scored = conn2.execute("SELECT COUNT(*) FROM jobs WHERE relevance_score > 0").fetchone()[0]
            above = conn2.execute(
                "SELECT COUNT(*) FROM jobs WHERE relevance_score >= ?",
                (float(env.get("RELEVANCE_SCORE_THRESHOLD", "7.0")),)
            ).fetchone()[0]
            last_run = conn2.execute("SELECT MAX(scraped_at) FROM jobs").fetchone()[0]
            st.metric("Total in DB", total)
            st.metric("Scored", scored)
            st.metric(f"Above threshold", above)
            if last_run:
                st.caption(f"🕐 Last run: {last_run[:16]}")
        else:
            st.info("No data yet.")

        st.markdown("#### 📡 Active Sources")
        if env.get("ENABLE_IIMJOBS", "true") == "true":
            st.success("✅ IIMJobs")
        if env.get("ENABLE_LINKEDIN", "false") == "true":
            if COOKIES_PATH.exists():
                st.success("✅ LinkedIn")
            else:
                st.warning("⚠️ LinkedIn (no cookies)")
        if env.get("ENABLE_GOOGLE_JOBS", "false") == "true":
            st.success("✅ Google Jobs")

    with col2:
        st.markdown("#### 🚀 Launch")
        if st.button("▶️ Run Now", type="primary", use_container_width=True):
            with st.status("⚡ Powering up the job agent…", expanded=True) as run_status:
                proc = subprocess.Popen(
                    [sys.executable, str(ROOT / "main.py")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(ROOT),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
                logs = []
                log_box = st.empty()
                for line in proc.stdout:
                    logs.append(line.rstrip())
                    log_box.code("\n".join(logs[-60:]), language="text")
                proc.wait()
                if proc.returncode == 0:
                    run_status.update(label="✅ Done! Check the Job Board.", state="complete")
                else:
                    run_status.update(label="❌ Failed — check logs above", state="error")

        st.markdown("#### 🤖 Automation (GitHub Actions)")
        st.info(
            "Push this repo to GitHub → add secrets → the agent runs automatically "
            "at **8 AM** and **6 PM IST** every day via `.github/workflows/job_alert.yml`."
        )

        roles_count = len([r for r in env.get("TARGET_ROLES", "").split(",") if r.strip()])
        locs_count = len([l for l in env.get("TARGET_LOCATIONS", "").split(",") if l.strip()])
        sources = sum([
            env.get("ENABLE_IIMJOBS", "true") == "true",
            env.get("ENABLE_LINKEDIN", "false") == "true",
            env.get("ENABLE_GOOGLE_JOBS", "false") == "true",
        ])
        queries = roles_count * locs_count * sources
        st.markdown(
            f"**Estimated run:** `{queries} queries` · `~15–20 min` · "
            f"`~${queries * 0.001:.2f}` per run"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 🔗 LINKEDIN SETUP  —  Itachi (the silent strategist)
# ══════════════════════════════════════════════════════════════════════════════
with tab_linkedin:
    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">LinkedIn Setup</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"People live their lives bound by what they accept as correct and true." — Itachi Uchiha</div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("itachi.png", "🔴", width=160)

    st.markdown("LinkedIn requires your **session cookies** to authenticate. 2-minute setup.")
    st.divider()

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("#### Step-by-step")
        st.markdown("**1️⃣** Install **Cookie-Editor** Chrome extension → [Open Chrome Web Store ↗](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)")
        st.markdown("**2️⃣** Go to [linkedin.com](https://www.linkedin.com) and make sure you're **logged in**")
        st.markdown("**3️⃣** Click the **Cookie-Editor icon** (top right) → **Export** → **Export as JSON**")
        st.markdown("**4️⃣** Paste the copied JSON in the box below 👇")
        st.markdown("**5️⃣** Go to **⚙️ Preferences** → tick **LinkedIn Jobs** → Save")

    with s2:
        if COOKIES_PATH.exists():
            try:
                cookies = json.loads(COOKIES_PATH.read_text())
                li_at = next((c for c in cookies if c.get("name") == "li_at"), None)
                st.success(f"✅ Cookies active — {len(cookies)} cookies loaded")
                if li_at:
                    st.success("✅ `li_at` session token present — ready to scrape")
                else:
                    st.error("❌ `li_at` not found — re-export cookies while logged into LinkedIn")
            except Exception:
                st.warning("⚠️ Cookies file exists but couldn't be parsed")
        else:
            st.warning("⚠️ No cookies file yet — paste below to set up")

        st.markdown("#### ⚠️ Important notes")
        st.markdown("""
- Cookies **expire ~30 days** — re-export when scraping stops working
- **Personal use only** — we scrape at human-like pace (max 30 jobs/search)
- If LinkedIn blocks, disable it in Preferences and try again in 24h
        """)

    st.divider()
    cookies_json = st.text_area(
        "Paste LinkedIn cookies JSON here",
        height=180,
        placeholder='[{"name": "li_at", "value": "AQE...", "domain": ".linkedin.com", ...}]',
    )

    c_save_li, _ = st.columns([1, 3])
    with c_save_li:
        if st.button("💾 Save Cookies", type="primary", use_container_width=True):
            try:
                parsed = json.loads(cookies_json)
                if not isinstance(parsed, list):
                    st.error("Expected a JSON array.")
                elif not any(c.get("name") == "li_at" for c in parsed):
                    st.error("Cookie 'li_at' not found. Make sure you're logged in.")
                else:
                    (ROOT / "data").mkdir(exist_ok=True)
                    COOKIES_PATH.write_text(json.dumps(parsed, indent=2))
                    st.success(f"✅ Saved {len(parsed)} cookies!")
                    st.info("Now go to **⚙️ Preferences** → enable **LinkedIn Jobs** → Save.")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 👥 CONNECTIONS & REFERRALS
# ══════════════════════════════════════════════════════════════════════════════
CONNECTIONS_CSV = ROOT / "data" / "connections.csv"
CONNECTIONS_PROGRESS = ROOT / "data" / "connections_progress.json"
LINKEDIN_EXPORT_PATH = ROOT / "data" / "Connections.csv"

with tab_connections:
    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown('<h2 class="glow-title">Connections & Referrals</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="character-quote">"The strength of a team lies in the network behind it." </div>',
            unsafe_allow_html=True,
        )
    with hcol2:
        show_character("itachi.png", "🤝", width=160)

    st.markdown("Find your LinkedIn connections by company & institute to identify who to ask for a referral.")
    st.divider()

    # ── Step 1: LinkedIn Export Setup ─────────────────────────────────────────
    with st.expander("📥 Step 1 — Upload LinkedIn Connections Export (required once)", expanded=not LINKEDIN_EXPORT_PATH.exists()):
        st.markdown("""
**Why:** LinkedIn blocks headless browsers on the connections list page, so we use their official data export instead — it's reliable and takes ~10 minutes.

**How to get it:**
1. Go to [linkedin.com/mypreferences/d/data-privacy](https://www.linkedin.com/mypreferences/d/data-privacy)
2. Click **"Get a copy of your data"**
3. Select **Connections** only (faster — not the full archive)
4. Click **"Request archive"** — LinkedIn emails you within ~10 min
5. Download the zip → unzip → upload `Connections.csv` below
        """)
        uploaded = st.file_uploader("Upload Connections.csv", type="csv", key="li_export_upload")
        if uploaded:
            LINKEDIN_EXPORT_PATH.parent.mkdir(exist_ok=True)
            LINKEDIN_EXPORT_PATH.write_bytes(uploaded.read())
            st.success(f"✅ Saved to {LINKEDIN_EXPORT_PATH}")
            st.rerun()

    if LINKEDIN_EXPORT_PATH.exists():
        try:
            _export_check = pd.read_csv(LINKEDIN_EXPORT_PATH, skiprows=3, on_bad_lines="skip")
            st.success(f"✅ Connections.csv loaded — {len(_export_check)} connections found")
        except Exception:
            st.warning("⚠️ Connections.csv exists but could not be parsed. Try re-uploading.")

    st.divider()

    # ── Run scraper ───────────────────────────────────────────────────────────
    run_col, status_col = st.columns([1, 2])

    with run_col:
        # Show cached stats
        if CONNECTIONS_CSV.exists():
            try:
                _df_check = pd.read_csv(CONNECTIONS_CSV)
                cached_count = len(_df_check)
                last_run = _df_check["scraped_at"].max() if "scraped_at" in _df_check.columns else "unknown"
                if last_run and last_run != "unknown":
                    try:
                        last_run_fmt = datetime.fromisoformat(str(last_run)).strftime("%d %b %Y, %I:%M %p")
                    except Exception:
                        last_run_fmt = str(last_run)
                else:
                    last_run_fmt = "unknown"
                st.metric("Cached connections", cached_count)
                st.caption(f"Last scraped: {last_run_fmt}")
            except Exception:
                pass

        scrape_btn = st.button("🔄 Scrape / Refresh", type="primary", use_container_width=True)
        st.caption("Skips profiles scraped within last 30 days")

    with status_col:
        if CONNECTIONS_PROGRESS.exists():
            try:
                prog = json.loads(CONNECTIONS_PROGRESS.read_text())
                done = prog.get("done", 0)
                total = prog.get("total", 0)
                status = prog.get("status", "")
                current = prog.get("current", "")
                if status == "done":
                    st.success(f"✅ Last run complete — {total} connections scraped")
                elif status == "error":
                    st.error(f"❌ Error: {current}")
                elif status in ("phase1", "phase2") and total > 0:
                    st.progress(done / total, text=f"Scraping {done}/{total} — {current}")
                elif status == "phase1":
                    st.info(f"Fetching connections list… {current}")
            except Exception:
                pass

    if scrape_btn:
        if not COOKIES_PATH.exists():
            st.error("LinkedIn cookies not found. Set them up in the **🔗 LinkedIn Setup** tab first.")
        else:
            with st.status("🔄 Scraping LinkedIn connections…", expanded=True) as scrape_status:
                proc = subprocess.Popen(
                    [sys.executable, str(ROOT / "scrapers" / "connections_scraper.py")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(ROOT),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
                logs: list[str] = []
                log_box = st.empty()
                for line in proc.stdout:
                    logs.append(line.rstrip())
                    log_box.code("\n".join(logs[-40:]), language="text")
                proc.wait()
                if proc.returncode == 0:
                    scrape_status.update(label="✅ Done! Connections loaded below.", state="complete")
                else:
                    scrape_status.update(label="❌ Scraper failed — check logs above", state="error")

    st.divider()

    # ── Load CSV ──────────────────────────────────────────────────────────────
    if not CONNECTIONS_CSV.exists():
        st.info("No connections scraped yet. Click **🔄 Scrape / Refresh** above to start.")
        st.stop()

    try:
        df_conn = pd.read_csv(CONNECTIONS_CSV)
    except Exception as e:
        st.error(f"Could not load connections CSV: {e}")
        st.stop()

    if df_conn.empty:
        st.warning("CSV is empty — try re-scraping.")
        st.stop()

    # Normalise nullable columns
    for col in ["months_in_role", "total_exp_years", "mutual_connections", "grad_year"]:
        if col in df_conn.columns:
            df_conn[col] = pd.to_numeric(df_conn[col], errors="coerce")

    for col in ["institutes", "current_company", "current_title", "seniority", "location", "degree", "headline"]:
        if col in df_conn.columns:
            df_conn[col] = df_conn[col].fillna("").astype(str)

    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown("#### Filter & Search")
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])

    with f1:
        search_query = st.text_input("Search name / company", placeholder="e.g. Google, Rahul")

    with f2:
        seniority_options = sorted([s for s in df_conn["seniority"].unique() if s])
        selected_seniority = st.multiselect("Seniority", seniority_options, default=[])

    with f3:
        institute_query = st.text_input("Institute contains", placeholder="e.g. IIT, IIM, BITS")

    with f4:
        min_months = st.slider("Min months in current role", 0, 60, 0, step=3)

    # Apply filters
    filtered = df_conn.copy()

    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["name"].str.lower().str.contains(q, na=False)
            | filtered["current_company"].str.lower().str.contains(q, na=False)
            | filtered["headline"].str.lower().str.contains(q, na=False)
        ]

    if selected_seniority:
        filtered = filtered[filtered["seniority"].isin(selected_seniority)]

    if institute_query:
        filtered = filtered[
            filtered["institutes"].str.lower().str.contains(institute_query.lower(), na=False)
        ]

    if min_months > 0 and "months_in_role" in filtered.columns:
        filtered = filtered[filtered["months_in_role"].fillna(0) >= min_months]

    # ── Stats bar ─────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Showing", len(filtered))
    m2.metric("Total connections", len(df_conn))
    iit_iim = df_conn[df_conn["institutes"].str.contains("IIT|IIM", case=False, na=False)]
    m3.metric("IIT/IIM alumni", len(iit_iim))
    if "months_in_role" in df_conn.columns:
        stable = df_conn[df_conn["months_in_role"].fillna(0) >= 6]
        m4.metric("Stable (6m+ in role)", len(stable))

    st.divider()

    # ── Table ─────────────────────────────────────────────────────────────────
    display_cols = [
        "name", "current_company", "current_title", "seniority",
        "months_in_role", "institutes", "location",
        "total_exp_years", "mutual_connections", "profile_url",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    col_config = {
        "profile_url": st.column_config.LinkColumn("Profile", display_text="Open ↗"),
        "months_in_role": st.column_config.NumberColumn("Months in role", format="%d"),
        "total_exp_years": st.column_config.NumberColumn("Exp (yrs)", format="%d"),
        "mutual_connections": st.column_config.NumberColumn("Mutual", format="%d"),
    }

    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        column_config=col_config,
        use_container_width=True,
        height=520,
    )

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.divider()
    dl1, dl2, _ = st.columns([1, 1, 3])

    with dl1:
        st.download_button(
            label="⬇️ Download filtered CSV",
            data=filtered[display_cols].to_csv(index=False).encode("utf-8"),
            file_name=f"connections_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with dl2:
        st.download_button(
            label="⬇️ Download full CSV",
            data=df_conn.to_csv(index=False).encode("utf-8"),
            file_name=f"connections_full_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
