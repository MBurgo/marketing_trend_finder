# app.py
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo  # Python 3.9+

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Page config & simple theme
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🇦🇺 Finance Trends Finder",
    layout="centered",
)

st.markdown(
    """
<style>
html, body, [class*="css"]  { font-family: 'Roboto', sans-serif; font-size: 17px; }
h1, h2, h3                   { color: #485CC7; }
h1                           { font-size: 34px !important; font-weight: 700; }
h2                           { font-size: 26px !important; }
h3                           { font-size: 20px !important; }
table                        { width: 100%; border-collapse: collapse; margin: 12px 0; }
th, td                       { border: 1px solid #ddd; padding: 6px; }
th                           { background-color: #f2f2f2; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# Paths & cooldown settings
# ─────────────────────────────────────────────────────────────
DATA_DIR          = Path("data")
DATA_DIR.mkdir(exist_ok=True)

LAST_RUN_FILE     = DATA_DIR / "last_run.txt"
LAST_SUMMARY_FILE = DATA_DIR / "last_summary.md"
COOLDOWN_HOURS    = 3
AEST              = ZoneInfo("Australia/Brisbane")


def _last_run_time_utc() -> datetime | None:
    if LAST_RUN_FILE.exists():
        return datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
    return None


def _within_cooldown() -> bool:
    last = _last_run_time_utc()
    return bool(last and (datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS)))


def _display_summary(summary_markdown: str) -> None:
    """Split summary on stand-alone ‘---’ lines and render neatly."""
    sections = re.split(r"\n---\n", summary_markdown)
    for sec in sections:
        if sec.strip():
            with st.container(border=True):
                st.markdown(sec.strip(), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Optional owner-only debug panel
# Show it only if SHOW_DEBUG_FILES is set in env / secrets
# ─────────────────────────────────────────────────────────────
if os.getenv("SHOW_DEBUG_FILES", "").lower() in {"1", "true", "yes"}:
    with st.sidebar.expander("🔍 Debug: data folder", expanded=False):
        files = sorted(p.name for p in DATA_DIR.glob("*"))
        st.write(files or "No files yet")
        if files:
            latest = max(DATA_DIR.glob("*"), key=lambda p: p.stat().st_mtime)
            st.caption(f"Preview of `{latest.name}`")
            try:
                st.dataframe(pd.read_csv(latest).head())
            except Exception as e:
                st.error(f"Could not read file: {e}")

# ─────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────
st.title("🇦🇺 Today's Australian Finance Trends")
st.markdown(
    "This tool scrapes Google Trends, Yahoo Finance and AU-investing subreddits "
    "to surface emerging financial themes and actionable marketing angles."
)
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🔍 Generate today's summary"):

    # 1) Serve cached version if still in cooldown
    if _within_cooldown() and LAST_SUMMARY_FILE.exists():
        last_run_utc = _last_run_time_utc()
        next_time = last_run_utc + timedelta(hours=COOLDOWN_HOURS)
        st.info(
            "Serving cached summary generated at "
            f"**{last_run_utc.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}** "
            f"(cool-down {COOLDOWN_HOURS} h). "
            "You can generate a fresh summary after "
            f"{next_time.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}."
        )
        _display_summary(LAST_SUMMARY_FILE.read_text())
        st.stop()

    # 2) Run collector scripts
    with st.spinner("Fetching headlines and generating insights …"):
        subprocess.run(["python", "scripts/reddit_hot_posts.py"], check=True)
        subprocess.run(["python", "scripts/yahoo_finance_au_rss.py"], check=True)
        subprocess.run(["python", "scripts/google_trends_serpapi.py"], check=True)

        # 3) Import summarizer *after* CSVs exist
        from summarizer import summarize

        summary_raw = summarize().lstrip("n").strip()

        # 4) Cache timestamp & summary
        LAST_RUN_FILE.write_text(datetime.utcnow().isoformat())
        LAST_SUMMARY_FILE.write_text(summary_raw)

    _display_summary(summary_raw)
    st.success("✅ Summary generated successfully — scroll up to read!")
