from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Task, User
from ..schemas import TaskIn, TaskOut

router = APIRouter()

def current_user_id(): return 1

@router.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskIn, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        user = User(id=user_id, name="Demo"); db.add(user); db.commit()
    t = Task(user_id=user_id, goal_id=payload.goal_id, title=payload.title, due=payload.due, estimate_min=payload.estimate_min, status="todo")
    db.add(t); db.commit(); db.refresh(t)
    return t
