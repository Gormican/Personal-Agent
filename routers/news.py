from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List
import feedparser
import os, json

router = APIRouter(prefix="/news", tags=["news"])

# ---- models ----
class Article(BaseModel):
    title: str
    link: str
    source: str | None = None
    published: str | None = None

class NewsResponse(BaseModel):
    topic: str
    count: int
    articles: List[Article]

# ---- helpers ----
def _google_news(topic: str, n: int = 5) -> List[Article]:
    url = f"https://news.google.com/rss/search?q={topic}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items: List[Article] = []
    for e in feed.entries[:n]:
        src = None
        if hasattr(e, "source") and getattr(e, "source"):
            try:
                src = e.source.get("title")  # not always present
            except Exception:
                src = None
        items.append(Article(
            title=e.get("title", ""),
            link=e.get("link", ""),
            source=src,
            published=e.get("published"),
        ))
    return items

# read saved topics (shared with prefs.py path)
DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json"))
def _read_topics() -> List[str]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("topics", [])

# ---- routes ----
@router.get("/", response_model=NewsResponse)
def get_news(topic: str = Query(..., min_length=2, max_length=60), limit: int = 5):
    arts = _google_news(topic, n=limit)
    return NewsResponse(topic=topic, count=len(arts), articles=arts)

class Bucket(BaseModel):
    topic: str
    articles: List[Article]

class ForMeResponse(BaseModel):
    topics: List[str]
    buckets: List[Bucket]

@router.get("/for-me", response_model=ForMeResponse)
def news_for_me(limit_per_topic: int = 3):
    topics = _read_topics()
    buckets = [Bucket(topic=t, articles=_google_news(t, n=limit_per_topic)) for t in topics]
    return ForMeResponse(topics=topics, buckets=buckets)
