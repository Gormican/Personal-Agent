from sqlalchemy.orm import Session
from ..models import NewsPref

def fetch_curated_news(db: Session, user_id: int, limit: int = 3):
    # Placeholder: use RSS/APIs approved by school; de-dupe and summarize.
    prefs = db.query(NewsPref).filter(NewsPref.user_id==user_id).all()
    topics = [p.topic for p in prefs] or ["Science Fair", "Local Sports", "Music"]
    headlines = [f"{t} — sample headline" for t in topics][:limit]
    return headlines
