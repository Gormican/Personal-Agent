# app/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Personal Agent")

# ---------- Static & templates ----------
BASE_DIR = os.path.dirname(__file__)

static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

# ---------- Routers (optional imports so we don't crash) ----------
def _try_include(module_path: str, attr: str = "router") -> None:
    try:
        module = __import__(module_path, fromlist=[attr])
        app.include_router(getattr(module, attr))
    except Exception:
        # If a router doesn't exist or fails to import, skip quietly.
        pass

_try_include("routers.news")
_try_include("routers.prefs")
_try_include("routers.study")
_try_include("routers.report")

# ---------- Basic routes ----------
@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/ui")

@app.head("/", include_in_schema=False)
def home_head():
    return PlainTextResponse("")

@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def ui(request: Request):
    # index.html should live in app/templates/
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz", tags=["default"])
def healthz():
    return {"status": "ok"}
