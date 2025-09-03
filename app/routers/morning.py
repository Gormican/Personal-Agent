from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.calendar import get_today_calendar
from ..services.weather import get_weather_one_liner
from ..services.news import fetch_curated_news
from ..services.planner import suggest_top3_priorities
from ..utils.time import blocks_from_events
from ..schemas import MorningReport

router = APIRouter()

# For MVP we assume a single demo user with id=1
def current_user_id(): return 1

@router.get("/morning", response_model=MorningReport)
def morning_report(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    events = get_today_calendar(user_id)
    free_blocks = blocks_from_events(events)
    schedule = "\n".join([f"{s}-{e}  {t}" for s,e,t in events])
    wx = get_weather_one_liner()
    headlines = fetch_curated_news(db, user_id, limit=3)
    top3 = suggest_top3_priorities(db, user_id)
    return {
        "schedule": schedule,
        "free_blocks": free_blocks,
        "weather": wx,
        "headlines": headlines,
        "top3_priorities": top3
    }
