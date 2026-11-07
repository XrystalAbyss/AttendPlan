"""Fail-closed, read-only portal controls. Never include portal content in errors."""
from __future__ import annotations

from enum import Enum
import re
import time
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ORIGIN = "https://mrei.icloudems.com"
SELECTORS = {
    "year": 'select[name="acad_year"], select#acad_year, select[name="acadyear"], select[name="aca"], select[name="sel_academic_year"], select#aca, select#acadyear, select#sel_academic_year',
    "semester": 'select[name="semNum"], select[name="semNum[]"], select[name="sem"], select[name="sel_sem"], select#semNum, select#sem, select#sel_sem',
    "class": 'select[name="class_id"], select#class_id, select[name="classid"], select[name="classid[]"], select[name="class"], select[name="sel_class"], select#classid, select#sel_class',
    "division": 'select[name="div_id"], select#div_id',
    "exam_session": 'select#exam_session',
    "exam_type": 'select#exam_name',
    "month": 'select[name="month"], select#month',
}


class PortalSafetyError(ValueError):
    """A fixed, non-sensitive diagnostic suitable for display."""


def check_page(page: Any) -> None:
    url = urlsplit(page.url)
    if url.hostname == "auth.mrei.ac.in" or "login" in url.path.lower():
        raise PortalSafetyError("SESSION_EXPIRED")
    if f"{url.scheme}://{url.netloc}" != ORIGIN or not url.path.startswith("/corecampus/student/"):
        raise PortalSafetyError("UNEXPECTED_PORTAL_ORIGIN_OR_ROUTE")
    text = page.locator("body").inner_text().lower()
    if any(marker in text for marker in ("direct url access is not allowed", "access denied", "fee hold", "session expired")):
        raise PortalSafetyError("PORTAL_ACCESS_DENIED_OR_EXPIRED")
    if page.locator('input[type="password"], input[autocomplete="one-time-code"]').count():
        raise PortalSafetyError("SESSION_EXPIRED")


def control(page: Any, kind: str) -> Any:
    locator = page.locator(SELECTORS[kind])
    if locator.count() != 1:
        raise PortalSafetyError("REQUIRED_FILTER_MISSING_OR_AMBIGUOUS")
    return locator


def options(page: Any, kind: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = control(page, kind).evaluate(
        "el => [...el.options].filter(o => !o.disabled && o.value && o.value !== '0' && o.value !== '-1').map(o => ({value:o.value,label:o.text.trim()}))"
    )
    return result


def selected(page: Any, kind: str) -> tuple[str, str]:
    values = control(page, kind).evaluate("el => [...el.selectedOptions].map(o => ({value:o.value,label:o.text.trim()}))")
    if len(values) != 1 or not values[0]["value"]:
        raise PortalSafetyError("FILTER_SELECTION_NOT_UNIQUE")
    return str(values[0]["value"]), str(values[0]["label"])


def choose(page: Any, kind: str, value: str) -> None:
    check_page(page)
    deadline = time.time() + 5.0
    current_options = options(page, kind)
    while time.time() < deadline:
        if value in {o["value"] for o in current_options}:
            break
        try:
            page.wait_for_timeout(500)
        except Exception:
            pass
        current_options = options(page, kind)
    if value not in {o["value"] for o in current_options}:
        raise PortalSafetyError("REQUESTED_FILTER_UNAVAILABLE")
    try:
        ctrl = control(page, kind)
        ctrl.select_option(value=value, timeout=8000)
        try:
            ctrl.evaluate("(el, val) => { const jq = window.jQuery; if (jq) { jq(el).val(val).trigger('change'); } }", value)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass
        page.wait_for_timeout(1500)
        check_page(page)
        if selected(page, kind)[0] != value:
            # Retry once after DOM settles in case cascading script reset it
            ctrl.select_option(value=value, timeout=8000)
            try:
                ctrl.evaluate("(el, val) => { const jq = window.jQuery; if (jq) { jq(el).val(val).trigger('change'); } }", value)
            except Exception:
                pass
            page.wait_for_timeout(1000)
            check_page(page)
            if selected(page, kind)[0] != value:
                raise PortalSafetyError("FILTER_SELECTION_MISMATCH")
    except PortalSafetyError:
        raise
    except Exception as exc:
        print(f"DEBUG: choose failed on kind={kind} value={value} with: {type(exc).__name__}: {exc}", flush=True)
        raise PortalSafetyError("FILTER_RELOAD_NOT_VERIFIED") from exc


def verify_filters(page: Any, year: str | None, semester: int | None, class_id: str | None) -> None:
    check_page(page)
    for kind, value in (("year", year), ("semester", str(semester) if semester is not None else None), ("class", class_id)):
        if value is not None and selected(page, kind)[0] != value:
            raise PortalSafetyError("RETURNED_FILTER_IDENTITY_MISMATCH")


def canonical_html(page: Any, submitted: dict[str, tuple[str, str]] | None = None) -> str:
    """Serialize live selected state (HTML attributes can be stale after JS updates)."""
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    for kind, canonical in (("year", "acadyear"), ("semester", "semNum"), ("class", "classid")):
        value, label = submitted[kind] if submitted is not None else selected(page, kind)
        controls = soup.select(SELECTORS[kind])
        if len(controls) != 1:
            raise PortalSafetyError("RETURNED_FILTER_MISSING")
        controls[0]["name"] = canonical
        controls[0]["id"] = canonical
        controls[0].clear()
        option = soup.new_tag("option", value=value, selected="selected")
        # Existing parser uses class label for subject summary and class ID for day-wise.
        option.string = label if kind == "class" else value
        controls[0].append(option)
    return str(soup)


def validate_result(
    result: Any,
    year: str | None = None,
    semester: int | None = None,
    class_id: str | None = None,
    class_label: str | None = None,
    month: str | None = None,
    require_dates: bool = False,
    **kwargs: Any,
) -> None:
    if year is None:
        year = kwargs.get("academic_year")
    if semester is None:
        semester = kwargs.get("semester")
    if class_id is None:
        class_id = kwargs.get("class_id")
    if class_label is None:
        class_label = kwargs.get("class_label")
    report = result.validation
    if not report.is_valid or report.quarantined or report.percentage_deviations:
        raise PortalSafetyError("EXTRACTION_QUARANTINED")
    if (result.academic_year, result.semester) != (year, semester):
        raise PortalSafetyError("PARSED_TERM_IDENTITY_MISMATCH")
    if result.class_identifier not in (class_id, class_label):
        raise PortalSafetyError("PARSED_CLASS_IDENTITY_MISMATCH")
    payload = result.snapshot if hasattr(result, "snapshot") else result.batch
    payload_class = payload.class_name if hasattr(payload, "class_name") else payload.class_identifier
    if (payload.academic_year, payload.semester) != (year, semester) or payload_class not in (class_id, class_label):
        raise PortalSafetyError("PAYLOAD_IDENTITY_MISMATCH")
    if month:
        dates = [o.attendance_date for o in result.batch.observations]
        if require_dates and not dates:
            raise PortalSafetyError("RETURNED_MONTH_SCOPE_MISMATCH")
        if dates and any(d.strftime("%Y-%m") != month for d in dates):
            raise PortalSafetyError("RETURNED_MONTH_SCOPE_MISMATCH")


class DaywiseScopeOutcome(str, Enum):
    """Formal classification of day-wise attendance report outcomes."""
    RECORDED = "RECORDED"
    EXPLICIT_EMPTY_RESULT = "EXPLICIT_EMPTY_RESULT"
    NO_REPORTED_PERIODS = "NO_REPORTED_PERIODS"
    UNVERIFIED_SOURCE = "UNVERIFIED_SOURCE"
    WARNING_PAGE = "WARNING_PAGE"
    PARSER_FAILURE = "PARSER_FAILURE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


def classify_daywise_html(html_content: str, requested_month: str | None = None) -> DaywiseScopeOutcome:
    """Classify the day-wise attendance report page into precise scope outcomes.
    
    Distinguishes:
    - AUTHENTICATION_REQUIRED: Session expired, login redirect, or login inputs present.
    - UNVERIFIED_SOURCE: Missing mandatory academic filters or mismatched month scope.
    - WARNING_PAGE: Portal returned a warning banner without a dated timetable matrix.
    - EXPLICIT_EMPTY_RESULT: Verified source explicitly reports no records found.
    - NO_REPORTED_PERIODS: Valid timetable matrix with dates matching requested month, but 0 delivered periods.
    - RECORDED: Valid timetable matrix with at least 1 delivered period.
    - PARSER_FAILURE: Document structure could not be parsed into a matrix.
    - UNKNOWN: Empty or unrecognized document.
    """
    if not html_content or not html_content.strip():
        return DaywiseScopeOutcome.UNKNOWN

    soup = BeautifulSoup(html_content, "html.parser")
    text_lower = soup.get_text(" ", strip=True).lower()

    # 1. Authentication check
    if any(marker in text_lower for marker in ("session expired", "please login", "login with", "sign in", "direct url access is not allowed", "access denied")):
        return DaywiseScopeOutcome.AUTHENTICATION_REQUIRED
    if soup.find("input", attrs={"type": re.compile(r"password", re.I)}) or soup.find("input", attrs={"autocomplete": "one-time-code"}):
        return DaywiseScopeOutcome.AUTHENTICATION_REQUIRED

    # 2. Check for warning page markers (banners, alert divs, notices)
    has_alert = False
    for el in soup.find_all(class_=re.compile(r"alert|warning|notice|error", re.I)):
        el_text = el.get_text(" ", strip=True).lower()
        if any(w in el_text for w in ("no record", "not found", "no attendance", "not generated", "warning", "not marked", "not available")):
            has_alert = True
            break
    if not has_alert and any(m in text_lower for m in ("warning: no attendance", "records not found", "attendance not generated", "timetable not configured")):
        has_alert = True

    # 3. Check for timetable table
    tbl = soup.find("table", id=re.compile(r"daywise", re.I))
    if not tbl:
        for t in soup.find_all("table"):
            t_text = t.get_text(" ", strip=True).lower()
            if any(k in t_text for k in ("lecture timing", "time slot", "timing")) and any(c.isdigit() for c in t_text):
                tbl = t
                break

    # If warning alert exists and NO timetable table exists:
    if has_alert and not tbl:
        return DaywiseScopeOutcome.WARNING_PAGE

    # 4. Check for explicit empty result (e.g. "0 records found" or explicit empty text with verified controls)
    if "no records found for the selected" in text_lower or "zero records found" in text_lower:
        return DaywiseScopeOutcome.EXPLICIT_EMPTY_RESULT

    # 5. Form filter presence check (verified source)
    has_acad = bool(soup.find("select", attrs={"name": re.compile(r"acad", re.I)}) or soup.find("select", id=re.compile(r"acad", re.I)))
    has_sem = bool(soup.find("select", attrs={"name": re.compile(r"sem", re.I)}) or soup.find("select", id=re.compile(r"sem", re.I)))
    if not (has_acad and has_sem):
        return DaywiseScopeOutcome.UNVERIFIED_SOURCE

    # If no table exists at all at this point:
    if not tbl:
        if has_alert:
            return DaywiseScopeOutcome.WARNING_PAGE
        return DaywiseScopeOutcome.PARSER_FAILURE

    # 6. Parse daywise observations from table
    from app.adapters.daywise_parser import ERPDaywiseParser, ParserError
    try:
        parser = ERPDaywiseParser()
        batch = parser.parse_html(html_content)
        if not batch.observations:
            return DaywiseScopeOutcome.EXPLICIT_EMPTY_RESULT

        # Check requested month
        if requested_month:
            dates = [o.attendance_date for o in batch.observations]
            if dates and any(d.strftime("%Y-%m") != requested_month for d in dates):
                return DaywiseScopeOutcome.UNVERIFIED_SOURCE

        delivered = sum(o.delivered_period_count for o in batch.observations)
        if delivered == 0:
            return DaywiseScopeOutcome.NO_REPORTED_PERIODS
        return DaywiseScopeOutcome.RECORDED
    except ParserError as err:
        err_msg = str(err).lower()
        if "could not locate day-wise" in err_msg or "0 observations" in err_msg:
            if has_alert:
                return DaywiseScopeOutcome.WARNING_PAGE
            if "no record" in text_lower or "not found" in text_lower:
                return DaywiseScopeOutcome.EXPLICIT_EMPTY_RESULT
            return DaywiseScopeOutcome.PARSER_FAILURE
        return DaywiseScopeOutcome.PARSER_FAILURE
    except Exception:
        return DaywiseScopeOutcome.PARSER_FAILURE
