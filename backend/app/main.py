"""Main FastAPI application entry point for AttendPlan.

Runs strictly as a local-first service bound to 127.0.0.1.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.api.archive_routes import recover_interrupted, router as archive_router
from app.api.performance_routes import router as performance_router
from app.api.routes import router
from app.api.startup_routes import coordinator, router as startup_router
from app.db.session import init_db

ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "testserver"}
ALLOWED_LOCAL_PORTS = {5173, 4173, 3000, *range(8000, 8011)}


class LocalOriginSecurityMiddleware(BaseHTTPMiddleware):
    """Guards AttendPlan local API against cross-origin drive-by attacks and CSRF.

    Verifies that requests to /api/ originating from web browsers come strictly from
    loopback addresses (127.0.0.1 / localhost) and authorized local ports.
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

            bound_port = getattr(request.app.state, "bound_port", None)
            allowed_ports = set(ALLOWED_LOCAL_PORTS)
            if bound_port is not None:
                allowed_ports.add(bound_port)

            # Check Origin header if present
            if origin:
                parts = urlsplit(origin)
                if parts.hostname not in ALLOWED_LOOPBACK_HOSTS:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin request blocked: origin not permitted."},
                    )
                if parts.port is not None and parts.port not in allowed_ports:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": f"Cross-origin request blocked: origin port {parts.port} not permitted."},
                    )

            # Check Referer header if present
            if referer:
                parts = urlsplit(referer)
                if parts.hostname not in ALLOWED_LOOPBACK_HOSTS:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin request blocked: referer not permitted."},
                    )
                if parts.port is not None and parts.port not in allowed_ports:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": f"Cross-origin request blocked: referer port {parts.port} not permitted."},
                    )

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

# Allow local frontend development servers and self-hosted loopback ports (8000-8010)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
] + [
    f"http://localhost:{p}" for p in range(8000, 8011)
] + [
    f"http://127.0.0.1:{p}" for p in range(8000, 8011)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
