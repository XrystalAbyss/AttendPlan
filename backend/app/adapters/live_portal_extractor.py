"""Live Playwright CDP Extractor for iCloudEMS Student Portal.

Executes resilient, read-only interactions over Chrome DevTools Protocol (CDP)
against an authorized student session:
- Dynamic discovery of academic years, semesters, and class mappings
- Subject-wise live attendance extraction and percentage verification
- Day-wise timetable matrix extraction with Show Course Name attribution
- Strict enforcement of domain invariants, privacy boundaries, and validation
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

from app.adapters.portal_safety import (
    PortalSafetyError, SELECTORS, canonical_html, check_page, choose, control, options, selected, validate_result, verify_filters,
)
from typing import Any, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright

from app.adapters.daywise_parser import ERPDaywiseParser, ParsedDaywiseBatch
from app.adapters.html_parser import ERPAttendanceParser
from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    AcademicTermDiscoveryResult,
    PortalSessionManager,
    TermOption,
)
from app.domain.models import AttendanceSnapshot as DomainSnapshot, DataProvenance

logger = logging.getLogger(__name__)

PORTAL_BASE = "https://mrei.icloudems.com"
SUBWISE_URL_PATH = "/corecampus/student/attendance/subwise_attendace_new.php"
DAYWISE_URL_PATH = "/corecampus/student/attendance/myattendance.php"
OVERALL_URL_PATH = "/corecampus/student/attendance/allSubject.php"


class PortalExtractionError(Exception):
    """Base exception for live portal extraction failures."""
    pass


class SessionNotAuthenticatedError(PortalExtractionError):
    """Raised when portal session is expired, missing, or requires manual login."""
    pass


class BrowserNotConnectedError(PortalExtractionError):
    """Raised when CDP endpoint is unreachable."""
    pass


@dataclass
class ExtractionValidationReport:
    """Detailed validation diagnostics for a live extraction."""
    is_valid: bool
    record_count: int
    source_displayed_totals: dict[str, Any] = field(default_factory=dict)
    locally_computed_totals: dict[str, Any] = field(default_factory=dict)
    percentage_deviations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quarantined: bool = False
    quarantine_reason: Optional[str] = None


@dataclass
class LiveSubjectWiseExtractionResult:
    snapshot: DomainSnapshot
    raw_html: str
    validation: ExtractionValidationReport
    academic_year: str
    semester: int
    class_identifier: Optional[str]
    reporting_start_date: Optional[str]
    reporting_end_date: Optional[str]


@dataclass
class LiveDayWiseExtractionResult:
    batch: ParsedDaywiseBatch
    raw_html: str
    validation: ExtractionValidationReport
    academic_year: str
    semester: int
    class_identifier: Optional[str]
    selected_month: Optional[str]
    coverage_start: date
    coverage_end: date
    course_attribution_active: bool


class LivePortalExtractor:
    """Orchestrates resilient Playwright CDP operations on the live portal session."""

    def __init__(self, session_manager: Optional[PortalSessionManager] = None) -> None:
        self.session_manager = session_manager or PortalSessionManager()

    def _get_portal_page(self, playwright_instance: Any) -> tuple[Any, Page]:
        """Connect over CDP and retrieve the active university portal tab."""
        if not self.session_manager.is_cdp_reachable():
            raise BrowserNotConnectedError(
                f"Chrome DevTools Protocol is not responding on {self.session_manager.cdp_url}."
            )

        browser = playwright_instance.chromium.connect_over_cdp(self.session_manager.cdp_url)
        if not browser.contexts:
            raise BrowserNotConnectedError("Connected to CDP, but browser has zero active contexts.")

        ctx = browser.contexts[0]
        portal_page = next((pg for pg in ctx.pages if urlsplit(pg.url).hostname == "mrei.icloudems.com"), None)
        if portal_page is None:
            browser.close()
            raise SessionNotAuthenticatedError("Manual private authentication required.")
        try:
            check_page(portal_page)
        except PortalSafetyError:
            browser.close()
            raise SessionNotAuthenticatedError("Manual private authentication required.") from None
        return browser, portal_page

    def navigate_to_view(self, page: Page, path: str, ready_indicator: str, timeout_ms: int = 8000) -> None:
        """Use only an exact same-origin attendance menu route; no direct URL fallback."""
        if path not in {SUBWISE_URL_PATH, DAYWISE_URL_PATH, OVERALL_URL_PATH}:
            raise PortalSafetyError("ROUTE_NOT_ALLOWLISTED")
        check_page(page)
        if urlsplit(page.url).path != path or bool(urlsplit(page.url).query):
            links = page.locator("a[href]")
            target = None
            from urllib.parse import urljoin
            for index in range(links.count()):
                link = links.nth(index)
                destination = urlsplit(urljoin(page.url, link.get_attribute("href") or ""))
                if (destination.scheme, destination.netloc, destination.path) == ("https", "mrei.icloudems.com", path):
                    target = link
                    break
            if target is None and path != SUBWISE_URL_PATH:
                self.navigate_to_view(page, SUBWISE_URL_PATH, ready_indicator, timeout_ms)
                self.navigate_to_view(page, path, ready_indicator, timeout_ms)
                return
            if target is None:
                raise PortalSafetyError("ATTENDANCE_MENU_ROUTE_UNAVAILABLE")
            try:
                target.click(timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            except Exception:
                if urlsplit(page.url).path != path:
                    raise PortalSafetyError("ATTENDANCE_NAVIGATION_NOT_READY") from None
        check_page(page)
        if urlsplit(page.url).path != path:
            raise PortalSafetyError("ATTENDANCE_ROUTE_MISMATCH")
        try:
            # A hidden profile form can precede attendance selectors in the DOM.
            page.locator(SELECTORS["year"]).wait_for(state="visible", timeout=timeout_ms)
            control(page, "year")
        except Exception as ex:
            logger.error("ATTENDANCE_VIEW_NOT_READY cause: %s (type: %s)", ex, type(ex).__name__)
            raise PortalSafetyError("ATTENDANCE_VIEW_NOT_READY") from None

    def discover_historical_combinations(self) -> list[dict[str, str]]:
        """Read dependent options after each year and semester reload; never cross product."""
        with sync_playwright() as p:
            browser, page = self._get_portal_page(p)
            try:
                self.navigate_to_view(page, SUBWISE_URL_PATH, "select#acadyear, select#aca, select#sel_academic_year")
                initial = {kind: selected(page, kind)[0] for kind in ("year", "semester", "class")}
                combinations = []
                try:
                    years = options(page, "year")
                    if len(years) > 20:
                        raise PortalSafetyError("DISCOVERY_SCOPE_TOO_LARGE")
                    for year in years:
                        choose(page, "year", year["value"])
                        semesters = options(page, "semester")
                        if len(semesters) > 12:
                            raise PortalSafetyError("DISCOVERY_SCOPE_TOO_LARGE")
                        for sem in semesters:
                            if not sem["value"].isdigit():
                                continue
                            choose(page, "semester", sem["value"])
                            if selected(page, "year")[0] != year["value"]:
                                raise PortalSafetyError("DEPENDENT_YEAR_RESET")
                            classes = options(page, "class")
                            if len(classes) > 20:
                                raise PortalSafetyError("DISCOVERY_SCOPE_TOO_LARGE")
                            for cls in classes:
                                choose(page, "class", cls["value"])
                                verify_filters(page, year["value"], int(sem["value"]), cls["value"])
                                combinations.append({"academic_year": year["value"], "semester": sem["value"],
                                                     "class_id": cls["value"], "class_label": cls["label"]})
                                if len(combinations) > 80:
                                    raise PortalSafetyError("DISCOVERY_SCOPE_TOO_LARGE")
                finally:
                    for kind in ("year", "semester", "class"):
                        choose(page, kind, initial[kind])
                return combinations
            finally:
                browser.close()

    def _apply_filters(self, page: Page, year: Optional[str], semester: Optional[int], class_id: Optional[str]) -> None:
        for kind, value in (("year", year), ("semester", str(semester) if semester is not None else None), ("class", class_id)):
            if value is not None:
                try:
                    already_selected = selected(page, kind)[0] == value
                except PortalSafetyError as error:
                    if str(error) != "FILTER_SELECTION_NOT_UNIQUE":
                        raise
                    already_selected = False
                if not already_selected:
                    choose(page, kind, value)
        verify_filters(page, year, semester, class_id)

    def _search(self, page: Page, expected_path: str) -> dict[str, tuple[str, str]]:
        if urlsplit(page.url).path != expected_path:
            raise PortalSafetyError("ATTENDANCE_ROUTE_MISMATCH")
        button = page.locator('#getattendance, #search, button:has-text("Search")')
        if button.count() != 1:
            raise PortalSafetyError("READ_ONLY_SEARCH_MISSING_OR_AMBIGUOUS")
        form_action = button.evaluate("el => el.form ? el.form.action : location.href")
        destination = urlsplit(form_action)
        if destination.scheme != "https" or destination.netloc != "mrei.icloudems.com" or destination.path != expected_path:
            raise PortalSafetyError("UNEXPECTED_SEARCH_TARGET")
        submitted = {kind: selected(page, kind) for kind in ("year", "semester", "class")}
        try:
            method = "GET" if expected_path == DAYWISE_URL_PATH else "POST"
            with page.expect_request(lambda req: req.method == method and req.is_navigation_request() and urlsplit(req.url).path == expected_path, timeout=8000) as pending:
                button.click(timeout=8000)
            request = pending.value
            target = urlsplit(request.url)
            if (target.scheme, target.netloc) != ("https", "mrei.icloudems.com"):
                raise PortalSafetyError("UNEXPECTED_SUBMITTED_ORIGIN")
            if method == "POST":
                fields = parse_qs(request.post_data or "")
                for kind, field_name in (("year", "acadyear"), ("semester", "semNum[]"), ("class", "classid[]")):
                    if fields.get(field_name) != [submitted[kind][0]]:
                        raise PortalSafetyError("SUBMITTED_SCOPE_MISMATCH")
            elif set(parse_qs(target.query)) != {"e", "submit"}:
                # Follow only the UI-generated report navigation; never decode or construct e.
                raise PortalSafetyError("UNEXPECTED_DAYWISE_QUERY_FIELDS")
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            check_page(page)
            if urlsplit(page.url).path != expected_path:
                raise PortalSafetyError("ATTENDANCE_ROUTE_MISMATCH")
            page.wait_for_selector("table", timeout=8000)
            response = request.response()
            if response is None or not response.ok or response.request != request:
                raise PortalSafetyError("REPORT_RESPONSE_NOT_VERIFIED")
            check_page(page)
            if urlsplit(page.url).path != expected_path:
                raise PortalSafetyError("REPORT_ROUTE_MISMATCH")
            if expected_path != DAYWISE_URL_PATH:
                for kind, (value, _) in submitted.items():
                    echoed = control(page, kind).evaluate("el => [...el.selectedOptions].map(o => o.value).filter(Boolean)")
                    if echoed and echoed != [value]:
                        raise PortalSafetyError("RETURNED_FILTER_IDENTITY_MISMATCH")
            else:
                if "e" not in parse_qs(urlsplit(page.url).query):
                    raise PortalSafetyError("RETURNED_FILTER_IDENTITY_MISMATCH")
            return submitted
        except PortalSafetyError:
            raise
        except Exception:
            raise PortalSafetyError("ATTENDANCE_SEARCH_NOT_READY") from None

    # ---------------------------------------------------------
    # Gate 1: Dynamic Discovery
    # ---------------------------------------------------------

    def discover_live_terms(self) -> AcademicTermDiscoveryResult:
        """Dynamically inspect available academic years, semesters, and class mappings."""
        with sync_playwright() as p:
            browser, page = self._get_portal_page(p)
            try:
                self.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca, #sem", timeout_ms=6000)
                html_content = page.content()
                result = AcademicTermDiscoveryAdapter.parse_from_html(html_content)

                # Annotate evidence with live provenance
                result.evidence["live_route"] = urlsplit(page.url).path
                result.evidence["classification"] = "VERIFIED_LIVE"
                return result
            finally:
                browser.close()

    def discover_semesters_for_year(self, academic_year: str) -> list[TermOption]:
        """Select an academic year and capture dynamically populated semester options."""
        with sync_playwright() as p:
            browser, page = self._get_portal_page(p)
            try:
                self.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca", timeout_ms=6000)
                choose(page, "year", academic_year)

                html_content = page.content()
                parsed = AcademicTermDiscoveryAdapter.parse_from_html(html_content)
                return parsed.semesters
            finally:
                browser.close()

    # ---------------------------------------------------------
    # Gate 2: Live Subject-Wise Extraction
    # ---------------------------------------------------------

    def extract_live_subject_wise(
        self,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        class_id: Optional[str] = None,
    ) -> LiveSubjectWiseExtractionResult:
        """Perform verified live extraction of Subject-Wise Attendance (subwise_attendace_new.php)."""
        with sync_playwright() as p:
            browser, page = self._get_portal_page(p)
            try:
                self.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca, table", timeout_ms=8000)

                self._apply_filters(page, academic_year, semester, class_id)
                submitted = self._search(page, SUBWISE_URL_PATH)
                html_content = canonical_html(page, submitted)

                # 6. Parse with domain parser
                parser = ERPAttendanceParser(strict_validation=True)
                snapshot = parser.parse_html(
                    html_content,
                    provenance=DataProvenance.LIVE_PORTAL,
                    snapshot_id=f"snap-live-{academic_year or 'active'}-s{semester or 0}",
                )


                # 7. Semantic validation: Compare calculated percentage against portal displayed percentage
                validation = self._validate_subject_wise_snapshot(html_content, snapshot)

                result = LiveSubjectWiseExtractionResult(
                    snapshot=snapshot,
                    raw_html=html_content,
                    validation=validation,
                    academic_year=snapshot.academic_year,
                    semester=snapshot.semester,
                    class_identifier=snapshot.class_name,
                    reporting_start_date=snapshot.date_range.from_date,
                    reporting_end_date=snapshot.date_range.to_date,
                )
                if academic_year is not None and semester is not None and class_id is not None:
                    validate_result(result, academic_year, semester, class_id, submitted["class"][1])
                elif not validation.is_valid or validation.quarantined:
                    raise PortalSafetyError("EXTRACTION_QUARANTINED")
                return result
            finally:
                browser.close()

    def _validate_subject_wise_snapshot(
        self,
        html_content: str,
        snapshot: DomainSnapshot,
    ) -> ExtractionValidationReport:
        """Validate mathematical invariants and compare with displayed portal values."""
        soup = BeautifulSoup(html_content, "html.parser")
        report = ExtractionValidationReport(is_valid=True, record_count=len(snapshot.courses))

        if len(snapshot.courses) == 0:
            report.is_valid = False
            report.quarantined = True
            report.quarantine_reason = "Zero course records parsed from subject-wise table"
            return report

        # Match the actual course-code column, not a code reused in a short name
        # or another cell. Use semantic headers to avoid unrelated profile tables.
        course_map = {course.code: course for course in snapshot.courses}
        if len(course_map) != len(snapshot.courses):
            report.is_valid = False
            report.quarantined = True
            report.quarantine_reason = "DUPLICATE_COURSE_CODES"
            return report
        matches = []
        parser = ERPAttendanceParser()
        for table in soup.find_all("table"):
            columns = parser._inspect_table_headers(table)
            if "course_code" not in columns or "percent" not in columns:
                continue
            rows = []
            course_idx = 0
            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if any(cell.name == "th" for cell in row.find_all(["td", "th"])):
                    continue
                row_text = row.get_text().lower()
                if "total" in row_text or "grand total" in row_text or "total percentage" in row_text:
                    continue
                if len(cells) > max(columns["course_code"], columns["percent"]):
                    c_code = cells[columns["course_code"]]
                    if c_code and course_idx < len(snapshot.courses):
                        course = snapshot.courses[course_idx]
                        if course.code.startswith(c_code):
                            rows.append((course, cells[columns["percent"]]))
                            course_idx += 1
            if rows:
                matches.append(rows)
        if not matches:
            report.is_valid = False
            report.quarantined = True
            report.quarantine_reason = "PERCENTAGE_COLUMN_NOT_IDENTIFIED"
            return report
        for course, displayed in max(matches, key=len):
            if course.percent is None:
                continue
            try:
                displayed_percentage = float(displayed.replace("%", "").strip())
            except ValueError:
                continue
            difference = abs(course.percent-displayed_percentage)
            if difference > 0.5:
                report.percentage_deviations.append({"course":course.code,"computed":course.percent,
                    "displayed":displayed_percentage,"diff":round(difference,2)})

        if len(report.percentage_deviations) > 0:
            report.warnings.append(
                f"{len(report.percentage_deviations)} courses show slight rounding differences with portal display."
            )

        report.locally_computed_totals = {
            "total_attended": snapshot.summary.total_attended,
            "total_delivered": snapshot.summary.total_delivered,
            "aggregate_percentage": snapshot.summary.overall_percentage,
        }
        return report


    # ---------------------------------------------------------
    # Gate 3: Live Day-Wise Extraction
    # ---------------------------------------------------------

    def extract_live_day_wise(
        self,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        class_id: Optional[str] = None,
        month: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        show_course_name: bool = True,
    ) -> LiveDayWiseExtractionResult:
        """Perform verified live extraction of Day-Wise Timetable Matrix (myattendance.php)."""
        with sync_playwright() as p:
            browser, page = self._get_portal_page(p)
            try:
                self.navigate_to_view(page, DAYWISE_URL_PATH, "select, #acadyear, #search", timeout_ms=8000)

                self._apply_filters(page, academic_year, semester, class_id)
                if month:
                    candidates = [o["value"] for o in options(page, "month") if o["value"].isdigit() and int(o["value"]) == int(month)]
                    if len(candidates) != 1:
                        raise PortalSafetyError("REQUESTED_MONTH_UNAVAILABLE")
                    choose(page, "month", candidates[0])
                if month:
                    if bool(from_date) != bool(to_date):
                        raise PortalSafetyError("BOTH_REPORT_DATES_REQUIRED")
                    if from_date and to_date:
                        start, end = date.fromisoformat(from_date), date.fromisoformat(to_date)
                    else:
                        start = datetime.strptime(page.locator("#from_date").input_value(), "%d/%m/%Y").date().replace(day=1)
                        end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
                    if start.month != int(month) or end.month != start.month or end.year != start.year or start > end:
                        raise PortalSafetyError("REPORT_DATE_MONTH_MISMATCH")
                    if academic_year and str(start.year) not in academic_year.split("-"):
                        raise PortalSafetyError("REPORT_DATE_YEAR_MISMATCH")
                    for selector, value in (("#from_date", start), ("#to_date", end)):
                        field = page.locator(selector)
                        if field.count() != 1:
                            raise PortalSafetyError("REPORT_DATE_CONTROL_MISSING")
                        formatted = value.strftime("%d/%m/%Y")
                        field.fill(formatted)
                        field.evaluate("(el, value) => { const jq = window.jQuery; if (jq && jq(el).data('datepicker')) jq(el).datepicker('update', value); }", formatted)
                        field.press("Tab")
                        if field.input_value() != formatted:
                            raise PortalSafetyError("REPORT_DATE_NOT_SELECTED")
                elif from_date or to_date:
                    raise PortalSafetyError("MONTH_REQUIRED_FOR_DATE_WINDOW")
                submitted = self._search(page, DAYWISE_URL_PATH)
                course_toggle_found = False
                if show_course_name:
                    label = page.locator("label").filter(has_text="Show Course Name")
                    toggle = label.locator('input[type="checkbox"]')
                    if label.count() != 1 or toggle.count() != 1:
                        raise PortalSafetyError("COURSE_ATTRIBUTION_CONTROL_MISSING")
                    if not toggle.is_checked():
                        label.click(timeout=8000)
                    course_toggle_found = toggle.is_checked()
                    if not course_toggle_found:
                        raise PortalSafetyError("COURSE_ATTRIBUTION_NOT_ENABLED")
                html_content = canonical_html(page, submitted)

                # 9. Parse daywise matrix
                parser = ERPDaywiseParser()
                batch = parser.parse_html(html_content)

                # 10. Validate matrix totals
                validation = self._validate_daywise_batch(html_content, batch)

                result = LiveDayWiseExtractionResult(
                    batch=batch,
                    raw_html=html_content,
                    validation=validation,
                    academic_year=batch.academic_year,
                    semester=batch.semester,
                    class_identifier=batch.class_identifier,
                    selected_month=month,
                    coverage_start=batch.coverage_start_date,
                    coverage_end=batch.coverage_end_date,
                    course_attribution_active=course_toggle_found,
                )
                if academic_year is not None and semester is not None and class_id is not None:
                    validate_result(result, academic_year, semester, class_id, submitted["class"][1])
                if not validation.is_valid or validation.quarantined:
                    raise PortalSafetyError("EXTRACTION_QUARANTINED")
                if month and any(o.attendance_date.month != int(month) for o in batch.observations):
                    raise PortalSafetyError("RETURNED_MONTH_SCOPE_MISMATCH")
                return result
            finally:
                browser.close()

    def _validate_daywise_batch(
        self,
        html_content: str,
        batch: ParsedDaywiseBatch,
    ) -> ExtractionValidationReport:
        """Cross-check extracted P/A observations against portal summary rows/columns."""
        soup = BeautifulSoup(html_content, "html.parser")
        report = ExtractionValidationReport(is_valid=True, record_count=len(batch.observations))

        present_count = sum(o.attended_period_count for o in batch.observations)
        delivered_count = sum(o.delivered_period_count for o in batch.observations)
        unmapped_count = sum(1 for o in batch.observations if o.delivered_period_count > 0 and not o.source_course_label)

        report.locally_computed_totals = {
            "total_present_periods": present_count,
            "total_delivered_periods": delivered_count,
            "unmapped_period_count": unmapped_count,
            "observed_dates_count": len(set(o.attendance_date for o in batch.observations)),
        }

        # Look for explicit Total row in table to verify against
        for tbl in soup.find_all("table"):
            for tr in tbl.find_all("tr"):
                txt = tr.get_text().lower()
                if "total" in txt and ("present" in txt or "attended" in txt or "absent" in txt):
                    cells = [c.get_text().strip() for c in tr.find_all(["td", "th"])]
                    report.source_displayed_totals["totals_row"] = cells
                    break

        if delivered_count == 0:
            report.warnings.append("Zero delivered periods extracted for the specified date window.")

        return report

