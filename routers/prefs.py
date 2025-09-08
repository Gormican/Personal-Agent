from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os, json

router = APIRouter(prefix="/prefs", tags=["prefs"])

# ---- file fallback path (used locally if no KV) ----
DATA_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json")
)

# ---- optional Key-Value (Redis) backend ----
# Prefer setting KV_URL in Render env; the default below is only for convenience.
KV_URL = os.getenv("KV_URL", "redis://red-d2v10gbe5dus73f7orv0:6379")  # use rediss://... if TLS
_KV_KEY = "prefs:topics"
_R = None
try:
    import redis  # make sure 'redis' is in requirements.txt
    if KV_URL:
        _R = redis.from_url(KV_URL, decode_responses=True)
except Exception:
    _R = None  # harmless fallback to file if Redis not available

class NewsPrefsIn(BaseModel):
    topics: List[str] = []

def _ensure_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"topics": []}, f)

def _read() -> dict:
    # Prefer KV if available
    if _R:
        raw = _R.get(_KV_KEY)
        return {"topics": json.loads(raw) if raw else []}
    # Fallback to local JSON file
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(d: dict):
    if _R:
        _R.set(_KV_KEY, json.dumps(d.get("topics", [])))
        return
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

@router.get("/news", response_model=NewsPrefsIn)
def get_news_prefs():
    return NewsPrefsIn(**_read())

@router.post("/news", response_model=NewsPrefsIn)
def set_news_prefs(prefs: NewsPrefsIn):
    _write(prefs.dict())
    return prefs


