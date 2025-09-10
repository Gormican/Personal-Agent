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
        return {
            "answer": (
                "No API key configured, so here’s a quick study scaffold:\n"
                "• Identify terms and definitions.\n"
                "• Outline the mechanism or steps.\n"
                "• Conclude in one sentence.\n"
                "Set OPENAI_API_KEY to enable AI-generated answers."
            )
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a study helper. Be concise and correct. Prefer bullet points."},
                {"role": "user", "content": q},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return {"answer": resp.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Study helper error: {e}")

