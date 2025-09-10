from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, io

from ..services.weather import get_weather_summary
from ..services.calendar import get_today_events

router = APIRouter(prefix="/report", tags=["report"])

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json"))

def _load_prefs() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"topics": [], "home": {}, "calendar": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"topics": [], "home": {}, "calendar": {}}

def _today_str(tz: str | None) -> str:
    try:
        if tz:
            return datetime.now(ZoneInfo(tz)).strftime("%A, %B %d")
    except Exception:
        pass
    return datetime.now().strftime("%A, %B %d")

def _calendar_connected(cal: Dict[str, Any]) -> bool:
    if not cal:
        return False
    for k in ("ics_url", "url", "ics", "calendar_url"):
        v = cal.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False

def _build_morning_text(prefs: Dict[str, Any]) -> str:
    home = prefs.get("home", {}) or {}
    cal  = prefs.get("calendar", {}) or {}
    topics = prefs.get("topics", []) or []

    tz = home.get("tz")
    units = (home.get("units") or "imperial").lower()
    place = home.get("city") or (f"ZIP {home.get('zip')}" if home.get("zip") else "your area")

    weather_s = get_weather_summary(home)
    cal_lines = get_today_events(cal, tz)

    lines = [f"Good morning. Here’s your report for { _today_str(tz) }."]
    # Calendar
    if _calendar_connected(cal):
        if cal_lines:
            lines.append("Today’s calendar:")
            lines.extend([f"• {x}" for x in cal_lines])
        else:
            lines.append("Your calendar is connected (no events today).")
    else:
        lines.append("No calendar connected yet.")

    # Weather
    if weather_s:
        lines.append(f"Weather for {place}: {weather_s}.")
    else:
        lines.append(f"Weather for {place}: unavailable right now ({'metric' if units=='metric' else 'imperial'}).")

    # Topics
    if topics:
        lines.append("Your topics: " + ", ".join(topics) + ".")
    else:
        lines.append("No news topics saved yet.")

    lines += ["", "(Note: smart summary unavailable.)"]
    return "\n".join(lines).strip()

@router.get("/morning")
def morning(smart: bool = True):
    prefs = _load_prefs()
    text = _build_morning_text(prefs)
    return {"text": text}

@router.get("/morning/speak")
def morning_speak(smart: bool = True):
    prefs = _load_prefs()
    text = _build_morning_text(prefs)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="TTS requires OPENAI_API_KEY.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # current SDK: no format kw; returns WAV bytes
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio_bytes = speech.read()

    except ImportError:
        raise HTTPException(status_code=500, detail="OpenAI client not installed on server.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'inline; filename="morning.wav"',
            "Cache-Control": "no-store",
        },
    )

