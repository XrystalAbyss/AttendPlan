"""AttendPlan Windows Desktop Application Launcher.

Initializes the local-first AttendPlan server, mounts the production frontend,
and opens the application in the student's default browser.
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Add backend directory to sys.path if running from source
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

APP_VERSION = "0.1.0-beta.3"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


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

    # File handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)

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
        help="Start the server without opening the default web browser",
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
        print(f"AttendPlan {APP_VERSION}")
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
            print(f"AttendPlan is RUNNING on http://{args.host}:{target_port}")
            return 0

        if not args.no_browser:
            logger.info("Opening browser to existing instance...")
            webbrowser.open(f"http://{args.host}:{target_port}/")
        print(f"AttendPlan is already running at http://{args.host}:{target_port}/")
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
            print(f"ERROR: AttendPlan could not find an available loopback port (checked {target_port}-8010).", file=sys.stderr)
            return 1

    if args.status:
        print(f"AttendPlan is NOT running on http://{args.host}:{target_port}")
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
        print("ERROR: AttendPlan failed to start within 15 seconds.", file=sys.stderr)
        return 1

    target_url = f"http://{args.host}:{target_port}/"
    logger.info("AttendPlan server is healthy at %s", target_url)
    print("=" * 60)
    print(f" AttendPlan — University Attendance Intelligence (v{APP_VERSION})")
    print(f" Running locally at: {target_url}")
    print(" Press Ctrl+C in this window to stop the application.")
    print("=" * 60)

    if not args.no_browser:
        logger.info("Opening default browser to %s", target_url)
        webbrowser.open(target_url)

    # Keep main thread alive until user interruption
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (Ctrl+C). Stopping server...")
        server.should_exit = True
        server_thread.join(timeout=3.0)
        logger.info("AttendPlan stopped cleanly.")

    return 0


if __name__ == "__main__":
    sys.exit(run_launcher())

