from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers.news import router as news_router
from routers.prefs import router as prefs_router

app = FastAPI()
from fastapi.responses import RedirectResponse, PlainTextResponse

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui")

@app.head("/", include_in_schema=False)
def home_head():
    return PlainTextResponse("")

@app.get("/")
def root():
    return {"ok": True, "msg": "G'day from FastAPI"}

app.include_router(news_router)
app.include_router(prefs_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/ui")
def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

