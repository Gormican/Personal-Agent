from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import NewsPref, User
from ..schemas import NewsPrefsIn

router = APIRouter()

def current_user_id(): return 1

@router.post("/prefs/news")
def set_news_prefs(payload: NewsPrefsIn, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        user = User(id=user_id, name="Demo"); db.add(user); db.commit()
    db.query(NewsPref).filter(NewsPref.user_id==user_id).delete()
    for t in payload.topics:
        db.add(NewsPref(user_id=user_id, topic=t))
    db.commit()
    return {"ok": True, "topics": payload.topics}
