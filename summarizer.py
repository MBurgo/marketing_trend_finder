# summarizer.py

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load data
reddit = pd.read_csv("data/reddit_hot.csv")
yahoo = pd.read_csv("data/yahoo_news.csv")
gtrends = pd.read_csv("data/google_trends_rising.csv")

# Concatenate dataframes
all_headlines = pd.concat([reddit, yahoo, gtrends], ignore_index=True)

# Prepare formatted prompt (limited to top 30 headlines for brevity)
prompt = (
    "Given the following Australian finance headlines, identify 4–5 strategic, high-level emerging themes. "
    "For each theme provide:\n"
    "1. A concise, engaging title with emoji.\n"
    "2. A brief strategic narrative (2–3 sentences maximum).\n"
    "3. Exactly ONE concise marketing angle Motley Fool Australia could adopt.\n"
    "Include no more than TWO of the most impactful headlines (with markdown hyperlinks) per theme.\n\n"
    "Present in a concise, executive-friendly markdown format. At the end, include a clearly formatted markdown table summarizing the themes. "
    "The table must have three columns: Theme Title, Strategic Narrative Summary, and Motley Fool Marketing Angle, each clearly separated by vertical bars, and with proper markdown table formatting (header row, separator row, and alignment indicators).\n\n"
    "Here are the headlines:\n\n"
)

# Adding formatted headlines (top 30)
for _, row in all_headlines.head(30).iterrows():
    if 'url' in row and pd.notna(row['url']):
        prompt += f"- [{row['query']}]({row['url']})\n"
    else:
        prompt += f"- {row['query']}\n"

# Summarize with GPT-4o
def summarize():
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    # Clean up summary output explicitly
    summary = response.choices[0].message.content.strip()

    # Explicitly remove unwanted markdown indicators
    if summary.lower().startswith("```markdown"):
        summary = summary[10:].strip()
    summary = summary.strip("` ")

    return summary

# For testing locally
if __name__ == "__main__":
    print(summarize())
