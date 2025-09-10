import json, os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/prefs", tags=["prefs"])

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json"))
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def _load() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"topics": [], "home": {}, "calendar": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"topics": [], "home": {}, "calendar": {}}

def _save(d: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

# ---- News topics ----
@router.get("/news")
def get_news_prefs():
    return {"topics": _load().get("topics", [])}

@router.post("/news")
def upsert_news(payload: Dict[str, List[str]]):
    topics = payload.get("topics", [])
    if not isinstance(topics, list):
        raise HTTPException(status_code=400, detail="topics must be a list[str]")
    d = _load()
    merged = list(dict.fromkeys([*d.get("topics", []), *[t for t in topics if t]]))
    d["topics"] = merged
    _save(d)
    return {"ok": True, "topics": merged}

@router.delete("/news/{topic}")
def remove_topic(topic: str):
    d = _load()
    d["topics"] = [t for t in d.get("topics", []) if t.lower() != (topic or "").lower()]
    _save(d)
    return {"ok": True, "topics": d["topics"]}

# ---- Home (location + units + tz) ----
@router.get("/home")
def get_home():
    return {"home": _load().get("home", {})}

@router.post("/home")
def set_home(payload: Dict[str, Any]):
    allowed = {"city", "zip", "lat", "lon", "tz", "units"}
    if not any(k in payload for k in allowed):
        raise HTTPException(status_code=400, detail="provide city or zip (and optional tz, units)")
    d = _load()
    home = d.get("home", {}) or {}
    home.update({k: v for k, v in payload.items() if k in allowed and v is not None})
    # sanity
    if "units" in home and str(home["units"]).lower() not in ("imperial", "metric"):
        home["units"] = "imperial"
    d["home"] = home
    _save(d)
    return {"ok": True, "home": home}

@router.post("/set_home")
def set_home_alias(payload: Dict[str, Any]):
    return set_home(payload)

# ---- Calendar (ICS URL) ----
@router.get("/calendar")
def get_calendar():
    return {"calendar": _load().get("calendar", {})}

@router.post("/calendar")
def set_calendar(payload: Dict[str, Any]):
    url = (payload.get("ics_url") or payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="ics_url is required")
    d = _load()
    d["calendar"] = {"ics_url": url}
    _save(d)
    return {"ok": True, "calendar": d["calendar"]}

@router.post("/set_calendar")
def set_calendar_alias(payload: Dict[str, Any]):
    return set_calendar(payload)


