# routers/report.py
from __future__ import annotations
import os, json
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote_plus

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import feedparser
import httpx

# reuse OpenAI helper + prefs
try:
    from routers.study import _get_client
except Exception:
    _get_client = None

from routers.prefs import get_news_prefs

# timezone formatting (nice local date if tz provided)
try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None  # fallback

router = APIRouter(prefix="/report", tags=["report"])

# ---------- helpers ----------
def _local_today_str(tz: Optional[str]) -> str:
    dt = datetime.now()
    if tz and ZoneInfo:
        try:
            dt = datetime.now(ZoneInfo(tz))
        except Exception:
            pass
    # weekday, Month day
    return dt.strftime("%A, %B %d")

def _fetch_headlines(topic: str, per: int) -> List[str]:
    url = f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    d = feedparser.parse(url)
    return [e.title for e in d.entries[:per]]

async def _fetch_weather(lat: Optional[float], lon: Optional[float], tz: Optional[str]) -> Optional[str]:
    """
    Uses Open-Meteo daily forecast. If no lat/lon provided, returns None.
    """
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
        daily = j.get("daily", {})
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        pops = daily.get("precipitation_probability_max", [])
        if not highs or not lows:
            return None
        hi = round(highs[0])
        lo = round(lows[0])
        pop = (pops[0] if pops else 0)
        return f"Weather: high {hi}°, low {lo}°, rain {pop}%."
    except Exception:
        return None  # fail quietly for now

def _schedule_stub() -> Optional[str]:
    """
    Placeholder: return None (no calendar yet).
    Later we’ll swap this to Google Calendar/ICS.
    """
    # You can temporarily set a one-line summary via env if you like:
    # e.g., REPORT_SCHEDULE_TODAY="09:00 Clinic; 12:30 Lunch with Sara"
    s = os.getenv("REPORT_SCHEDULE_TODAY")
    return s.strip() if s else None

async def _build_script(smart: bool, per: int, lat: Optional[float], lon: Optional[float], tz: Optional[str]) -> str:
    lines: List[str] = []
    lines.append(f"Good morning. Here’s your report for { _local_today_str(tz) }.")

    # Schedule (stub / optional)
    sched = _schedule_stub()
    lines.append(sched if sched else "No calendar connected yet.")

    # Weather (optional)
    w = await _fetch_weather(lat, lon, tz)
    if w: lines.append(w)

    # News (from your saved topics)
    prefs = get_news_prefs()  # pydantic model with .topics
    topics = (prefs.topics or []) if hasattr(prefs, "topics") else []
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

    # Optional: smart summary via OpenAI
    if smart:
        if _get_client is None:
            # still speak the raw script
            return script + "\n\n(Note: smart summary unavailable.)"
        try:
            client = _get_client()
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

    if _get_client is None:
        raise HTTPException(500, "TTS requires OpenAI client.")
    client = _get_client()
    voice = os.getenv("TTS_VOICE", "alloy")
    model = os.getenv("TTS_MODEL", "tts-1")  # try 'gpt-4o-mini-tts' later if enabled
    r = client.audio.speech.create(model=model, voice=voice, input=text)

    def gen():
        yield r.read()

    return StreamingResponse(gen(), media_type="audio/mpeg")
