"""Portal session manager and read-only discovery adapters for iCloudEMS.

Implements safe, read-only browser orchestration via Chrome DevTools Protocol (CDP)
and Playwright, strictly respecting user privacy and university anti-tamper controls.
"""

from __future__ import annotations

import os
import sys
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import socket
from typing import Any, Optional
import urllib.request
import urllib.parse
import json

from bs4 import BeautifulSoup, Tag

DEFAULT_PORTAL_URL = "https://mrei.icloudems.com/corecampus/index.php"
DEFAULT_CDP_PORT = 9222
DEFAULT_CDP_HOST = "127.0.0.1"
ALLOWED_AUTH_HOSTS = {
    "usermanagement.icloudems.com",
    "mrei.icloudems.com",
}


OTP_SELECTOR = "input[name='otp'], input#otp, input[name='totp'], input#totp, input[name='login-otp'], input[autocomplete='one-time-code']"


def select_authentication_page(pages: list[Any], require_otp: bool = False) -> Any:
    """Prefer the actual visible challenge over unrelated or stale portal tabs."""
    allowed = [page for page in pages if urllib.parse.urlsplit(page.url).hostname in ALLOWED_AUTH_HOSTS]
    challenges = []
    mobile = []
    for page in allowed:
        otp = page.query_selector(OTP_SELECTOR)
        if otp is not None and otp.is_visible() is True:
            challenges.append(page)
        username = page.query_selector("input#username, input[name='username'], input[type='tel']")
        if username is not None and username.is_visible() is True:
            mobile.append(page)
    if len(challenges) > 1:
        from app.domain.totp_models import TotpOriginSecurityError
        raise TotpOriginSecurityError("Multiple authentication challenges are open. Select one private login tab before continuing.")
    if challenges:
        return challenges[0]
    if require_otp:
        return None
    return mobile[0] if mobile else allowed[0] if allowed else None


class PortalSessionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    BROWSER_READY = "BROWSER_READY"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    AUTHENTICATED = "AUTHENTICATED"
    DISCOVERING = "DISCOVERING"
    DISCOVERY_COMPLETE = "DISCOVERY_COMPLETE"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ERROR = "ERROR"
    MANUAL_IMPORT_AVAILABLE = "MANUAL_IMPORT_AVAILABLE"


@dataclass
class PortalSessionInfo:
    state: PortalSessionState
    browser_launched: bool
    cdp_port: int
    cdp_url: str
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    profile_dir: str = ""
    details: str = ""
    manual_fallback_available: bool = True
    otp_challenge_active: bool = False


@dataclass
class TermOption:
    value: str
    label: str
    selected: bool = False


@dataclass
class AcademicTermDiscoveryResult:
    academic_years: list[TermOption] = field(default_factory=list)
    semesters: list[TermOption] = field(default_factory=list)
    classes: list[TermOption] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubjectWiseDiscoveryResult:
    table_found: bool = False
    header_columns: list[str] = field(default_factory=list)
    record_count: int = 0
    date_range_detected: Optional[str] = None
    courses_found: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DayWiseDiscoveryResult:
    table_found: bool = False
    date_columns: list[str] = field(default_factory=list)
    time_slots: list[str] = field(default_factory=list)
    has_course_name_toggle: bool = False
    course_name_mapping_mechanism: str = "UNKNOWN"
    sample_statuses_observed: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class OverallDiscoveryResult:
    view_found: bool = False
    filter_controls: list[str] = field(default_factory=list)
    displayed_columns: list[str] = field(default_factory=list)
    macro_attendance_percentage: Optional[float] = None
    evidence: dict[str, Any] = field(default_factory=dict)


def get_dedicated_profile_dir() -> Path:
    """Return dedicated Chrome user data directory outside the workspace."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    profile_dir = Path(base) / "AttendPlan" / "chrome-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir


def find_chrome_executable() -> Optional[str]:
    """Locate local Google Chrome executable or compatible Chromium browser (e.g. Edge)."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


class PortalSessionManager:
    """Manages dedicated browser instance and detects authentication lifecycle."""

    def __init__(
        self,
        cdp_host: str = DEFAULT_CDP_HOST,
        cdp_port: int = DEFAULT_CDP_PORT,
        profile_dir: Optional[Path] = None,
    ) -> None:
        self.cdp_host = cdp_host
        self.cdp_port = cdp_port
        self.profile_dir = profile_dir or get_dedicated_profile_dir()
        self._browser_process: Optional[subprocess.Popen[Any]] = None

    @property
    def cdp_url(self) -> str:
        return f"http://{self.cdp_host}:{self.cdp_port}"

    def is_cdp_reachable(self, port: Optional[int] = None) -> bool:
        """Check if Chrome DevTools Protocol endpoint is responding on loopback."""
        check_port = port or self.cdp_port
        try:
            req = urllib.request.Request(f"http://{self.cdp_host}:{check_port}/json/version", method="GET")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=1.5) as resp:
                if resp.status != 200:
                    return False
                data = json.loads(resp.read().decode("utf-8"))
                return isinstance(data, dict) and ("Browser" in data or "webSocketDebuggerUrl" in data)
        except Exception:
            return False

    def find_working_cdp_port(self) -> int:
        """Find active CDP port or first free port in range 9222..9230."""
        if self.is_cdp_reachable(self.cdp_port):
            return self.cdp_port

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            current_in_use = (s.connect_ex((self.cdp_host, self.cdp_port)) == 0)

        if not current_in_use:
            return self.cdp_port

        for p in range(9223, 9231):
            if self.is_cdp_reachable(p):
                self.cdp_port = p
                return p
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex((self.cdp_host, p)) != 0:
                    self.cdp_port = p
                    return p

        return self.cdp_port

    def get_open_tabs(self) -> list[dict[str, Any]]:
        """List active browser tabs via CDP JSON endpoint."""
        try:
            req = urllib.request.Request(f"{self.cdp_url}/json/list", method="GET")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def launch_dedicated_browser(self, portal_url: str = DEFAULT_PORTAL_URL) -> PortalSessionInfo:
        """Launch dedicated Chrome instance bound to loopback CDP."""
        self.cdp_port = self.find_working_cdp_port()
        chrome_exe = find_chrome_executable()
        if not chrome_exe:
            return PortalSessionInfo(
                state=PortalSessionState.ERROR,
                browser_launched=False,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                profile_dir=str(self.profile_dir),
                details="Google Chrome executable not found in standard system locations.",
            )

        if self.is_cdp_reachable():
            # Already running
            return self.check_session_status()

        cmd = [
            chrome_exe,
            f"--remote-debugging-port={self.cdp_port}",
            f"--remote-debugging-address={self.cdp_host}",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            portal_url,
        ]

        try:
            # Start process detached
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            self._browser_process = subprocess.Popen(
                cmd,
                creationflags=flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return PortalSessionInfo(
                state=PortalSessionState.BROWSER_READY,
                browser_launched=True,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                profile_dir=str(self.profile_dir),
                details="Browser launched. Please log in using Keycloak and complete Google Authenticator MFA in the opened window.",
            )
        except Exception as e:
            return PortalSessionInfo(
                state=PortalSessionState.ERROR,
                browser_launched=False,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                profile_dir=str(self.profile_dir),
                details=f"Failed to launch Chrome process: {str(e)}",
            )

    def check_session_status(self) -> PortalSessionInfo:
        """Inspect current browser state over CDP without touching credentials or cookies."""
        if not self.is_cdp_reachable():
            return PortalSessionInfo(
                state=PortalSessionState.DISCONNECTED,
                browser_launched=False,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                profile_dir=str(self.profile_dir),
                details="No browser session connected on loopback port 9222.",
            )

        tabs = self.get_open_tabs()
        portal_tab = next(
            (t for t in tabs if "icloudems" in t.get("url", "").lower() or "mrei" in t.get("url", "").lower()),
            None,
        )

        if not portal_tab:
            return PortalSessionInfo(
                state=PortalSessionState.BROWSER_READY,
                browser_launched=True,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                profile_dir=str(self.profile_dir),
                details="Dedicated Chrome is running, but university portal tab is not open.",
            )

        current_url = portal_tab.get("url", "")
        title = portal_tab.get("title", "")

        # State determination based on authoritative URL and page indicators
        url_lower = current_url.lower()
        title_lower = title.lower()
        is_login_page = any(
            k in url_lower
            for k in ["/auth/", "keycloak", "login", "authenticate", "openid-connect", "corecampus/index.php"]
        )

        has_strong_view = any(
            v in url_lower
            for v in ["student_dashboard", "subwise_attendace", "myattendance", "allsubject", "student_index", "myreportcard"]
        )
        has_student_dashboard_title = any(
            t in title_lower
            for t in ["dashboard", "attendance", "student portal", "home"]
        )

        if not is_login_page and (has_strong_view or ("/student/" in url_lower and has_student_dashboard_title)):
            return PortalSessionInfo(
                state=PortalSessionState.AUTHENTICATED,
                browser_launched=True,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                current_url=current_url,
                page_title=title,
                profile_dir=str(self.profile_dir),
                details="Authenticated student portal session detected. Ready for read-only discovery.",
            )

        if (
            "usermanagement.icloudems.com" in url_lower
            or "keycloak" in url_lower
            or "login" in url_lower
            or "/auth/" in url_lower
            or url_lower.endswith("/index.php")
            or "corecampus/index.php" in url_lower
        ):
            is_otp = (
                "login-actions/authenticate" in url_lower
                or "execution=" in url_lower
                or "totp" in url_lower
                or "mfa" in url_lower
                or "authenticator" in title.lower()
            )
            details_msg = (
                "Keycloak two-factor authentication (TOTP) challenge detected."
                if is_otp
                else "Portal login page detected. Please complete Keycloak login and Google Authenticator MFA in Chrome."
            )
            return PortalSessionInfo(
                state=PortalSessionState.LOGIN_REQUIRED,
                browser_launched=True,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                current_url=current_url,
                page_title=title,
                profile_dir=str(self.profile_dir),
                details=details_msg,
                otp_challenge_active=is_otp,
            )

        return PortalSessionInfo(
            state=PortalSessionState.SESSION_EXPIRED,
            browser_launched=True,
            cdp_port=self.cdp_port,
            cdp_url=self.cdp_url,
            current_url=current_url,
            page_title=title,
            profile_dir=str(self.profile_dir),
            details="Current page is not an authenticated student dashboard. Session may have expired.",
            otp_challenge_active=False,
        )

    def close_session(self) -> None:
        """Close browser process if started by AttendPlan."""
        if self._browser_process:
            try:
                self._browser_process.terminate()
            except Exception:
                pass
            self._browser_process = None
        if self.is_cdp_reachable():
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    b = p.chromium.connect_over_cdp(self.cdp_url)
                    b.close()
            except Exception:
                pass

    def fetch_portal_page_content(self, url_keyword: str = "icloudems") -> tuple[Optional[str], Optional[str]]:
        """Safely connect over CDP, find the portal tab, and retrieve its rendered HTML DOM."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp_url)
                if not browser.contexts:
                    return None, None
                ctx = browser.contexts[0]
                target_page = next(
                    (pg for pg in ctx.pages if url_keyword in pg.url.lower()),
                    ctx.pages[0] if ctx.pages else None,
                )
                if not target_page:
                    return None, None
                url = target_page.url
                html = target_page.content()
                return url, html
        except Exception:
            return None, None

    def navigate_portal(self, path_or_href: str) -> bool:
        """Safely navigate to an authorized sub-page in the portal tab."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp_url)
                if not browser.contexts:
                    return False
                ctx = browser.contexts[0]
                target_page = next(
                    (pg for pg in ctx.pages if "icloudems" in pg.url.lower()),
                    None,
                )
                if not target_page:
                    return False
                clicked = target_page.evaluate(
                    f"""() => {{
                        const a = [...document.querySelectorAll('a')].find(x => (x.getAttribute('href')||'').includes('{path_or_href}'));
                        if (a) {{ a.click(); return true; }}
                        return false;
                    }}"""
                )
                if clicked:
                    target_page.wait_for_timeout(1500)
                return bool(clicked)
        except Exception:
            return False

    def autofill_keycloak_mfa(
        self,
        vault_service: Any,
        force_submit: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Perform verified, origin-constrained TOTP autofill and optional submission on Keycloak."""
        if not vault_service.is_enrolled():
            return {
                "success": False,
                "submitted": False,
                "redirected": False,
                "message": "No authenticator enrolled in local Windows vault.",
                "error": "VAULT_NOT_ENROLLED",
            }

        meta = vault_service.get_masked_account_metadata()
        if not meta:
            return {
                "success": False,
                "submitted": False,
                "redirected": False,
                "message": "Enrollment metadata unavailable.",
                "error": "METADATA_UNAVAILABLE",
            }

        if not self.is_cdp_reachable():
            return {
                "success": False,
                "submitted": False,
                "redirected": False,
                "message": "Dedicated Chrome is not reachable on loopback port 9222.",
                "error": "BROWSER_UNREACHABLE",
            }

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(self.cdp_url)
            try:
                if not browser.contexts:
                    return {
                        "success": False,
                        "submitted": False,
                        "redirected": False,
                        "message": "No active browser contexts in dedicated Chrome.",
                        "error": "NO_CONTEXT",
                    }
                ctx = browser.contexts[0]
                # Find tab on allowed authentication hosts
                auth_page = select_authentication_page(ctx.pages, require_otp=True)
                if not auth_page:
                    return {
                        "success": False,
                        "submitted": False,
                        "redirected": False,
                        "message": "No visible authenticator challenge is open. If already signed in, no autofill is needed; otherwise run the complete login sequence.",
                        "error": "AUTH_PAGE_NOT_FOUND",
                    }

                # Strict origin check
                parsed = urllib.parse.urlparse(auth_page.url)
                if parsed.hostname not in ALLOWED_AUTH_HOSTS:
                    from app.domain.totp_models import TotpOriginSecurityError
                    raise TotpOriginSecurityError(
                        f"Refusing to fill TOTP code: Hostname '{parsed.hostname}' is not in allowed university authentication origins."
                    )

                # Locate OTP input element
                otp_input = auth_page.query_selector(
                    "input[name='otp'], input#otp, input[name='totp'], input#totp, input[name='login-otp'], input[autocomplete='one-time-code']"
                )
                if not otp_input:
                    return {
                        "success": False,
                        "submitted": False,
                        "redirected": False,
                        "message": "No OTP challenge input field found on active Keycloak page.",
                        "error": "NO_OTP_FIELD",
                    }

                # Generate genuine current TOTP code from Windows Credential Manager
                code_result = vault_service.generate_current_code(
                    min_safety_margin_seconds=4,
                    wait_if_near_expiry=True,
                )

                # Fill code into official input field
                otp_input.fill(code_result.code)

                should_submit = force_submit if force_submit is not None else meta.auto_submit_enabled
                if not should_submit:
                    return {
                        "success": True,
                        "submitted": False,
                        "redirected": False,
                        "message": f"Generated code entered into field ({code_result.time_remaining_seconds}s remaining in window). Please review and submit in Chrome.",
                    }

                # Trigger submit button
                submit_btn = auth_page.query_selector(
                    "input[type='submit'], button[type='submit'], #kc-login, input[name='login']"
                )
                if submit_btn:
                    try:
                        submit_btn.click(timeout=3000)
                    except Exception:
                        auth_page.evaluate("b => b.click()", submit_btn)

                auth_page.wait_for_timeout(2500)

                # Check if redirected into student portal
                new_url = auth_page.url.lower()
                if "/student/" in new_url or "subwise_attendace" in new_url or "myattendance" in new_url or "student_dashboard" in new_url:
                    return {
                        "success": True,
                        "submitted": True,
                        "redirected": True,
                        "message": "MFA submitted successfully and university session authenticated.",
                    }

                # Check for Keycloak error banner
                err_text = auth_page.evaluate(
                    """() => {
                        const err = document.querySelector('.alert-error, .kc-feedback-text, #input-error-otp, .alert-danger');
                        return err ? err.innerText.trim() : null;
                    }"""
                )
                if err_text:
                    return {
                        "success": False,
                        "submitted": True,
                        "redirected": False,
                        "message": f"University authentication rejected the code: {err_text}",
                        "error": "REJECTED_BY_SERVER",
                    }

                return {
                    "success": True,
                    "submitted": True,
                    "redirected": False,
                    "message": "Code submitted. Waiting for portal redirect.",
                }
            finally:
                browser.close()


# -------------------------------------------------------------
# Discovery Adapters (Pure DOM Analyzers & CDP Wrappers)
# -------------------------------------------------------------

class AcademicTermDiscoveryAdapter:
    """Discovers accessible academic years, semesters, and class mappings."""

    @staticmethod
    def parse_from_html(html_content: str) -> AcademicTermDiscoveryResult:
        soup = BeautifulSoup(html_content, "html.parser")
        result = AcademicTermDiscoveryResult()

        # 1. Academic Year selector (aca, acadyear)
        acad_select = soup.find("select", attrs={"name": lambda x: x and ("aca" in x.lower() or "year" in x.lower())})
        if not acad_select:
            acad_select = soup.find("select", id=lambda x: x and ("aca" in x.lower() or "year" in x.lower()))

        if acad_select and isinstance(acad_select, Tag):
            for opt in acad_select.find_all("option"):
                val = opt.get("value", "").strip()
                txt = opt.get_text().strip()
                if val:
                    result.academic_years.append(
                        TermOption(value=val, label=txt, selected=opt.has_attr("selected"))
                    )

        # 2. Semester selector (sem, semNum, semNum[])
        sem_select = soup.find("select", attrs={"name": lambda x: x and "sem" in x.lower()})
        if not sem_select:
            sem_select = soup.find("select", id=lambda x: x and "sem" in x.lower())

        if sem_select and isinstance(sem_select, Tag):
            for opt in sem_select.find_all("option"):
                val = opt.get("value", "").strip()
                txt = opt.get_text().strip()
                if val:
                    result.semesters.append(
                        TermOption(value=val, label=txt, selected=opt.has_attr("selected"))
                    )

        # 3. Class selector (class, classid, classid[])
        class_select = soup.find("select", attrs={"name": lambda x: x and "class" in x.lower()})
        if not class_select:
            class_select = soup.find("select", id=lambda x: x and "class" in x.lower())

        if class_select and isinstance(class_select, Tag):
            for opt in class_select.find_all("option"):
                val = opt.get("value", "").strip()
                txt = opt.get_text().strip()
                if val:
                    result.classes.append(
                        TermOption(value=val, label=txt, selected=opt.has_attr("selected"))
                    )

        result.evidence = {
            "academic_year_count": len(result.academic_years),
            "semester_count": len(result.semesters),
            "class_count": len(result.classes),
        }
        return result


class SubjectWiseAttendanceAdapter:
    """Discovers schema, table structure, and fields of subwise_attendace_new.php."""

    @staticmethod
    def parse_from_html(html_content: str) -> SubjectWiseDiscoveryResult:
        soup = BeautifulSoup(html_content, "html.parser")
        res = SubjectWiseDiscoveryResult()

        tables = soup.find_all("table")
        target_table: Optional[Tag] = None

        for tbl in tables:
            headers = [th.get_text().strip() for th in tbl.find_all(["th", "td"])]
            header_str = " ".join(headers).lower()
            if "course" in header_str and ("attended" in header_str or "percent" in header_str or "faculty" in header_str):
                target_table = tbl
                break

        if not target_table:
            return res

        res.table_found = True
        # Extract headers
        thead = target_table.find("thead")
        header_tr = thead.find("tr") if thead and isinstance(thead, Tag) else target_table.find("tr")
        if header_tr and isinstance(header_tr, Tag):
            res.header_columns = [c.get_text().strip() for c in header_tr.find_all(["th", "td"]) if c.get_text().strip()]

        # Extract rows
        tbody = target_table.find("tbody")
        rows = tbody.find_all("tr") if tbody and isinstance(tbody, Tag) else target_table.find_all("tr")[1:]

        courses = []
        for r in rows:
            tds = [c.get_text().strip() for c in r.find_all(["td", "th"])]
            if len(tds) >= 5:
                courses.append({
                    "cells": tds,
                    "first_cell": tds[0],
                })

        res.record_count = len(courses)
        res.courses_found = courses
        res.evidence = {
            "total_rows_found": len(rows),
            "header_columns": res.header_columns,
        }
        return res


class DayWiseAttendanceAdapter:
    """Discovers schema, time slot rows, date columns, and Show Course Name toggle of myattendance.php."""

    @staticmethod
    def parse_from_html(html_content: str) -> DayWiseDiscoveryResult:
        soup = BeautifulSoup(html_content, "html.parser")
        res = DayWiseDiscoveryResult()

        # Check toggle existence
        course_name_toggle = soup.find(lambda e: e.name in ["input", "button", "label"] and "show course name" in e.get_text().lower())
        if not course_name_toggle:
            course_name_toggle = soup.find("input", attrs={"name": lambda x: x and "course" in x.lower()})

        res.has_course_name_toggle = course_name_toggle is not None

        # Find timetable grid table
        table = soup.find("table", id=lambda x: x and ("attendance" in x.lower() or "daywise" in x.lower()))
        if not table:
            for tbl in soup.find_all("table"):
                txt = tbl.get_text().lower()
                if "time" in txt and ("08:" in txt or "09:" in txt or "slot" in txt):
                    table = tbl
                    break

        if not table or not isinstance(table, Tag):
            return res

        res.table_found = True

        # Extract thead columns (date columns)
        thead = table.find("thead")
        if thead and isinstance(thead, Tag):
            for th in thead.find_all(["th", "td"]):
                t = th.get_text().strip()
                if t:
                    res.date_columns.append(t)

        # Extract time slots and observed cells
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody and isinstance(tbody, Tag) else table.find_all("tr")[1:]

        statuses_seen: set[str] = set()
        slots: list[str] = []
        has_inline_course = False

        for r in rows:
            cells = r.find_all(["td", "th"])
            if not cells:
                continue
            slot_text = cells[0].get_text(separator=" ").strip()
            if "total" not in slot_text.lower():
                slots.append(slot_text)

            for c in cells[1:]:
                c_txt = c.get_text(separator=" ").strip()
                if "P" in c_txt:
                    statuses_seen.add("P")
                if "A" in c_txt:
                    statuses_seen.add("A")
                if any(x in c_txt.lower() for x in ["csh", "cdo", "eds", "rdo"]):
                    has_inline_course = True

        res.time_slots = slots
        res.sample_statuses_observed = sorted(list(statuses_seen))
        res.course_name_mapping_mechanism = "INLINE_CELL_TEXT" if has_inline_course else "TOOLTIP_OR_SEPARATE"
        res.evidence = {
            "time_slot_count": len(slots),
            "date_column_count": len(res.date_columns),
            "statuses_seen": res.sample_statuses_observed,
        }
        return res


class OverallAttendanceAdapter:
    """Discovers allSubject.php view schema and candidate macro percentage."""

    @staticmethod
    def parse_from_html(html_content: str) -> OverallDiscoveryResult:
        soup = BeautifulSoup(html_content, "html.parser")
        res = OverallDiscoveryResult()

        tables = soup.find_all("table")
        if not tables:
            return res

        res.view_found = True
        # Filter controls
        for s in soup.find_all("select"):
            name = s.get("name") or s.get("id") or "select"
            res.filter_controls.append(name)

        # Main table headers
        tbl = tables[0]
        header_tr = tbl.find("tr")
        if header_tr and isinstance(header_tr, Tag):
            res.displayed_columns = [c.get_text().strip() for c in header_tr.find_all(["th", "td"]) if c.get_text().strip()]

        res.evidence = {
            "filter_count": len(res.filter_controls),
            "displayed_columns": res.displayed_columns,
        }
        return res
