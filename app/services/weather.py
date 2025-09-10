import httpx
from typing import Optional, Dict, Any

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

def _geocode(city_or_zip: str) -> Optional[Dict[str, float]]:
    params = {"name": city_or_zip, "count": 1, "language": "en", "format": "json"}
    try:
        r = httpx.get(GEOCODE_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("results"):
            return None
        res = data["results"][0]
        return {"lat": float(res["latitude"]), "lon": float(res["longitude"])}
    except Exception:
        return None

def get_weather_summary(home: Dict[str, Any]) -> Optional[str]:
    """
    Returns a lightweight weather string like:
    '66°F now, H 72° / L 60°, 10% precip'
    """
    if not home:
        return None

    units = (home.get("units") or "imperial").lower()
    tz = home.get("tz") or "UTC"

    lat = home.get("lat")
    lon = home.get("lon")
    if not (lat and lon):
        city_or_zip = home.get("city") or home.get("zip")
        if not city_or_zip:
            return None
        loc = _geocode(str(city_or_zip))
        if not loc:
            return None
        lat, lon = loc["lat"], loc["lon"]

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": tz,
    }
    if units == "imperial":
        params["temperature_unit"] = "fahrenheit"

    try:
        r = httpx.get(WEATHER_URL, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        current = j.get("current", {})
        daily = j.get("daily", {})
        temp_now = current.get("temperature_2m")
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        pprob = (daily.get("precipitation_probability_max") or [0])[0]
        if temp_now is None or tmax is None or tmin is None:
            return None
        deg = "°F" if units == "imperial" else "°C"
        return f"{round(temp_now)}{deg} now, H {round(tmax)}{deg} / L {round(tmin)}{deg}, {int(pprob)}% precip"
    except Exception:
        return None
