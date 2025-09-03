from fastapi import APIRouter
from ..schemas import QuizOut, QuizQ
from ..services.study import generate_quiz_from_notes

router = APIRouter()

@router.post("/study/quiz", response_model=QuizOut)
def quiz(notes: str, difficulty: str = "mixed"):
    qs_raw = generate_quiz_from_notes(notes, difficulty)
    qs = []
    for q in qs_raw:
        qs.append(QuizQ(**{k:v for k,v in q.items() if k in {"question","choices","answer","explanation","page_ref"}}))
    return {"questions": qs}
