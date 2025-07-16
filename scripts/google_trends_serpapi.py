"""Google Trends (AU) — rising queries + timeseries via SerpAPI (with URLs)."""
from __future__ import annotations
import os, requests, re, pandas as pd
from datetime import datetime, date, timezone
from pathlib import Path
from time import sleep
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)

API_KEY = os.getenv("SERPAPI_KEY")
if not API_KEY:
    raise EnvironmentError("SERPAPI_KEY missing in env or .env file")
SERP_URL = "https://serpapi.com/search.json"

GEO = "AU"
REQ_SLEEP = 0.8

KEYWORDS = {
   "ASX 200":              "/m/0bl5c2",
   "Stocks":               "/m/077mq",
   "Dividend investing":   "/m/02j9s0",
   "Share":                "/m/03jzl9",
   "Small‑cap stocks":     "/g/11fjtgs_qg",
   "ETFs":                 "/m/02mxjp",
}

TS_CSV   = DATA / "google_trends_timeseries.csv"
RISE_CSV = DATA / "google_trends_rising.csv"

def _call_serp(params: dict) -> dict:
    params["api_key"] = API_KEY
    r = requests.get(SERP_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def _to_int(val):
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        if val.lower() == "breakout":
            return 1000
        digits = re.sub(r"[^\d]", "", val)
        return int(digits) if digits else 0
    return 0

def _fetch_one(mid: str, name: str):
    rise_rows = []  # <-- fixed definition here
    ts_rows = []

    # Rising queries
    rising = _call_serp({
        "engine": "google_trends",
        "data_type": "RELATED_QUERIES",
        "q": mid,
        "date": "now 7-d",
        "geo": GEO,
    }).get("related_queries", {}).get("rising", [])

    for idx, item in enumerate(rising, 1):
        query = item.get("query") or item.get("topic_title", "UNKNOWN")
        rise_rows.append({
            "parent_topic": name,
            "query": query,
            "url": f"https://trends.google.com/trends/explore?q={query.replace(' ', '+')}&geo=AU",  # <-- URL added
            "score": _to_int(item.get("value", "")),
            "rank": item.get("rank", idx),
        })

    # Timeseries (optional)
    ts = _call_serp({
        "engine": "google_trends",
        "data_type": "TIMESERIES",
        "q": mid,
        "date": "now 7-d",
        "geo": GEO,
    }).get("interest_over_time", {}).get("timeline_data", [])

    for e in ts:
        day = datetime.fromtimestamp(int(e["timestamp"]), timezone.utc).date()
        val = e["values"][0].get("extracted_value") or int(e["values"][0]["value"])
        ts_rows.append({"date": day, "topic": name, "freq": val})

    return ts_rows, rise_rows

def main():
    ts_all, rise_all = [], []
    for nm, mid in KEYWORDS.items():
        ts, rise = _fetch_one(mid, nm)
        ts_all += ts
        rise_all += rise
        sleep(REQ_SLEEP)

    pd.DataFrame(ts_all).to_csv(TS_CSV, index=False)
    pd.DataFrame(rise_all).assign(as_of=date.today()).to_csv(RISE_CSV, index=False)

    print(f"✓ {len(ts_all)} TS rows → {TS_CSV.relative_to(ROOT)}")
    print(f"✓ {len(rise_all)} rising queries → {RISE_CSV.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
