"""Manav Rachna Performances filters, discovered from real menu links and DOM options."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import sync_playwright

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import PortalSafetyError, check_page, choose, control, options, selected
from app.services.performance_service import parse_performance

QUERY_PATH = "/corecampus/student/grades/new/save/myreportcardSave.php"
PERFORMANCE_PATH = "/corecampus/student/grades/new/myreportcard.php"


def open_performances(page: Any) -> None:
    check_page(page)
    if urlsplit(page.url).path != PERFORMANCE_PATH:
        links = page.locator("a[href]")
        target = None
        for index in range(links.count()):
            link = links.nth(index)
            dest = urlsplit(urljoin(page.url, link.get_attribute("href") or ""))
            if (dest.scheme, dest.netloc, dest.path) == ("https", "mrei.icloudems.com", PERFORMANCE_PATH) and link.is_visible():
                target = link
                break
        if target is None:
            raise PortalSafetyError("PERFORMANCES_MENU_UNAVAILABLE")
        target.click(timeout=10000)
        page.wait_for_url("**" + PERFORMANCE_PATH, timeout=10000)
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
    check_page(page)
    if urlsplit(page.url).path != PERFORMANCE_PATH:
        raise PortalSafetyError("PERFORMANCES_ROUTE_MISMATCH")
    control(page, "year").wait_for(state="visible", timeout=10000)


def validate_scope(page: Any, term: Any, session: str, exam_type: str | None = None, division_id: str | None = None) -> None:
    check_page(page)
    if urlsplit(page.url).path != PERFORMANCE_PATH:
        raise PortalSafetyError("PERFORMANCES_ROUTE_MISMATCH")
    if selected(page, "year")[0] != term.academic_year or selected(page, "class")[0] != term.class_identifier:
        raise PortalSafetyError("PERFORMANCE_TERM_MISMATCH")
    label = selected(page, "class")[1]
    if not re.search(rf"\bsem(?:ester)?\s*-?\s*{term.semester_number}\b", label, re.I):
        raise PortalSafetyError("PERFORMANCE_SEMESTER_LABEL_MISMATCH")
    if selected(page, "exam_session")[0] != session:
        raise PortalSafetyError("PERFORMANCE_EXAM_SESSION_MISMATCH")
    divisions = options(page, "division")
    if len(divisions) != 1 or selected(page, "division")[0] != divisions[0]["value"]:
        raise PortalSafetyError("PERFORMANCE_DIVISION_REQUIRES_EXPLICIT_SCOPE")
    if division_id is not None and selected(page, "division")[0] != division_id:
        raise PortalSafetyError("PERFORMANCE_DIVISION_MISMATCH")
    if exam_type == "4":
        raise PortalSafetyError("EXTERNAL_EXAM_SCOPE_REJECTED")
    if exam_type is not None and selected(page, "exam_type")[0] != exam_type:
        raise PortalSafetyError("PERFORMANCE_EXAM_TYPE_MISMATCH")


def discover_scopes(term: Any) -> list[dict[str, str]]:
    with sync_playwright() as p:
        browser, page = LivePortalExtractor()._get_portal_page(p)
        try:
            open_performances(page)
            initial = {kind: control(page, kind).input_value() for kind in ("year", "exam_session", "class", "exam_type")}
            result = []
            try:
                choose(page, "year", term.academic_year)
                sessions = options(page, "exam_session")
                if len(sessions) > 12:
                    raise PortalSafetyError("EXAM_DISCOVERY_SCOPE_TOO_LARGE")
                for session in sessions:
                    choose(page, "exam_session", session["value"])
                    if term.class_identifier not in {c["value"] for c in options(page, "class")}:
                        continue
                    choose(page, "class", term.class_identifier)
                    try:
                        validate_scope(page, term, session["value"])
                    except PortalSafetyError:
                        continue
                    for exam in options(page, "exam_type"):
                        if exam.get("value") == "4" or "external" in exam.get("label", "").lower():
                            continue
                        result.append({"exam_session": session["value"], "exam_session_label": session["label"],
                                       "exam_type": exam["value"], "exam_type_label": exam["label"], "division_id": selected(page, "division")[0]})
            finally:
                try:
                    for kind, value in initial.items():
                        if value:
                            choose(page, kind, value)
                        else:
                            control(page, kind).select_option(value="", timeout=8000)
                except Exception:
                    pass
            return result
        finally:
            browser.close()


def extract_marks(term: Any, session: str, exam_type: str, division_id: str | None = None) -> dict[str, Any]:
    if exam_type == "4":
        raise PortalSafetyError("EXTERNAL_EXAM_SCOPE_REJECTED")
    with sync_playwright() as p:
        browser, page = LivePortalExtractor()._get_portal_page(p)
        try:
            open_performances(page)
            for kind, value in (("year", term.academic_year), ("exam_session", session), ("class", term.class_identifier), ("exam_type", exam_type)):
                choose(page, kind, value)
            validate_scope(page, term, session, exam_type, division_id)
            button = page.locator('input[type="submit"][name="submit"], button[type="submit"][name="submit"]')
            if button.count() != 1:
                raise PortalSafetyError("PERFORMANCE_SEARCH_AMBIGUOUS")
            form = button.locator("xpath=ancestor::form")
            if form.count() != 1 or form.locator('input[type="file"]').count():
                raise PortalSafetyError("UNEXPECTED_PERFORMANCE_FORM")
            action = urlsplit(button.evaluate("el => el.form.action"))
            if action.scheme != "https" or action.netloc != "mrei.icloudems.com" or action.path not in {PERFORMANCE_PATH, QUERY_PATH}:
                raise PortalSafetyError("UNEXPECTED_PERFORMANCE_FORM_TARGET")
            # The observed report-query handler is named Save, but its form accepts
            # only academic filter choices plus hidden identity/context, never editable marks.
            fields = form.locator("input,select,textarea").evaluate_all("els => els.map(e => ({tag:e.tagName,type:e.type,name:e.name}))")
            for field in fields:
                if field["tag"] == "SELECT":
                    if field["name"] not in {"acad_year", "exam_session", "class_id", "div_id", "exam_id[]"}:
                        raise PortalSafetyError("UNEXPECTED_PERFORMANCE_FILTER")
                elif field["type"] not in {"hidden", "search", "submit"}:
                    raise PortalSafetyError("EDITABLE_DATA_NOT_ALLOWED_IN_REPORT_QUERY")
            with page.expect_response(lambda response: response.request.method == "POST" and urlsplit(response.url).path == action.path, timeout=15000) as pending_report:
                button.click(timeout=10000)
            if not pending_report.value.ok:
                raise PortalSafetyError("PERFORMANCE_REPORT_RESPONSE_FAILED")
            report_text = pending_report.value.text()
            if "Subject Code" in report_text or "Course Code" in report_text:
                parsed = parse_performance(report_text)
            else:
                page.get_by_text("Subject Code", exact=True).wait_for(state="visible", timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)
                validate_scope(page, term, session, exam_type, division_id)
                parsed = parse_performance(page.content())
            parsed["exam_session"] = session
            parsed["exam_type"] = exam_type
            parsed["division_id"] = selected(page, "division")[0]
            return parsed
        finally:
            browser.close()

