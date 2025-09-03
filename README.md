# Student AI Chief‑of‑Staff (AI CoS) — Starter

FastAPI starter for a student-focused AI Chief‑of‑Staff with daily **Morning Report**, **Goal cascade**, **Study drills**, and **Reminders**.

## Stack
- FastAPI, Uvicorn
- SQLAlchemy (SQLite by default)
- OpenAI (optional)
- ChromaDB (stubbed hook)
- APScheduler for optional jobs

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (optional) copy env and set your keys
cp .env.example .env
# edit .env to set OPENAI_API_KEY if you want LLM quiz generation

# run
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/docs

## Example usage (once server is running)
```bash
# set news topics
curl -X POST http://127.0.0.1:8000/prefs/news -H "Content-Type: application/json"   -d '{"topics": ["Taylor Swift", "Padres", "Science Fair"]}'

# add a goal
curl -X POST http://127.0.0.1:8000/goals -H "Content-Type: application/json"   -d '{"level":"year","title":"Ace AP Bio","metric":"exam_score","target":5,"deadline":"2026-05-15"}'

# quick task
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json"   -d '{"title":"Finish lab outline","due":"2025-09-05","estimate_min":30}'

# morning report
curl http://127.0.0.1:8000/morning
```

## Environment variables
See `.env.example`. If `OPENAI_API_KEY` is not set, the app will use safe placeholders.

## Project layout
```
app/
  main.py            # app entry
  config.py          # env config
  db.py              # SQLAlchemy Base/engine/session
  models.py          # ORM models
  schemas.py         # Pydantic schemas
  routers/           # API routes
  services/          # calendar, weather, news, planner, study
  utils/             # helpers (time)
```

## Notes
- This is school‑safe: no essay writing; only outlines/feedback in study flow (enforced in code path).
- Replace placeholder integrations in `services/` with real calendar, weather, and news sources approved by your school.
