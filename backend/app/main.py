"""Main FastAPI application entry point for AttendPlan.

Runs strictly as a local-first service bound to 127.0.0.1.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.api.archive_routes import recover_interrupted, router as archive_router
from app.api.performance_routes import router as performance_router
from app.api.routes import router
from app.api.startup_routes import coordinator, router as startup_router
from app.db.session import init_db

def get_allowed_origins(app_state: Any = None) -> set[str]:
    """Calculate the strictly allowed origins for AttendPlan local API.

    In production mode:
      Only the dynamically bound loopback origin (e.g. http://127.0.0.1:<bound_port>,
      http://localhost:<bound_port>, and testserver for test suites) is permitted.
      Arbitrary or unrelated localhost ports (e.g. 8001 when server runs on 8000) are blocked.

    In development mode (ATTENDPLAN_ENV=development):
      Vite development server origins (ports 5173, 4173, 3000) are also permitted.
    """
    env = os.environ.get("ATTENDPLAN_ENV", "").lower()
    allowed = {"http://testserver", "https://testserver"}

    bound_port = getattr(app_state, "bound_port", None) if app_state else None
    if bound_port is not None:
        allowed.add(f"http://127.0.0.1:{bound_port}")
        allowed.add(f"http://localhost:{bound_port}")
    else:
        # Default fallback if bound_port is not yet set on app.state
        allowed.add("http://127.0.0.1:8000")
        allowed.add("http://localhost:8000")

    if env == "development":
        for p in (5173, 4173, 3000):
            allowed.add(f"http://localhost:{p}")
            allowed.add(f"http://127.0.0.1:{p}")

    return allowed


class LocalOriginSecurityMiddleware(BaseHTTPMiddleware):
    """Guards AttendPlan local API against cross-origin drive-by attacks and CSRF.

    Enforces that browser requests to /api/ originate strictly from authorized
    origins. Dynamically attaches CORS headers ONLY to explicitly authorized origins.
    """

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            sec_fetch_site = request.headers.get("sec-fetch-site")

            # Reject explicitly cross-site requests
            if sec_fetch_site and sec_fetch_site == "cross-site":
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin request blocked: cross-site access prohibited."},
                )

            app_state = getattr(request, "app", None).state if hasattr(request, "app") else None
            allowed_origins = get_allowed_origins(app_state)

            # Check Origin header if present
            if origin:
                clean_origin = origin.rstrip("/")
                if clean_origin not in allowed_origins:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin request blocked: origin not permitted."},
                    )

            # Check Referer header if present
            if referer:
                parts = urlsplit(referer)
                referer_origin = f"{parts.scheme}://{parts.netloc}".rstrip("/")
                if referer_origin not in allowed_origins:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin request blocked: referer not permitted."},
                    )

            # Handle CORS preflight OPTIONS request
            if request.method == "OPTIONS":
                if origin and origin.rstrip("/") in allowed_origins:
                    return Response(
                        status_code=200,
                        headers={
                            "Access-Control-Allow-Origin": origin,
                            "Access-Control-Allow-Credentials": "true",
                            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                            "Access-Control-Allow-Headers": request.headers.get(
                                "access-control-request-headers", "*"
                            ),
                            "Vary": "Origin",
                        },
                    )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin preflight blocked: origin not permitted."},
                )

            # Process request
            response = await call_next(request)

            # Add CORS headers strictly for authorized origin
            if origin and origin.rstrip("/") in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Vary"] = "Origin"

            return response

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on startup
    init_db()
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        recover_interrupted(db)
    coordinator.start()
    yield

app = FastAPI(
    title="AttendPlan API",
    description="Local-first university attendance intelligence application API",
    version="0.2.0-F1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enforce host header restriction against DNS rebinding attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "testserver"],
)

app.add_middleware(LocalOriginSecurityMiddleware)

app.include_router(router)
app.include_router(performance_router)
app.include_router(startup_router)
app.include_router(archive_router)


# Mount compiled frontend when available (production & packaged desktop mode)


def get_frontend_dist_dir() -> Path | None:
    """Resolve directory containing compiled frontend assets."""
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates = [
            base_dir / "frontend_dist",
            base_dir / "frontend" / "dist",
            base_dir / "dist",
        ]
        for c in candidates:
            if c.exists() and (c / "index.html").exists():
                return c
    else:
        dev_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
        if dev_dist.exists() and (dev_dist / "index.html").exists():
            return dev_dist
    return None


class SPAStaticFiles(StaticFiles):
    """Serve static files with index.html fallback for client-side single page app routing."""
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await super().get_response("index.html", scope)
            return response
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


frontend_dist = get_frontend_dist_dir()
if frontend_dist:
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    # Non-negotiable boundary: Local-only API, binding to 127.0.0.1 rather than 0.0.0.0
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
