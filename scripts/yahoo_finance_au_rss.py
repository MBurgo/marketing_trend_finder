"""Yahoo Finance AU – Top Stories (<24 h)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import feedparser, pandas as pd, re, hashlib

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
CSV  = DATA / "yahoo_news.csv"

RSS_URL = "https://au.finance.yahoo.com/rss/section-news"
CUTOFF  = datetime.now(timezone.utc) - timedelta(days=1)
FIXED_SCORE = 150

feed = feedparser.parse(RSS_URL)
rows = []
for ent in feed.entries:
    pub = datetime(*ent.published_parsed[:6], tzinfo=timezone.utc)
    if pub < CUTOFF:
        continue
    title = re.sub(r"\s+", " ", ent.title).strip()
    slug  = hashlib.md5(title.lower().encode()).hexdigest()[:10]
    rows.append({
        "parent_topic": "YahooFinanceAU",
        "query": title,
        "url": ent.link,  # Add URL here
        "score": FIXED_SCORE,
        "published": pub.isoformat(),
        "slug": slug,
    })

pd.DataFrame(rows).to_csv(CSV, index=False)
print(f"✓ {len(rows)} Yahoo AU headlines → {CSV.relative_to(ROOT)}")
