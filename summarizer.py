# summarizer.py
"""
Generate an executive-level markdown summary of today’s AU-finance headlines.

Key points
----------
* Creates data/ folder if absent.
* If any CSV is missing, automatically calls its collector script.
* Loads CSVs *after* ensuring they exist, so first-boot on Streamlit Cloud
  never crashes.
* Strips accidental ```markdown fences from the LLM output.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# Environment & constants
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv(find_dotenv())
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CSV_INFO = {
    "reddit_hot.csv":      ["scripts/reddit_hot_posts.py"],
    "yahoo_news.csv":      ["scripts/yahoo_finance_au_rss.py"],
    "google_trends_rising.csv": ["scripts/google_trends_serpapi.py"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Helper: ensure each CSV exists (run collector lazily if not)
# ──────────────────────────────────────────────────────────────────────────────
def _ensure_csvs() -> None:
    for csv_name, collect_cmd in CSV_INFO.items():
        csv_path = DATA_DIR / csv_name
        if not csv_path.exists():
            subprocess.run(["python", *collect_cmd], check=True)

# ──────────────────────────────────────────────────────────────────────────────
# Main public function
# ──────────────────────────────────────────────────────────────────────────────
def summarize() -> str:
    """Return pure-markdown executive summary (no code-block fences)."""
    _ensure_csvs()

    reddit  = pd.read_csv(DATA_DIR / "reddit_hot.csv")
    yahoo   = pd.read_csv(DATA_DIR / "yahoo_news.csv")
    gtrends = pd.read_csv(DATA_DIR / "google_trends_rising.csv")
    all_headlines = pd.concat([reddit, yahoo, gtrends], ignore_index=True)

    # Build LLM prompt
    prompt = (
        "Given the following Australian finance headlines, identify 4–5 strategic, "
        "high-level emerging themes. For each theme provide:\n"
        "1. A concise, engaging title with emoji.\n"
        "2. A brief strategic narrative (max 2–3 sentences).\n"
        "3. ONE concise marketing angle Motley Fool Australia could adopt.\n"
        "Include no more than TWO high-impact headlines (markdown hyperlinks) per theme.\n\n"
        "Present the output as pure markdown. Finish with a markdown table that has exactly "
        "three columns: Theme Title | Strategic Narrative Summary | Motley Fool Marketing Angle.\n\n"
        "Here are the headlines:\n\n"
    )

    for _, row in all_headlines.head(30).iterrows():
        url = row.get("url", "")
        if isinstance(url, str) and url.strip():
            prompt += f"- [{row['query']}]({url})\n"
        else:
            prompt += f"- {row['query']}\n"

    # Call GPT-4o
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    summary = resp.choices[0].message.content.strip()

    # Remove accidental ```markdown fences if present
    if summary.lower().startswith("```markdown"):
        summary = summary.split("\n", 1)[1].rstrip("`").strip()
    summary = summary.strip("` ")

    return summary


# CLI test
if __name__ == "__main__":
    print(summarize())
