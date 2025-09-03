from fastapi import FastAPI
from .db import init_db
from .routers import morning, goals, tasks, study, metrics, prefs

app = FastAPI(title="Student AI CoS", version="0.1.0")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(morning.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(study.router)
app.include_router(metrics.router)
app.include_router(prefs.router)
