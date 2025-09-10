# app/routers/prefs.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, AnyHttpUrl
from typing import Any, Dict, List, Optional
import os, json

router = APIRouter(prefix="/prefs", tags=["prefs"])

# ---------- simple file persistence ----------
DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DATA_FILE = os.path.join(DATA_DIR, "prefs.json")

def _ensure_file() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"topics": [], "home": {}, "calendar": {}}, f)

def _read() -> Dict[str, Any]:
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(d: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

def _mask_ics(url: str) -> str:
    if not url:
        return ""
    parts = url.split("/private-", 1)
    if len(parts) == 2:
        return parts[0] + "/private-********/basic.ics"
    return url.split("?")[0].split("#")[0][:30] + "…"

# ---------- models ----------
class HomePrefIn(BaseModel):
    zip: Optional[str] = None
    city: Optional[str] = None
    tz: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    units: Optional[str] = None  # "imperial" | "metric"

class CalendarPrefIn(BaseModel):
    ics_url: AnyHttpUrl

# ---------- NEWS ----------
@router.get("/news")
def get_news_prefs():
    d = _read()
    return {"topics": d.get("topics", [])}

@router.post("/news")
def upsert_news(body: Dict[str, Any] = Body(...)):
    """
    Accepts:
      - {"topic": "Padres"} -> append (de-duped)
      - {"topics": ["A","B"]} -> replace list
    """
    d = _read()
    topics: List[str] = d.get("topics", [])

    def norm(s: Any) -> str:
        return str(s).strip()

    if "topic" in body:
        t = norm(body["topic"])
        if not t:
            raise HTTPException(status_code=400, detail="Empty topic.")
        # de-dupe case-insensitive but preserve original case
        if t.lower() not in [x.lower() for x in topics]:
            topics.append(t)
        d["topics"] = topics
        _write(d)
        return {"ok": True, "mode": "added", "topics": topics}

    if "topics" in body and isinstance(body["topics"], list):
        seen, uniq = set(), []
        for raw in body["topics"]:
            t = norm(raw)
            if t and t.lower() not in seen:
                seen.add(t.lower())
                uniq.append(t)
        d["topics"] = uniq
        _write(d)
        return {"ok": True, "mode": "replaced", "topics": uniq}

    raise HTTPException(status_code=400, detail="Provide 'topic' or 'topics' list.")

@router.delete("/news/{topic}")
def remove_topic(topic: str):
    d = _read()
    old = d.get("topics", [])
    remain = [t for t in old if t.lower() != topic.strip().lower()]
    d["topics"] = remain
    _write(d)
    return {"ok": True, "removed": topic, "topics": remain}

# ---------- HOME ----------
@router.get("/home")
def get_home():
    d = _read()
    return d.get("home", {})

@router.post("/home")
@router.post("/set_home")  # alias for older UI
def set_home(payload: HomePrefIn):
    d = _read()
    home = d.get("home", {})
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is None:
            continue
        home[k] = v
    d["home"] = home
    _write(d)
    return {"ok": True, "home": home}

# ---------- CALENDAR ----------
@router.get("/calendar")
def get_calendar():
    d = _read()
    ics_url = d.get("calendar", {}).get("ics_url", "")
    return {"configured": bool(ics_url), "ics_masked": _mask_ics(ics_url) if ics_url else ""}

@router.post("/calendar")
@router.post("/set_calendar")  # alias for older UI
def set_calendar(payload: CalendarPrefIn):
    d = _read()
    d["calendar"] = {"ics_url": str(payload.ics_url)}
    _write(d)
    return {"ok": True, "calendar": {"ics_masked": _mask_ics(str(payload.ics_url))}}

