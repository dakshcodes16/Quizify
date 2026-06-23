"""
FastAPI application entrypoint.
Run with: uvicorn api.main:app --reload --port 8000
Owns authentication (JWT) and exposes a REST surface for courses,
quizzes, and analytics. Streamlit calls the agent layer in-process
for the core adaptive-learning loop and calls this API for auth.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import init_db
from api.auth_routes import router as auth_router
from api.data_routes import router as data_router

app = FastAPI(
    title="Quizify API",
    description="Multi-agent adaptive learning platform — auth & data API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(data_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"status": "ok", "service": "Quizify API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
