@echo off
call .\.venv\Scripts\activate
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload