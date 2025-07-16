# app.py
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

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
.container-card              { padding: 0.5rem 1rem; }
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
DATA_DIR        = Path("data")
LAST_RUN_FILE   = DATA_DIR / "last_run.txt"
COOLDOWN_HOURS  = 3

def _too_soon() -> bool:
    """Return True if a summary was generated < COOLDOWN_HOURS ago."""
    if LAST_RUN_FILE.exists():
        last = datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
        return datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS)
    return False

# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
st.title("🇦🇺 Today's Australian Finance Trends")
st.markdown(
    "A concise, strategic summary of emerging financial themes and actionable marketing angles."
)
st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Generate Button
# ──────────────────────────────────────────────────────────────────────────────
if st.button("🔍 Generate Today's Summary"):

    # Throttle check
    if _too_soon():
        next_time = datetime.fromisoformat(
            LAST_RUN_FILE.read_text().strip()
        ) + timedelta(hours=COOLDOWN_HOURS)
        st.warning(
            f"A summary was generated less than {COOLDOWN_HOURS} hours ago. We are showing cached results from that run."
            f"Please try again after {next_time.strftime('%I:%M %p UTC')}."
        )
        st.stop()

    with st.spinner("Fetching headlines and generating insights …"):
        # Run collectors
        subprocess.run(["python", "scripts/reddit_hot_posts.py"])
        subprocess.run(["python", "scripts/yahoo_finance_au_rss.py"])
        subprocess.run(["python", "scripts/google_trends_serpapi.py"])

        # Generate summary
        summary_raw = summarize().lstrip("n").strip()  # strip stray 'n' & whitespace

        # Record timestamp
        DATA_DIR.mkdir(exist_ok=True)
        LAST_RUN_FILE.write_text(datetime.utcnow().isoformat())

    # ─ Split on stand-alone “---” lines only ─
    sections = re.split(r"\n---\n", summary_raw)
    for sec in sections:
        if sec.strip():
            with st.container(border=True):
                st.markdown(sec.strip(), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

    st.success("✅ Summary generated successfully!")

# ──────────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("🧑‍💻 _Built by Burgo_")
