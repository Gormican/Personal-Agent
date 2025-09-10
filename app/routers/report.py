from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, io

router = APIRouter(prefix="/report", tags=["report"])

# ---- Prefs storage (same file used by prefs.py) ----
DATA_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json")
)

def _load_prefs() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"topics": [], "home": {}, "calendar": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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
    # Accept multiple possible keys to match how it may have been saved
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

    lines = [
        f"Good morning. Here’s your report for { _today_str(tz) }.",
        "Your calendar is connected." if _calendar_connected(cal) else "No calendar connected yet.",
        f"Weather for {place}: details unavailable right now ({'metric' if units=='metric' else 'imperial'}).",
        "Your topics: " + ", ".join(topics) + "." if topics else "No news topics saved yet.",
        "",
        "(Note: smart summary unavailable.)",
    ]
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
        # Import inside so a missing package won’t block router registration
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # NOTE: no `format=` argument; current SDK defaults to WAV bytes.
        # If you later want MP3, we can use the Responses API audio block or re-encode server-side.
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio_bytes = speech.read()

    except ImportError:
        raise HTTPException(status_code=500, detail="OpenAI client not installed on server.")
    except Exception as e:
        # Surface exact TTS errors (e.g., quota, wrong arg) back to UI
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    # Serve as WAV since that's the SDK's default output
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'inline; filename="morning.wav"',
            "Cache-Control": "no-store",
        },
    )
