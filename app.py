# app.py
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo   # Python 3.9+

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Page config & simple theme
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="🇦🇺 Finance Trends Finder", layout="centered")

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
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

LAST_RUN_FILE     = DATA_DIR / "last_run.txt"
LAST_SUMMARY_FILE = DATA_DIR / "last_summary.md"
COOLDOWN_HOURS    = 3
AEST              = ZoneInfo("Australia/Brisbane")

# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────
def _last_run_time_utc() -> datetime | None:
    if LAST_RUN_FILE.exists():
        return datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
    return None


def _within_cooldown() -> bool:
    last = _last_run_time_utc()
    return bool(last and (datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS)))


def _display_summary(md: str) -> None:
    """Render markdown, split on standalone '---' lines for nicer boxes."""
    sections = re.split(r"\n---\n", md)
    for sec in sections:
        if sec.strip():
            with st.container(border=True):
                st.markdown(sec.strip(), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)


def run_collector(cmd: list[str], label: str) -> None:
    """Run a collector script and surface its stderr if it fails."""
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if res.stdout:
            st.sidebar.write(f"✅ {label} OK:\n{res.stdout}")
    except subprocess.CalledProcessError as e:
        st.error(
            f"❌ {label} failed (exit {e.returncode}).\n\n"
            f"Stderr output:\n{e.stderr or '— no stderr —'}"
        )
        st.stop()

# ─────────────────────────────────────────────────────────────
# Runtime sanity-check sidebar (always visible)
# ─────────────────────────────────────────────────────────────
with st.sidebar.expander("🛠 Runtime sanity check", expanded=False):
    st.write("**Current working directory:**", os.getcwd())
    st.write("**DATA_DIR absolute path:**", DATA_DIR.resolve())
    st.write(
        "**Current contents of `data/`:**",
        [p.name for p in DATA_DIR.iterdir()] if DATA_DIR.exists() else "— empty —",
    )

# ─────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────
st.title("🇦🇺 Today's Australian Finance Trends")
st.markdown(
    "This tool scrapes Google Trends, Yahoo Finance AU and AU-investing subreddits "
    "to surface emerging financial themes and actionable marketing angles."
)
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🔍 Generate today's summary"):

    # 1) Serve cached markdown if still in cooldown
    if _within_cooldown() and LAST_SUMMARY_FILE.exists():
        last_run_utc = _last_run_time_utc()
        next_time    = last_run_utc + timedelta(hours=COOLDOWN_HOURS)
        st.info(
            "Serving cached summary generated at "
            f"**{last_run_utc.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}** "
            f"(cool-down {COOLDOWN_HOURS} h). "
            "You can generate a fresh one after "
            f"{next_time.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}."
        )
        _display_summary(LAST_SUMMARY_FILE.read_text())
        st.stop()

    # 2) Run collector scripts
    with st.spinner("Fetching headlines and generating insights …"):
        run_collector(["python", "scripts/reddit_hot_posts.py"],   "Reddit collector")
        run_collector(["python", "scripts/yahoo_finance_au_rss.py"], "Yahoo collector")
        run_collector(["python", "scripts/google_trends_serpapi.py"], "Trends collector")

        # 3) Import summarizer *after* CSVs exist
        from summarizer import summarize

        summary_raw = summarize().lstrip("n").strip()

        # 4) Cache timestamp & summary
        LAST_RUN_FILE.write_text(datetime.utcnow().isoformat())
        LAST_SUMMARY_FILE.write_text(summary_raw)

    _display_summary(summary_raw)
    st.success("✅ Summary generated successfully — scroll up to read!")
