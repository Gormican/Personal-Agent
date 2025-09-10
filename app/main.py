from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ----- App -----
app = FastAPI(title="Personal Agent", version="1.0.0")

# ----- Paths -----
BASE_DIR = Path(__file__).resolve().parent          # .../app
REPO_ROOT = BASE_DIR.parent                         # repo root
TEMPLATES_DIR = REPO_ROOT / "templates"             # root/templates
STATIC_DIRS = [REPO_ROOT / "static", BASE_DIR / "static"]

# ----- Static -----
for cand in STATIC_DIRS:
    if cand.is_dir():
        app.mount("/static", StaticFiles(directory=str(cand)), name="static")
        break

# ----- Templates -----
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ----- Routers (no silent failures) -----
from .routers.prefs import router as prefs_router
app.include_router(prefs_router)

# Study helper endpoints
from .routers.study import router as study_router
app.include_router(study_router)

# Morning report + TTS
from .routers.report import router as report_router
app.include_router(report_router)

# ----- Root/UI/Health -----
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
        return HTMLResponse(
            f"<pre>Template not found at {index_path}</pre>", status_code=500
        )
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# ----- Optional path aliases (if any old UI calls them) -----
# Some earlier docs mention '/morning'; map them to the report router.
from fastapi import Depends
from .routers.report import morning as r_morning, morning_speak as r_morning_speak

@app.get("/morning", include_in_schema=False)
def morning_alias():
    return r_morning()

@app.get("/morning/speak", include_in_schema=False)
def morning_speak_alias():
    return r_morning_speak()
