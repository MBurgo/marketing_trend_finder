# app.py
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo   # Python 3.9+

import streamlit as st
from summarizer import summarize

# ──────────────────────────────────────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🇦🇺 Finance Trends Finder",
    layout="centered",
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Throttle Settings
# ──────────────────────────────────────────────────────────────────────────────
DATA_DIR          = Path("data")
DATA_DIR.mkdir(exist_ok=True)

LAST_RUN_FILE     = DATA_DIR / "last_run.txt"
LAST_SUMMARY_FILE = DATA_DIR / "last_summary.md"
COOLDOWN_HOURS    = 3

AEST = ZoneInfo("Australia/Brisbane")

def _last_run_time_utc() -> datetime | None:
    if LAST_RUN_FILE.exists():
        return datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
    return None


def _within_cooldown() -> bool:
    last = _last_run_time_utc()
    return last and (datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS))


def _display_summary(summary_markdown: str) -> None:
    """Split summary on stand-alone ‘---’ lines and render neatly."""
    sections = re.split(r"\n---\n", summary_markdown)
    for sec in sections:
        if sec.strip():
            with st.container(border=True):
                st.markdown(sec.strip(), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
st.title("🇦🇺 Today's Australian Finance Trends")
st.markdown(
    "This tool scrapes Google Trends, Yahoo Finance and AU-specific investing subreddits to surface emerging financial themes and actionable marketing angles."
)
st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Generate Button
# ──────────────────────────────────────────────────────────────────────────────
if st.button("🔍 Generate Today's Summary"):

    if _within_cooldown() and LAST_SUMMARY_FILE.exists():
        last_run_utc = _last_run_time_utc()
        next_time_utc = last_run_utc + timedelta(hours=COOLDOWN_HOURS)
        next_time_aest = next_time_utc.astimezone(AEST)

        st.info(
            "Serving cached summary generated at "
            f"**{last_run_utc.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}** "
            f"(cool-down {COOLDOWN_HOURS} h).\n\n"
            f"You can generate a fresh summary after "
            f"{next_time_aest.strftime('%I:%M %p %d %b %Y AEST')}."
        )
        _display_summary(LAST_SUMMARY_FILE.read_text())
        st.stop()

    # Otherwise generate a fresh summary
    with st.spinner("Fetching headlines and generating insights …"):
        subprocess.run(["python", "scripts/reddit_hot_posts.py"])
        subprocess.run(["python", "scripts/yahoo_finance_au_rss.py"])
        subprocess.run(["python", "scripts/google_trends_serpapi.py"])

        summary_raw = summarize().lstrip("n").strip()  # remove stray 'n' if present

        # Cache timestamp & summary (timestamp saved in UTC)
        LAST_RUN_FILE.write_text(datetime.utcnow().isoformat())
        LAST_SUMMARY_FILE.write_text(summary_raw)

    _display_summary(summary_raw)
    st.success("✅ Summary generated successfully!")

# ────────────────────────────────────────────────────
