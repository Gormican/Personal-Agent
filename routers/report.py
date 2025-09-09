# routers/report.py
from __future__ import annotations
import os
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote_plus

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import feedparser
import httpx

# Calendar parsing
from ics import Calendar

# Reuse OpenAI client if available; fallback locally
try:
    from routers.study import _get_client as study_get_client
except Exception:
    study_get_client = None

try:
    from dotenv import load_dotenv
    load_dotenv(); load_dotenv("/etc/secrets/.env")
except Exception:
    pass

def _local_get_client():
    try:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY") or os.getenv("OAI_API_KEY")
        return OpenAI(api_key=key) if key else None
    except Exception:
        return None

# Pull saved prefs
from routers.prefs import get_news_prefs, get_home_prefs, get_calendar_prefs

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

router = APIRouter(prefix="/report", tags=["report"])

# ---------- helpers ----------
def _local_today_str(tz: Optional[str]) -> str:
    dt = datetime.now()
    if tz and ZoneInfo:
        try:
            dt = datetime.now(ZoneInfo(tz))
        except Exception:
            pass
    return dt.strftime("%A, %B %d")

def _fetch_headlines(topic: str, per: int) -> List[str]:
    url = f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    d = feedparser.parse(url)
    return [e.title for e in d.entries[:per]]

async def _fetch_weather(lat: Optional[float], lon: Optional[float], tz: Optional[str]) -> Optional[str]:
    if lat is None or lon is None:
        return None
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1,
        "timezone": tz or "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            r.raise_for_status()
            j = r.json()
        d = j.get("daily", {})
        highs = d.get("temperature_2m_max", [])
        lows  = d.get("temperature_2m_min", [])
        pops  = d.get("precipitation_probability_max", [])
        if not highs or not lows:
            return None
        hi = round(highs[0]); lo = round(lows[0]); pop = (pops[0] if pops else 0)
        return f"Weather: high {hi}°, low {lo}°, rain {pop}%."
    except Exception:
        return None

async def _fetch_schedule_today(ics_url: Optional[str], tz: Optional[str]) -> Optional[List[str]]:
    """
    Return list like ["09:00: Clinic block", "12:30: Lunch w/ Sara"] for today.
    """
    if not ics_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(ics_url)
            r.raise_for_status()
            cal = Calendar(r.text)
    except Exception:
        return None

    # Determine 'today' in target timezone for comparison
    if tz and ZoneInfo:
        try:
            local_now = datetime.now(ZoneInfo(tz))
        except Exception:
            local_now = datetime.now()
    else:
        local_now = datetime.now()
    d0 = local_now.date()

    items: List[str] = []
    for e in cal.events:
        try:
            b = e.begin  # Arrow object
            if tz:
                b = b.to(tz)
            if b.date() == d0:
                tstr = b.format("HH:mm")
                title = e.name or "Untitled"
                loc = f" @ {e.location}" if getattr(e, "location", None) else ""
                items.append(f"{tstr}: {title}{loc}")
        except Exception:
            continue
    return items if items else None

async def _build_script(
    smart: bool, per: int,
    qlat: Optional[float], qlon: Optional[float], qtz: Optional[str]
) -> str:
    # Load saved prefs (ignore 404s)
    lat = qlat; lon = qlon; tz = qtz
    try:
        if lat is None or lon is None or tz is None:
            home = get_home_prefs()
            lat = lat if lat is not None else getattr(home, "lat", None)
            lon = lon if lon is not None else getattr(home, "lon", None)
            tz  = tz  if tz  is not None else getattr(home, "tz",  None)
    except Exception:
        pass

    # Intro
    lines: List[str] = [f"Good morning. Here’s your report for {_local_today_str(tz)}."]

    # Schedule
    ics_url = None
    try:
        ics = get_calendar_prefs()
        ics_url = getattr(ics, "ics_url", None)
    except Exception:
        pass
    sched = await _fetch_schedule_today(ics_url, tz)
    if sched:
        lines.append("Today:")
        lines.extend([f"• {s}" for s in sched])
    else:
        lines.append("No calendar connected yet.")

    # Weather
    w = await _fetch_weather(lat, lon, tz)
    if w: lines.append(w)

    # News
    prefs = get_news_prefs()
    topics = (getattr(prefs, "topics", None) or [])
    if topics:
        for t in topics:
            hs = _fetch_headlines(t, per)
            if not hs: 
                continue
            lines.append(f"{t}:")
            for h in hs:
                lines.append(f"• {h}")
    else:
        lines.append("No saved news topics yet. Add some on the Home page.")

    script = "\n".join(lines)

    # Smart summary (optional)
    if smart:
        client = (study_get_client() if callable(study_get_client) else _local_get_client())
        if not client:
            return script + "\n\n(Note: smart summary unavailable.)"
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Rewrite into a crisp 60–90 second spoken brief. Keep names, avoid fluff."},
                    {"role": "user",   "content": script},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or script
        except Exception:
            return script + "\n\n(Note: smart summary failed; reading headlines.)"
    return script

# ---------- endpoints ----------
@router.get("/morning")
async def morning(
    smart: bool = Query(False),
    per: int = Query(3, ge=1, le=5),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    tz: Optional[str] = Query(None),
):
    text = await _build_script(smart, per, lat, lon, tz)
    return {"text": text}

@router.get("/morning/speak")
async def morning_speak(
    smart: bool = Query(False),
    per: int = Query(3, ge=1, le=5),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    tz: Optional[str] = Query(None),
):
    text = await _build_script(smart, per, lat, lon, tz)
    if not text:
        raise HTTPException(400, "No report content.")

    client = (study_get_client() if callable(study_get_client) else _local_get_client())
    if client is None:
        raise HTTPException(500, "TTS requires OpenAI key. Set OPENAI_API_KEY or use a Secret File.")

    voice = os.getenv("TTS_VOICE", "alloy")
    model = os.getenv("TTS_MODEL", "tts-1")  # try 'gpt-4o-mini-tts' later if enabled
    r = client.audio.speech.create(model=model, voice=voice, input=text)

    def gen():
        yield r.read()

    return StreamingResponse(gen(), media_type="audio/mpeg")


