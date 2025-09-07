from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os, json

router = APIRouter(prefix="/prefs", tags=["prefs"])

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prefs.json"))

class NewsPrefsIn(BaseModel):
    topics: List[str] = []

def _ensure_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"topics": []}, f)

def _read() -> dict:
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(d: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

@router.get("/news", response_model=NewsPrefsIn)
def get_news_prefs():
    return NewsPrefsIn(**_read())

@router.post("/news", response_model=NewsPrefsIn)
def set_news_prefs(prefs: NewsPrefsIn):
    _write(prefs.dict())
    return prefs
