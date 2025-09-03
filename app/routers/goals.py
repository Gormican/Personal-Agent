from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Goal, User
from ..schemas import GoalIn, GoalOut

router = APIRouter()

def current_user_id(): return 1

@router.post("/goals", response_model=GoalOut)
def create_goal(payload: GoalIn, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    # ensure default user exists
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        user = User(id=user_id, email=None, name="Demo", tz="America/Los_Angeles")
        db.add(user); db.commit()
    g = Goal(
        user_id=user_id,
        parent_goal_id=payload.parent_goal_id,
        level=payload.level,
        title=payload.title,
        metric=payload.metric,
        target=payload.target,
        deadline=payload.deadline,
        weight=payload.weight,
        status="planned"
    )
    db.add(g); db.commit(); db.refresh(g)
    return g
