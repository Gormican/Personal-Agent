from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# --- app first ---
app = FastAPI()

# --- paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# --- root + Render HEAD probe ---
@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/ui")

@app.head("/", include_in_schema=False)
def home_head():
    return PlainTextResponse("")

# --- routers (import after app exists) ---
from routers.news import router as news_router
from routers.prefs import router as prefs_router
from routers.study import router as study_router
from routers.report import router as report_router

app.include_router(news_router)
app.include_router(prefs_router)
app.include_router(study_router)
app.include_router(report_router)

# --- UI + health ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/ui")
def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


