# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for AttendPlan Windows Desktop Application.

Packages the FastAPI backend, pure calculation engines, Playwright adapter,
and compiled Vite React frontend into a self-contained Windows application directory.
"""

from pathlib import Path
import sys

block_cipher = None

# Root paths
SPEC_DIR = Path(SPECPATH).resolve()
REPO_ROOT = SPEC_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
FIXTURES_DIR = BACKEND_DIR / "app" / "fixtures"

# Collect datas
datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend_dist"))
if FIXTURES_DIR.exists():
    datas.append((str(FIXTURES_DIR), "app/fixtures"))

# Hidden imports required for Uvicorn, FastAPI, SQLAlchemy, and Keyring
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "starlette",
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.middleware.trustedhost",
    "fastapi",
    "fastapi.routing",
    "fastapi.staticfiles",
    "fastapi.responses",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "fastapi.middleware.trustedhost",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "sqlalchemy.orm",
    "sqlalchemy.sql.default_comparator",
    "keyring",
    "keyring.backends",
    "keyring.backends.Windows",
    "playwright",
    "playwright.sync_api",
    "bs4",
    "pyotp",
    "pydantic",
    "sqlite3",
]

a = Analysis(
    [str(BACKEND_DIR / "launcher.py")],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email.test",
        "test",
        "pytest",
        "matplotlib",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AttendPlan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AttendPlan",
)
