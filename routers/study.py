# routers/study.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()                      # load local .env if present
load_dotenv("/etc/secrets/.env")   # load Render secret file if present

router = APIRouter(prefix="/study", tags=["study"])

# Read API key from env (Render/Windows). If missing, we error nicely.
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None

class QuestionIn(BaseModel):
    question: str
    level: Optional[str] = None     # e.g., "med student", "resident", "board review"
    format: Optional[str] = None    # e.g., "bullets", "short answer", "flashcard"

class AnswerOut(BaseModel):
    answer: str

@router.post("/ask", response_model=AnswerOut)
def ask(q: QuestionIn):
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="OpenAI key not configured. Set environment variable OPENAI_API_KEY.",
        )

    system = (
        "You are a concise, evidence-aware clinical study assistant. "
        "Answer directly in plain English. Include 1–3 key points. "
        "If a topic is safety-critical or uncertain, say so."
    )
    extras = []
    if q.level:
        extras.append(f"Target level: {q.level}.")
    if q.format:
        extras.append(f"Preferred format: {q.format}.")
    prompt = "\n".join([q.question] + extras)

    # Cheap/fast model that’s still good
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400,
    )
    return {"answer": resp.choices[0].message.content.strip()}
