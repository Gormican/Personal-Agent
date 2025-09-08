# routers/study.py
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Load env if using Secret File on Render (and local .env during dev)
try:
    from dotenv import load_dotenv  # python-dotenv==1.0.1
    load_dotenv()
    load_dotenv("/etc/secrets/.env")
except Exception:
    pass

from openai import OpenAI
# optional specific errors (SDK v1.x)
try:
    from openai import (
        RateLimitError,
        APIError,
        APIConnectionError,
        AuthenticationError,
        BadRequestError,
    )
except Exception:
    RateLimitError = APIError = APIConnectionError = AuthenticationError = BadRequestError = Exception  # type: ignore

router = APIRouter(prefix="/study", tags=["study"])

# ---------- models ----------
class QuestionIn(BaseModel):
    question: str = Field(..., min_length=3)
    level: Optional[str] = None
    format: Optional[str] = None

class AnswerOut(BaseModel):
    answer: str

# ---------- helper ----------
def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("OAI_API_KEY")
    if not key:
        raise HTTPException(500, "OpenAI key not configured. Set OPENAI_API_KEY.")
    return OpenAI(api_key=key)

# ---------- routes ----------
@router.post("/ask", response_model=AnswerOut)
def ask(q: QuestionIn) -> AnswerOut:
    client = _get_client()

    system = (
        "You are a concise, evidence-aware clinical study assistant. "
        "Answer in 2–5 bullet points. If there is uncertainty or a safety issue, say so."
    )
    extras = []
    if q.level:  extras.append(f"Target level: {q.level}.")
    if q.format: extras.append(f"Preferred format: {q.format}.")
    prompt = "\n".join([q.question] + extras)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise HTTPException(502, "OpenAI returned an empty response.")
        return AnswerOut(answer=text)
    except RateLimitError:
        raise HTTPException(429, "OpenAI quota exceeded. Check billing/limits.")
    except AuthenticationError:
        raise HTTPException(401, "OpenAI auth failed. Check OPENAI_API_KEY.")
    except BadRequestError as e:
        raise HTTPException(400, f"OpenAI bad request: {e}")
    except APIConnectionError as e:
        raise HTTPException(502, f"OpenAI connection error: {e}")
    except APIError as e:
        raise HTTPException(502, f"OpenAI API error: {e}")
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")

# Optional status endpoint (debug)
@router.get("/status", include_in_schema=False)
def status():
    return {"openai_key_present": bool(os.getenv("OPENAI_API_KEY") or os.getenv("OAI_API_KEY"))}


