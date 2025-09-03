from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import get_db
from ..models import Task, Goal

router = APIRouter()

def current_user_id(): return 1

@router.get("/metrics/weekly")
def weekly_metrics(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    total = db.query(func.count(Task.id)).filter(Task.user_id==user_id).scalar() or 0
    done = db.query(func.count(Task.id)).filter(Task.user_id==user_id, Task.status=="done").scalar() or 0
    completion = (done/total) if total else 0.0
    return {"tasks_total": total, "tasks_done": done, "completion_ratio": round(completion,2)}
