from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, PlainTextResponse

from routers.news import router as news_router
from routers.prefs import router as prefs_router

app = FastAPI()

# --- robust paths for static/templates ---
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ---- default landing + Render HEAD probe ----
@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui")

@app.head("/", include_in_schema=False)
def home_head():
    return PlainTextResponse("")

# ---- routers ----
app.include_router(news_router)
app.include_router(prefs_router)

# ---- tiny UI + health ----
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/ui")
def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


