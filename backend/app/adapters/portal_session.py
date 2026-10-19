"""Portal session manager and read-only discovery adapters for iCloudEMS.

Implements safe, read-only browser orchestration via Chrome DevTools Protocol (CDP)
and Playwright, strictly respecting user privacy and university anti-tamper controls.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import urllib.request
import json

from bs4 import BeautifulSoup, Tag

DEFAULT_PORTAL_URL = "https://mrei.icloudems.com/corecampus/index.php"
DEFAULT_CDP_PORT = 9222
DEFAULT_CDP_HOST = "127.0.0.1"


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
    """Locate local Google Chrome executable."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
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

    def is_cdp_reachable(self) -> bool:
        """Check if Chrome DevTools Protocol endpoint is responding on loopback."""
        try:
            req = urllib.request.Request(f"{self.cdp_url}/json/version", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_open_tabs(self) -> list[dict[str, Any]]:
        """List active browser tabs via CDP JSON endpoint."""
        try:
            req = urllib.request.Request(f"{self.cdp_url}/json/list", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def launch_dedicated_browser(self, portal_url: str = DEFAULT_PORTAL_URL) -> PortalSessionInfo:
        """Launch dedicated Chrome instance bound to loopback CDP."""
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
            self._browser_process = subprocess.Popen(
                cmd,
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

        # State determination based on authoritative URL patterns
        url_lower = current_url.lower()
        if "keycloak" in url_lower or "login" in url_lower or "index.php" in url_lower:
            return PortalSessionInfo(
                state=PortalSessionState.LOGIN_REQUIRED,
                browser_launched=True,
                cdp_port=self.cdp_port,
                cdp_url=self.cdp_url,
                current_url=current_url,
                page_title=title,
                profile_dir=str(self.profile_dir),
                details="Portal login page detected. Please complete Keycloak login and Google Authenticator MFA in Chrome.",
            )

        if (
            "student_dashboard" in url_lower
            or "subwise_attendace" in url_lower
            or "myattendance" in url_lower
            or "allsubject" in url_lower
            or "student" in url_lower
        ):
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

        return PortalSessionInfo(
            state=PortalSessionState.SESSION_EXPIRED,
            browser_launched=True,
            cdp_port=self.cdp_port,
            cdp_url=self.cdp_url,
            current_url=current_url,
            page_title=title,
            profile_dir=str(self.profile_dir),
            details="Current page is not an authenticated student dashboard. Session may have expired.",
        )

    def close_session(self) -> None:
        """Close browser process if started by AttendPlan."""
        if self._browser_process:
            try:
                self._browser_process.terminate()
            except Exception:
                pass
            self._browser_process = None

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
