from typing import List, Dict
from ..config import settings
from datetime import datetime
try:
    from openai import OpenAI
    _client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
except Exception:
    _client = None

def generate_quiz_from_notes(notes: str, difficulty: str = "mixed") -> List[Dict]:
    # If no OpenAI key, return a safe, static quiz
    if not _client:
        return [
            {"question":"Name the process that converts glucose to ATP in the cytoplasm.",
             "answer":"Glycolysis", "explanation":"First step of cellular respiration.", "page_ref":None},
            {"question":"Which law explains constant acceleration due to net force?",
             "choices":["Newton's 1st","Newton's 2nd","Newton's 3rd"], "answer":"Newton's 2nd",
             "explanation":"F=ma.", "page_ref":None},
        ]
    # Otherwise, call the model for generation
    prompt = f"""Create 6 retrieval questions (mix MCQ + short answers) from the notes below.
    Return JSON list with fields: question, choices(optional), answer, explanation, page_ref.
    Difficulty: {difficulty}.
    Notes:
    {notes}
    """
    resp = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"You are a helpful study assistant. Keep questions factual."},
                  {"role":"user","content":prompt}],
        temperature=0.2,
    )
    import json
    try:
        data = json.loads(resp.choices[0].message.content)
        return data
    except Exception:
        return [{"question":"What is photosynthesis?","answer":"Process converting light energy to chemical energy in plants."}]
