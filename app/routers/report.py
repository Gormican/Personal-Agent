# app/routers/report.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from openai import OpenAI
import os, json, io

router = APIRouter(prefix="/report", tags=["report"])

# ---- prefs storage (same file used by prefs.py) ----
DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json"))

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

def _build_morning_text(prefs: Dict[str, Any]) -> str:
    home = prefs.get("home", {}) or {}
    cal  = prefs.get("calendar", {}) or {}
    topics = prefs.get("topics", []) or []

    tz = home.get("tz")
    units = home.get("units", "imperial")
    city = home.get("city")
    zipc = home.get("zip")

    date_line = f"Good morning. Here’s your report for { _today_str(tz) }."
    # Calendar
    if cal.get("ics_url"):
        cal_line = "Your calendar is connected."
    else:
        cal_line = "No calendar connected yet."

    # Weather (placeholder – we’re not hitting an external API here)
    place = city or (f"ZIP {zipc}" if zipc else "your area")
    if units == "metric":
        weather_line = f"Weather for {place}: details unavailable right now (metric)."
    else:
        weather_line = f"Weather for {place}: details unavailable right now (imperial)."

    # News (just list topics; your existing news endpoint can still be used elsewhere)
    if topics:
        topics_line = "Your topics: " + ", ".join(topics) + "."
    else:
        topics_line = "No news topics saved yet."

    # Summary note (placeholder)
    summary_line = "(Note: smart summary unavailable.)"

    return "\n".join([date_line, cal_line, weather_line, topics_line, "", summary_line]).strip()

# ---------- Endpoints ----------

@router.get("/morning")
def morning(smart: bool = True):
    """
    Compose a lightweight morning report using saved prefs.
    """
    prefs = _load_prefs()
    text = _build_morning_text(prefs)
    return {"text": text}

@router.get("/morning/speak")
def morning_speak(smart: bool = True):
    """
    Generate TTS (MP3) for the morning report text.
    Requires OPENAI_API_KEY to be configured (Render Secret or env var).
    """
    # Build text first (even if TTS fails, text endpoint works)
    prefs = _load_prefs()
    text = _build_morning_text(prefs)

    # Ensure the TTS client is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="TTS requires OPENAI_API_KEY.")

    try:
        client = OpenAI(api_key=api_key)
        # New TTS endpoint (v1.4x)
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            format="mp3",
        )
        audio_bytes = speech.read()  # get bytes
    except Exception as e:
        # Return a clear error but keep it 200 text path working separately
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="morning.mp3"',
            "Cache-Control": "no-store",
        },
    )

        key = os.getenv("OPENAI_API_KEY") or os.getenv("OAI_API_KEY")
        return OpenAI(api_key=key) if key else None
    except Exception:
        return None

from routers.prefs import get_news_prefs, get_home_prefs, get_calendar_prefs

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None

router = APIRouter(prefix="/report", tags=["report"])

# ----------------- helpers -----------------
def _local_today_and_bounds(tz: Optional[str]):
    """
    Returns (now_local, day_start, day_end, date_only) in the given timezone if provided.
    """
    now = datetime.now()
    if tz and ZoneInfo:
        try:
            z = ZoneInfo(tz)
            now = datetime.now(z)
        except Exception:
            pass
    date_only = now.date()
    start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=now.tzinfo)
    end = start + timedelta(days=1)
    return now, start, end, date_only

def _pretty_date_str(tz: Optional[str]) -> str:
    now, *_ = _local_today_and_bounds(tz)
    return now.strftime("%A, %B %d")

def _fetch_headlines(topic: str, per: int) -> List[str]:
    url = f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    d = feedparser.parse(url)
    return [e.title for e in d.entries[:per]]

async def _fetch_weather(lat: Optional[float], lon: Optional[float], tz: Optional[str]) -> Optional[str]:
    """
    Open-Meteo returns Celsius by default. Force Fahrenheit.
    """
    if lat is None or lon is None:
        return None
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1,
        "timezone": tz or "auto",
        "temperature_unit": "fahrenheit",   # << force °F
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
        return f"Weather: high {hi}°F, low {lo}°F, rain {pop}%."
    except Exception:
        return None

async def _fetch_schedule_today(ics_url: Optional[str], tz: Optional[str]) -> Optional[List[str]]:
    """
    Returns today's events as lines. Handles timed and all-day/multi-day events.
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

    now_local, day_start, day_end, date_only = _local_today_and_bounds(tz)
    items: List[str] = []

    for e in cal.events:
        try:
            b = e.begin  # Arrow
            # Convert to tz if provided
            if tz:
                b = b.to(tz)
            # End can be None; for all-day events, ics usually sets end to day after.
            e_end = getattr(e, "end", None)
            if e_end and tz:
                try:
                    e_end = e_end.to(tz)
                except Exception:
                    pass

            title = e.name or "Untitled"
            loc = f" @ {e.location}" if getattr(e, "location", None) else ""

            if getattr(e, "all_day", False):
                # All-day or multi-day: include if today's date is within [begin.date(), end.date())
                start_d = b.date()
                end_d = (e_end.date() if e_end else start_d)
                # Some calendars set end = next day for all-day; make inclusive of start only.
                if start_d <= date_only <= end_d:
                    # If event ends next day, it's still "today".
                    items.append(f"All-day: {title}{loc}")
            else:
                # Timed event: include if starts today (local)
                if b.date() == date_only:
                    tstr = b.format("HH:mm")
                    items.append(f"{tstr}: {title}{loc}")
        except Exception:
            continue

    return items if items else None

async def _build_script(
    smart: bool,
    per: int,
    qlat: Optional[float], qlon: Optional[float], qtz: Optional[str]
) -> str:
    # Home prefs fallback if lat/lon/tz not provided
    lat, lon, tz = qlat, qlon, qtz
    try:
        if lat is None or lon is None or tz is None:
            home = get_home_prefs()
            lat = lat if lat is not None else getattr(home, "lat", None)
            lon = lon if lon is not None else getattr(home, "lon", None)
            tz  = tz  if tz  is not None else getattr(home, "tz",  None)
    except Exception:
        pass

    lines: List[str] = [f"Good morning. Here’s your report for {_pretty_date_str(tz)}."]

    # Calendar
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
        lines.append("No calendar events for today.")

    # Weather
    w = await _fetch_weather(lat, lon, tz)
    if w:
        lines.append(w)

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

# ----------------- endpoints -----------------
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
    model = os.getenv("TTS_MODEL", "tts-1")
    r = client.audio.speech.create(model=model, voice=voice, input=text)
    def gen():
        yield r.read()
    return StreamingResponse(gen(), media_type="audio/mpeg")



