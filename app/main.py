# app/main.py
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Personal Agent")

BASE_DIR = Path(__file__).resolve().parent        # .../app
REPO_ROOT = BASE_DIR.parent                       # repo root
TEMPLATES_DIR = REPO_ROOT / "templates"           # root/templates

# ---- optional static (root/static preferred, else app/static) ----
for cand in (REPO_ROOT / "static", BASE_DIR / "static"):
    if cand.is_dir():
        app.mount("/static", StaticFiles(directory=str(cand)), name="static")
        break

# ---- templates (root/templates) ----
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---- routers (import from app.routers) ----
try:
    from .routers.prefs import router as prefs_router
    app.include_router(prefs_router)
except Exception:
    pass

try:
    from .routers.study import router as study_router
    app.include_router(study_router)
except Exception:
    pass

try:
    from .routers.report import router as report_router
    app.include_router(report_router)
except Exception:
    pass

try:
    from .routers.news import router as news_router
    app.include_router(news_router)
except Exception:
    pass

# ---- basic routes ----
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui")

@app.head("/", include_in_schema=False)
def root_head():
    return PlainTextResponse("")

@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def ui(request: Request):
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        msg = f"Template not found at {index_path}"
        return HTMLResponse(f"<pre>{msg}</pre>", status_code=500)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

