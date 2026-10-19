"""Main FastAPI application entry point for AttendPlan.

Runs strictly as a local-first service bound to 127.0.0.1.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import router
from app.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on startup
    init_db()
    yield

app = FastAPI(
    title="AttendPlan API",
    description="Local-first university attendance intelligence application API",
    version="0.2.0-F1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Allow local frontend development servers
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    # Non-negotiable boundary: Local-only API, binding to 127.0.0.1 rather than 0.0.0.0
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
