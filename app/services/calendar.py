from typing import Dict, Any, List
import httpx
from ics import Calendar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def _today_window(tz_str: str | None):
    try:
        tz = ZoneInfo(tz_str) if tz_str else timezone.utc
    except Exception:
        tz = timezone.utc
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59)
    return start, end, tz

def get_today_events(cal: Dict[str, Any], tz_str: str | None) -> List[str]:
    url = (cal or {}).get("ics_url") or (cal or {}).get("url")
    if not url:
        return []
    try:
        r = httpx.get(url, timeout=15)
        r.raise_for_status()
        c = Calendar(r.text)
    except Exception:
        return []

    start, end, tz = _today_window(tz_str)
    items = []
    for ev in c.events:
        try:
            # ics uses arrow; get datetimes
            begin = ev.begin.to("UTC").naive.replace(tzinfo=timezone.utc).astimezone(tz)
            if not (start <= begin <= end):
                continue
            t = begin.strftime("%-I:%M %p") if hasattr(begin, "strftime") else str(begin)
            items.append(f"{t} — {ev.name}")
        except Exception:
            continue
    return sorted(items)[:6]
