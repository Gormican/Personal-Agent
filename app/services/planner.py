from sqlalchemy.orm import Session
from ..models import Task

def suggest_top3_priorities(db: Session, user_id: int):
    # Naive: next 3 due tasks not done
    q = (db.query(Task)
           .filter(Task.user_id==user_id, Task.status!="done")
           .order_by(Task.due.is_(None), Task.due.asc()))
    items = q.limit(3).all()
    return [t.title for t in items] or ["Review notes 25 min", "Finish math problem set", "Prep lab outline"]
