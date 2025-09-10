from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter(prefix="/study", tags=["study"])

class AskIn(BaseModel):
    question: str

@router.post("/ask")
def ask(payload: AskIn):
    q = (payload.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question is empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # local, safe fallback
        return {
            "answer": (
                "I don’t have an API key configured, so here’s a structured way to study:\n"
                "1) Identify the key vocabulary/terms in the question.\n"
                "2) Write a 2–3 step outline of the mechanism or reasoning.\n"
                "3) State the final conclusion in one sentence.\n"
                "Enable OPENAI_API_KEY for AI-generated answers."
            )
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a study helper. Be concise and correct. Prefer outlines and bullet points."},
                {"role": "user", "content": q},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        text = resp.choices[0].message.content
        return {"answer": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Study helper error: {e}")
