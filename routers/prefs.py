from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, json

router = APIRouter(prefix="/prefs", tags=["prefs"])

# ---- file fallback paths (used locally if no KV) ----
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
TOPICS_FILE = os.path.join(DATA_DIR, "prefs_topics.json")
HOME_FILE   = os.path.join(DATA_DIR, "prefs_home.json")
CAL_FILE    = os.path.join(DATA_DIR, "prefs_calendar.json")

# ---- optional Key-Value (Redis) backend ----
KV_URL = os.getenv("KV_URL", "redis://red-d2v10gbe5dus73f7orv0:6379")  # swap to rediss:// if TLS
_R = None
try:
    import redis  # requires 'redis' in requirements.txt
    if KV_URL:
        _R = redis.from_url(KV_URL, decode_responses=True)
except Exception:
    _R = None

_KV_TOPICS   = "prefs:topics"
_KV_HOME     = "prefs:home"
_KV_CALENDAR = "prefs:calendar"

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

# ---------- News topics (unchanged API) ----------
class NewsPrefsIn(BaseModel):
    topics: List[str] = []

def _read_topics() -> List[str]:
    if _R:
        raw = _R.get(_KV_TOPICS)
        return json.loads(raw) if raw else []
    _ensure_dir()
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_topics(topics: List[str]):
    if _R:
        _R.set(_KV_TOPICS, json.dumps(topics))
        return
    _ensure_dir()
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2)

@router.get("/news", response_model=NewsPrefsIn)
def get_news_prefs():
    return NewsPrefsIn(topics=_read_topics())

@router.post("/news", response_model=NewsPrefsIn)
def set_news_prefs(prefs: NewsPrefsIn):
    _write_topics(prefs.topics or [])
    return prefs

# ---------- Home location (new) ----------
class HomePrefs(BaseModel):
    lat: float
    lon: float
    tz: Optional[str] = None  # e.g., "America/Los_Angeles"

def _read_home() -> Optional[HomePrefs]:
    if _R:
        raw = _R.get(_KV_HOME)
        return HomePrefs(**json.loads(raw)) if raw else None
    _ensure_dir()
    if not os.path.exists(HOME_FILE):
        return None
    with open(HOME_FILE, "r", encoding="utf-8") as f:
        return HomePrefs(**json.load(f))

def _write_home(h: HomePrefs):
    data = h.dict()
    if _R:
        _R.set(_KV_HOME, json.dumps(data))
        return
    _ensure_dir()
    with open(HOME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@router.get("/home", response_model=HomePrefs)
def get_home_prefs():
    h = _read_home()
    if not h:
        raise HTTPException(404, "Home location not set.")
    return h

@router.post("/home", response_model=HomePrefs)
def set_home_prefs(h: HomePrefs):
    _write_home(h)
    return h

# ---------- Calendar ICS (new) ----------
class CalendarPrefs(BaseModel):
    ics_url: str  # public or private ICS URL

def _read_calendar() -> Optional[CalendarPrefs]:
    if _R:
        raw = _R.get(_KV_CALENDAR)
        return CalendarPrefs(**json.loads(raw)) if raw else None
    _ensure_dir()
    if not os.path.exists(CAL_FILE):
        return None
    with open(CAL_FILE, "r", encoding="utf-8") as f:
        return CalendarPrefs(**json.load(f))

def _write_calendar(c: CalendarPrefs):
    data = c.dict()
    if _R:
        _R.set(_KV_CALENDAR, json.dumps(data))
        return
    _ensure_dir()
    with open(CAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@router.get("/calendar", response_model=CalendarPrefs)
def get_calendar_prefs():
    c = _read_calendar()
    if not c:
        raise HTTPException(404, "Calendar ICS URL not set.")
    return c

@router.post("/calendar", response_model=CalendarPrefs)
def set_calendar_prefs(c: CalendarPrefs):
    _write_calendar(c)
    return c



