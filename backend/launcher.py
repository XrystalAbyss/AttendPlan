"""AttendPlan Windows Desktop Application Launcher.

Initializes the local-first AttendPlan server, mounts the production frontend,
and opens the application in a unified, dedicated Chromium profile.
"""

from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

# Add backend directory to sys.path if running from source
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

APP_VERSION = "0.1.0-beta.5"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Global shutdown event triggered by API or keyboard interrupt
SHUTDOWN_EVENT = threading.Event()


def safe_print(*args: Any, **kwargs: Any) -> None:
    """Print safely without raising when stdout is None in Windows windowed mode."""
    if sys.stdout is not None and hasattr(sys.stdout, "write"):
        try:
            print(*args, **kwargs)
        except Exception:
            pass


def setup_desktop_logging() -> logging.Logger:
    """Set up rotating desktop log file in %LOCALAPPDATA%/AttendPlan/logs/."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        log_dir = Path(local_app_data) / "AttendPlan" / "logs"
    else:
        log_dir = Path.home() / ".attendplan" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "attendplan.log"

    logger = logging.getLogger("attendplan")
    logger.setLevel(logging.INFO)

    # Clear existing handlers if re-initializing
    logger.handlers.clear()

    # Rotating file handler (5 MB max, 3 backups)
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler only if stdout is available (e.g. running from terminal)
    if sys.stdout is not None and hasattr(sys.stdout, "write"):
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(file_formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass

    return logger


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a TCP port is in use or cannot be bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        if s.connect_ex((host, port)) == 0:
            return True

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(host: str, preferred_port: int = DEFAULT_PORT, max_port: int = 8010) -> int:
    """Find a port that is free or already running AttendPlan."""
    if is_server_healthy(host, preferred_port):
        return preferred_port
    if not is_port_in_use(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, max_port + 1):
        if is_server_healthy(host, port):
            return port
        if not is_port_in_use(host, port):
            return port

    return preferred_port


def is_server_healthy(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Check if AttendPlan API is responsive on the loopback address."""
    url = f"http://{host}:{port}/api/v1/startup/status"
    try:
        req = urllib.request.Request(url, method="GET")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_seconds: float = 15.0,
) -> bool:
    """Poll loopback until AttendPlan responds or timeout expires."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_server_healthy(host, port):
            return True
        time.sleep(0.2)
    return False


def launch_unified_browser(
    target_url: str,
    logger: logging.Logger,
    allow_default_browser: bool = False,
) -> dict[str, Any]:
    """Open AttendPlan in dedicated Chromium profile, creating unified multi-tab experience."""
    try:
        from app.adapters.portal_session import (
            find_chrome_executable,
            get_dedicated_profile_dir,
            PortalSessionManager,
        )

        manager = PortalSessionManager()
        if manager.is_cdp_reachable():
            logger.info("Managed Chromium already active on loopback CDP; opening/focusing dashboard tab...")
            if manager.open_or_focus_tab(target_url):
                return {"success": True, "mode": "cdp_existing_tab"}

        chrome_exe = find_chrome_executable()
        if chrome_exe:
            profile_dir = get_dedicated_profile_dir()
            cdp_port = manager.find_working_cdp_port()
            cmd = [
                chrome_exe,
                f"--remote-debugging-port={cdp_port}",
                "--remote-debugging-address=127.0.0.1",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                target_url,
            ]
            flags = 0
            if sys.platform == "win32":
                import subprocess
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(
                    cmd,
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                import subprocess
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            logger.info("Launched unified Chromium profile with dashboard at %s", target_url)
            return {"success": True, "mode": "chromium_process"}
    except Exception as exc:
        logger.warning(
            "Could not launch dedicated Chromium browser: %s.",
            exc,
        )

    if allow_default_browser:
        logger.info("Opening system default browser to %s (--open-default-browser passed)", target_url)
        webbrowser.open(target_url)
        return {"success": True, "mode": "system_default_browser"}

    guidance = (
        "No compatible Chromium-based browser (Chrome, Edge, Brave) was found on loopback. "
        "Install Google Chrome or Microsoft Edge for the best experience, or pass --open-default-browser to launch in your default browser."
    )
    logger.warning("Chromium executable not detected and --open-default-browser not specified. Did not launch system browser.")
    return {
        "success": False,
        "mode": "none",
        "guidance": guidance,
    }


def run_launcher() -> int:
    parser = argparse.ArgumentParser(
        description="AttendPlan — Local-First University Attendance Intelligence"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Loopback port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"Loopback host to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without opening the web browser",
    )
    parser.add_argument(
        "--open-default-browser",
        action="store_true",
        help="Allow falling back to the system default browser if Chromium is not found",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version information and exit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check if an AttendPlan instance is already running",
    )

    args = parser.parse_args()

    if args.version:
        safe_print(f"AttendPlan {APP_VERSION}")
        return 0

    logger = setup_desktop_logging()
    logger.info("AttendPlan Desktop Launcher initializing (v%s)", APP_VERSION)

    target_port = args.port

    # Single-instance check
    if is_server_healthy(args.host, target_port):
        logger.info(
            "An existing AttendPlan instance is already running on http://%s:%d",
            args.host,
            target_port,
        )
        if args.status:
            safe_print(f"AttendPlan is RUNNING on http://{args.host}:{target_port}")
            return 0

        if not args.no_browser:
            logger.info("Focusing/opening unified browser to existing instance...")
            launch_unified_browser(
                f"http://{args.host}:{target_port}/",
                logger,
                allow_default_browser=args.open_default_browser,
            )
        safe_print(f"AttendPlan is already running at http://{args.host}:{target_port}/")
        return 0

    # If target port is occupied by another application, find alternative port
    if is_port_in_use(args.host, target_port):
        logger.warning(
            "Port %d on %s is occupied by an external application.",
            target_port,
            args.host,
        )
        fallback_port = find_available_port(args.host, preferred_port=target_port)
        if fallback_port != target_port:
            logger.info("Selected alternative loopback port %d", fallback_port)
            target_port = fallback_port
        elif is_port_in_use(args.host, target_port) and not is_server_healthy(args.host, target_port):
            logger.error("All loopback ports in range %d-8010 are occupied by external applications.", target_port)
            safe_print(f"ERROR: AttendPlan could not find an available loopback port (checked {target_port}-8010).")
            return 1

    if args.status:
        safe_print(f"AttendPlan is NOT running on http://{args.host}:{target_port}")
        return 1

    # Import application components inside launcher
    import uvicorn
    from app.main import app

    server_config = uvicorn.Config(
        app=app,
        host=args.host,
        port=target_port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(server_config)

    def trigger_shutdown() -> None:
        SHUTDOWN_EVENT.set()
        server.should_exit = True

    app.state.trigger_shutdown = trigger_shutdown
    app.state.shutdown_event = SHUTDOWN_EVENT

    # Run Uvicorn server in a separate daemon thread
    server_thread = threading.Thread(
        target=server.run,
        daemon=True,
        name="attendplan-uvicorn-server",
    )
    server_thread.start()
    logger.info("Uvicorn background server thread started on http://%s:%d", args.host, target_port)

    # Wait for the server to be ready
    if not wait_for_server(args.host, target_port, timeout_seconds=15.0):
        logger.error("Timed out waiting for AttendPlan server to start on port %d", target_port)
        safe_print("ERROR: AttendPlan failed to start within 15 seconds.")
        return 1

    target_url = f"http://{args.host}:{target_port}/"
    logger.info("AttendPlan server is healthy at %s", target_url)
    safe_print("=" * 60)
    safe_print(f" AttendPlan — University Attendance Intelligence (v{APP_VERSION})")
    safe_print(f" Running locally at: {target_url}")
    safe_print("=" * 60)

    if not args.no_browser:
        launch_res = launch_unified_browser(
            target_url,
            logger,
            allow_default_browser=args.open_default_browser,
        )
        if not launch_res.get("success"):
            safe_print(f"NOTE: {launch_res.get('guidance')}")
            safe_print(f"You can open {target_url} manually in your browser.")

    # Keep main thread alive until shutdown event or user interruption
    try:
        while server_thread.is_alive() and not SHUTDOWN_EVENT.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (Ctrl+C).")
    finally:
        logger.info("Stopping AttendPlan server...")
        server.should_exit = True
        server_thread.join(timeout=3.0)
        logger.info("AttendPlan stopped cleanly.")

    return 0


if __name__ == "__main__":
    sys.exit(run_launcher())
