# summarizer.py

"""Generate an executive‑level markdown summary of today’s AU‑finance headlines.

Key design choices
------------------
* **Lazy CSV loading** – the CSVs are read *inside* `summarize()` so first‑boot on
  Streamlit Cloud doesn’t crash when the `data/` folder isn’t there yet.
* **No global state that depends on runtime files** – only the OpenAI client is
  initialised at import‑time; everything else happens inside the function.
* **Back‑tick stripping** – guarantees the markdown Block isn’t wrapped in
  ```markdown ...``` which previously broke Streamlit rendering.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Initialise OpenAI client once.
# ---------------------------------------------------------------------------
load_dotenv(find_dotenv())
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Path where the collector scripts write their CSVs
DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# Main function called by Streamlit UI
# ---------------------------------------------------------------------------

def summarize() -> str:
    """Return a pure‑markdown executive summary (no triple back‑ticks)."""

    # --- Load fresh headline CSVs ------------------------------------------------
    reddit_csv  = DATA_DIR / "reddit_hot.csv"
    yahoo_csv   = DATA_DIR / "yahoo_news.csv"
    gtrends_csv = DATA_DIR / "google_trends_rising.csv"

    # These files are created by the collector scripts just before summarize()
    # is invoked from `app.py`. If they’re missing we raise – Streamlit will
    # surface a clear error rather than a cryptic FileNotFound in the logs.
    reddit  = pd.read_csv(reddit_csv)
    yahoo   = pd.read_csv(yahoo_csv)
    gtrends = pd.read_csv(gtrends_csv)

    all_headlines = pd.concat([reddit, yahoo, gtrends], ignore_index=True)

    # --- Build the LLM prompt ----------------------------------------------------
    prompt = (
        "Given the following Australian finance headlines, identify 4–5 strategic, "
        "high‑level emerging themes. For each theme provide:\n"
        "1. A concise, engaging title with emoji.\n"
        "2. A brief strategic narrative (max 2–3 sentences).\n"
        "3. ONE concise marketing angle Motley Fool Australia could adopt.\n"
        "Include no more than TWO high‑impact headlines (markdown hyperlinks) per theme.\n\n"
        "Present the output as pure markdown. Finish with a markdown table that has "
        "exactly three columns: Theme Title, Strategic Narrative Summary, Motley Fool "
        "Marketing Angle. Ensure the table header and separator rows are correct.\n\n"
        "Here are the headlines:\n\n"
    )

    for _, row in all_headlines.head(30).iterrows():
        if pd.notna(row.get("url")):
            prompt += f"- [{row['query']}]({row['url']})\n"
        else:
            prompt += f"- {row['query']}\n"

    # --- Call OpenAI -------------------------------------------------------------
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    summary = response.choices[0].message.content.strip()

    # --- Strip accidental ```markdown fences if the model produced them ---------
    if summary.lower().startswith("```markdown"):
        summary = summary.split("\n", 1)[1]  # drop first line
    summary = summary.strip("` ")

    return summary


# ---------------------------------------------------------------------------
# CLI helper for local testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(summarize())
