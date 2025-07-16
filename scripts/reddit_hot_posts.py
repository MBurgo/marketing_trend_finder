"""Reddit – Hot posts (24 h) from AusFinance / ASX_Bets / AustralianStocks."""
from __future__ import annotations
import os, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd, praw
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
CSV  = DATA / "reddit_hot.csv"

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT", "mfa_trend_bot"),
)
reddit.read_only = True

SUBS = ["AusFinance", "ASX_Bets", "AustralianStocks"]
CUTOFF = datetime.now(timezone.utc) - timedelta(days=1)

rows = []
for sub in SUBS:
    for post in reddit.subreddit(sub).hot(limit=40):
        ts = datetime.fromtimestamp(post.created_utc, timezone.utc)
        if ts < CUTOFF:
            continue
        rows.append({
            "parent_topic": sub,
            "query": post.title.strip(),
            "url": post.url,  # Add URL here
            "score": post.score * 0.9,
            "comments": post.num_comments,
            "created": ts.isoformat(),
        })

        time.sleep(1)

pd.DataFrame(rows).to_csv(CSV, index=False)
print(f"✓ {len(rows)} Reddit rows → {CSV.relative_to(ROOT)}")
