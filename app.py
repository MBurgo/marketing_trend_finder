# app.py  (drop-in replacement)
import os, re, subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo  # Py 3.9+

import pandas as pd
import streamlit as st
from summarizer import summarize

# ── Page & theme ────────────────────────────────────────────────────────────
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

# ── Paths / constants ───────────────────────────────────────────────────────
DATA_DIR          = Path("data"); DATA_DIR.mkdir(exist_ok=True)
LAST_RUN_FILE     = DATA_DIR / "last_run.txt"
LAST_SUMMARY_FILE = DATA_DIR / "last_summary.md"
COOLDOWN_HOURS    = 3
AEST              = ZoneInfo("Australia/Brisbane")

# ── Owner-only debug panel (opt-in) ─────────────────────────────────────────
SHOW_DEBUG = os.getenv("SHOW_DEBUG_FILES", "0") == "1" or bool(
    st.secrets.get("show_debug_files", False)
)
if SHOW_DEBUG:
    st.sidebar.header("🔍 Debug – `data/` folder")
    if st.sidebar.button("Refresh file list") or "file_list" not in st.session_state:
        st.session_state["file_list"] = sorted(os.listdir(DATA_DIR))
    files = st.session_state["file_list"]
    st.sidebar.write(files or "(empty)")
    if files:
        latest = sorted((DATA_DIR / f for f in files), key=lambda p: p.stat().st_mtime)[-1]
        st.sidebar.write(f"Previewing **{latest.name}**")
        st.sidebar.dataframe(pd.read_csv(latest))

# ── Helpers ────────────────────────────────────────────────────────────────
def _last_run_time_utc() -> datetime | None:
    if LAST_RUN_FILE.exists():
        return datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
    return None

def _within_cooldown() -> bool:
    last = _last_run_time_utc()
    return bool(last and (datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS)))

def _display_summary(md: str) -> None:
    for section in re.split(r"\n---\n", md):
        if section.strip():
            with st.container(border=True):
                st.markdown(section.strip(), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

# ── UI ──────────────────────────────────────────────────────────────────────
st.title("🇦🇺 Today's Australian Finance Trends")
st.markdown(
    "This tool scrapes Google Trends, Yahoo Finance and AU-centric investing "
    "subreddits to unearth emerging themes and actionable marketing angles."
)
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🔍 Generate Today's Summary"):

    # Serve cached version if still in cool-down window
    if _within_cooldown() and LAST_SUMMARY_FILE.exists():
        last_utc = _last_run_time_utc()
        next_utc = last_utc + timedelta(hours=COOLDOWN_HOURS)
        st.info(
            f"Serving cached summary from "
            f"**{last_utc.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}** "
            f"(cool-down {COOLDOWN_HOURS} h).  \n\n"
            f"Fresh generation available after "
            f"{next_utc.astimezone(AEST).strftime('%I:%M %p %d %b %Y AEST')}."
        )
        _display_summary(LAST_SUMMARY_FILE.read_text())
        st.stop()

    # Collect fresh data & summarise
    with st.spinner("Fetching headlines and generating insights …"):
        subprocess.run(["python", "scripts/reddit_hot_posts.py"],  check=True)
        subprocess.run(["python", "scripts/yahoo_finance_au_rss.py"], check=True)
        subprocess.run(["python", "scripts/google_trends_serpapi.py"], check=True)

        summary_raw = summarize().lstrip("n").strip()

        LAST_RUN_FILE.write_text(datetime.utcnow().isoformat())
        LAST_SUMMARY_FILE.write_text(summary_raw)

    _display_summary(summary_raw)
    st.success("✅ Summary generated successfully!")
