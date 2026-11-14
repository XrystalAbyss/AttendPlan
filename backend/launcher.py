"""AttendPlan Windows Desktop Application Launcher.

Initializes the local-first AttendPlan server, mounts the production frontend,
and opens the application in a unified, dedicated Chromium profile.
"""

from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
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

APP_VERSION = "0.1.0-beta.9"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Global shutdown event triggered by API or keyboard interrupt
SHUTDOWN_EVENT = threading.Event()
_APP_MUTEX_HANDLE: Any = None
ERROR_ALREADY_EXISTS = 183


def acquire_app_mutex() -> tuple[bool, bool]:
    """Acquire single-instance named Win32 mutex for Inno Setup and process tracking.

    Returns:
        tuple[bool, bool]: (is_owner, already_exists)
        - (True, False): Successfully created and owns the named mutex.
        - (False, True): Mutex already exists; another instance is running.
        - (False, False): System failure creating mutex.
        On non-Windows platforms, returns (True, False).
    """
    global _APP_MUTEX_HANDLE
    if sys.platform != "win32":
        return True, False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        mutex_name = "AttendPlanDesktopAppMutex"
        handle = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()

        if not handle:
            return False, False

        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False, True

        _APP_MUTEX_HANDLE = handle
        return True, False
    except Exception:
        return False, False


def release_app_mutex() -> None:
    """Cleanly close and release the Win32 named mutex."""
    global _APP_MUTEX_HANDLE
    if _APP_MUTEX_HANDLE and sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.CloseHandle(_APP_MUTEX_HANDLE)
        except Exception:
            pass
        _APP_MUTEX_HANDLE = None


def inspect_database_file(db_file: Path) -> int:
    """Perform integrity check and count academic entities in a SQLite database file."""
    import sqlite3

    if not db_file.exists():
        safe_print(f"ERROR: Database file does not exist at {db_file}")
        return 1
    safe_print(f"Database File: {db_file}")
    safe_print(f"File Size: {db_file.stat().st_size} bytes")
    try:
        conn = sqlite3.connect(str(db_file))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            integrity = cur.fetchall()
            safe_print(f"Integrity Check: {integrity}")
            if integrity != [("ok",)]:
                safe_print(f"ERROR: PRAGMA integrity_check failed: {integrity}")
                return 1

            tables = [
                row[0]
                for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            ]
            for t in [
                "academic_terms",
                "courses",
                "attendance_period_observations",
                "attendance_observation_batches",
                "attendance_snapshots",
                "attendance_snapshot_rows",
                "performance_snapshots",
            ]:
                if t in tables:
                    cnt = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                    safe_print(f"{t}: {cnt}")
                else:
                    safe_print(f"{t}: [table not present]")
        finally:
            conn.close()
    except (sqlite3.Error, Exception) as exc:
        safe_print(f"ERROR: SQLite database error during inspection: {exc}")
        return 1
    return 0


def perform_safe_backup(dest_path_str: str) -> int:
    """Create a verified SQLite online backup of the application database."""
    import hashlib
    import sqlite3
    from app.db.session import get_default_db_path

    db_path = get_default_db_path().resolve()
    if not db_path.exists():
        safe_print(f"ERROR: Source database not found at {db_path}")
        return 1

    dest = Path(dest_path_str).resolve()
    if dest == db_path:
        safe_print(f"ERROR: Destination path collision: source and destination are identical ({dest})")
        return 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        if not dest.exists() or dest.stat().st_size == 0:
            safe_print(f"ERROR: Backup file was not created or is zero bytes at {dest}")
            return 1

        # Verify backup integrity
        b_conn = sqlite3.connect(str(dest))
        try:
            b_cur = b_conn.cursor()
            b_cur.execute("PRAGMA integrity_check")
            b_integ = b_cur.fetchall()
            if b_integ != [("ok",)]:
                safe_print(f"ERROR: Backup failed PRAGMA integrity_check: {b_integ}")
                return 1

            # Compare record counts between source and backup
            s_conn = sqlite3.connect(str(db_path))
            s_cur = s_conn.cursor()
            try:
                for tbl in [
                    "academic_terms",
                    "courses",
                    "attendance_period_observations",
                    "performance_snapshots",
                ]:
                    s_cnt = s_cur.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
                    b_cnt = b_cur.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
                    if s_cnt != b_cnt:
                        safe_print(
                            f"ERROR: Record count mismatch in table {tbl}: source={s_cnt}, backup={b_cnt}"
                        )
                        return 1
            finally:
                s_conn.close()
        finally:
            b_conn.close()
    except (sqlite3.Error, Exception) as exc:
        safe_print(f"ERROR: Backup creation or verification failed: {exc}")
        return 1

    h = hashlib.sha256()
    with open(dest, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)

    safe_print(f"BACKUP_VERIFIED: {dest}")
    safe_print(f"SHA256: {h.hexdigest()}")
    safe_print(f"SIZE: {dest.stat().st_size} bytes")
    return 0


def purge_vault_only() -> int:
    """Revoke AttendPlan's MFA enrollment from Windows Credential Manager."""
    try:
        from app.services.totp_vault_service import TotpVaultService

        vault = TotpVaultService()
        if vault.is_enrolled():
            vault.remove_enrollment()
            safe_print("AttendPlan authenticator enrollment removed from Windows Credential Manager.")
        else:
            safe_print("No AttendPlan authenticator enrolled in Windows Credential Manager.")
        return 0
    except Exception as exc:
        safe_print(f"ERROR: Failed to purge vault: {exc}")
        return 1


def perform_safe_app_data_reset(backup_dest_str: str | None, confirm: str | None) -> int:
    """Safely reset local app data with verified backup, vault revocation, and allowlist deletion."""
    import shutil
    from app.db.session import get_default_db_path

    if confirm != "DELETE":
        safe_print("ERROR: Safety violation. --reset-app-data requires --confirm DELETE")
        return 1

    db_path = get_default_db_path().resolve()
    app_data_dir = db_path.parent.resolve()

    if not backup_dest_str:
        safe_print("ERROR: --reset-app-data requires a verified backup destination via --backup-dest")
        return 1

    backup_dest = Path(backup_dest_str).resolve()
    if backup_dest == db_path:
        safe_print(f"ERROR: Backup destination collides with source database ({backup_dest})")
        return 1

    try:
        if backup_dest.is_relative_to(app_data_dir):
            safe_print(f"ERROR: Backup destination cannot be inside the deletion scope ({app_data_dir})")
            return 1
    except AttributeError:
        if str(backup_dest).startswith(str(app_data_dir)):
            safe_print(f"ERROR: Backup destination cannot be inside the deletion scope ({app_data_dir})")
            return 1

    if db_path.exists():
        safe_print(f"Creating verified safety backup to {backup_dest} before data reset...")
        res = perform_safe_backup(str(backup_dest))
        if res != 0:
            safe_print("CRITICAL: Safety backup failed or failed integrity check. ABORTING RESET.")
            return 1

    try:
        purge_vault_only()
    except Exception as exc:
        safe_print(f"Warning during vault revocation: {exc}")

    ALLOWLIST_FILES = [
        "attendplan.sqlite3",
        "attendplan.sqlite3-wal",
        "attendplan.sqlite3-shm",
        "settings.json",
        "startup.json",
        "term_calendars.json",
        "totp_metadata.json",
    ]

    ALLOWLIST_DIRS = [
        "logs",
        "run",
        "chrome-profile",
    ]

    PROTECTED_DIRS = [
        "backups",
        "support_evidence",
    ]

    safe_print("Applying strict allowlist data cleanup...")
    deleted_items = []
    preserved_items = []

    for fname in ALLOWLIST_FILES:
        target = app_data_dir / fname
        if target.exists():
            try:
                target.unlink()
                deleted_items.append(str(target))
            except Exception as e:
                safe_print(f"Warning: could not delete {target}: {e}")

    for dname in ALLOWLIST_DIRS:
        target_dir = app_data_dir / dname
        if target_dir.exists() and target_dir.is_dir():
            try:
                shutil.rmtree(target_dir, ignore_errors=True)
                deleted_items.append(str(target_dir))
            except Exception as e:
                safe_print(f"Warning: could not delete directory {target_dir}: {e}")

    for pdir in PROTECTED_DIRS:
        ptarget = app_data_dir / pdir
        if ptarget.exists():
            preserved_items.append(str(ptarget))

    safe_print("=" * 60)
    safe_print("ATTENDPLAN APP DATA RESET COMPLETED SAFELY")
    safe_print(f"Verified Backup Preserved At: {backup_dest}")
    safe_print(f"Deleted Items ({len(deleted_items)}):")
    for it in deleted_items:
        safe_print(f"  - {it}")
    safe_print(f"Protected Security Evidence & Archives Preserved ({len(preserved_items)}):")
    for it in preserved_items:
        safe_print(f"  + {it}")
    safe_print("=" * 60)
    return 0


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
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Perform SQLite integrity check and inspect academic counts on default database, then exit",
    )
    parser.add_argument(
        "--check-db-file",
        type=str,
        metavar="PATH",
        help="Perform SQLite integrity check and inspect academic counts on specified database file, then exit",
    )
    parser.add_argument(
        "--backup-db",
        type=str,
        metavar="DEST",
        help="Create a verified, consistent SQLite backup to DEST, print SHA-256, and exit",
    )
    parser.add_argument(
        "--purge-vault",
        action="store_true",
        help="Revoke AttendPlan's authenticator secret from Windows Credential Manager and exit",
    )
    parser.add_argument(
        "--reset-app-data",
        action="store_true",
        help="Safely reset local app data with verified backup and allowlist deletion",
    )
    parser.add_argument(
        "--confirm",
        type=str,
        metavar="TEXT",
        help="Confirmation keyword required for high-risk operations (e.g. DELETE)",
    )
    parser.add_argument(
        "--backup-dest",
        type=str,
        metavar="PATH",
        help="Destination path for verified backup before reset-app-data",
    )

    args = parser.parse_args()

    if args.version:
        safe_print(f"AttendPlan {APP_VERSION}")
        return 0

    if args.check_db_file:
        return inspect_database_file(Path(args.check_db_file).resolve())

    if args.check_db:
        from app.db.session import get_default_db_path

        return inspect_database_file(get_default_db_path().resolve())

    if args.backup_db:
        return perform_safe_backup(args.backup_db)

    if args.purge_vault:
        return purge_vault_only()

    if args.reset_app_data:
        return perform_safe_app_data_reset(args.backup_dest, args.confirm)

    logger = setup_desktop_logging()
    logger.info("AttendPlan Desktop Launcher initializing (v%s)", APP_VERSION)
    is_owner, already_exists = acquire_app_mutex()

    target_port = args.port

    # Single-instance check
    if already_exists or is_server_healthy(args.host, target_port):
        logger.info(
            "An existing AttendPlan instance is already running (mutex_exists=%s, port_healthy=%s)",
            already_exists,
            is_server_healthy(args.host, target_port),
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

    instance_token = secrets.token_hex(16)
    app.state.instance_token = instance_token
    app.state.bound_port = target_port
    app.state.bound_host = args.host
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
        try:
            from app.db.session import default_engine
            default_engine.dispose()
            logger.info("Database engine connections closed.")
        except Exception as exc:
            logger.warning("Error closing database engine: %s", exc)
        logger.info("AttendPlan stopped cleanly.")
        release_app_mutex()

    return 0


if __name__ == "__main__":
    sys.exit(run_launcher())
