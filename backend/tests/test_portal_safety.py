"""Offline safety regressions: no live browser, database, or credentials."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.adapters.live_portal_extractor import LivePortalExtractor, SUBWISE_URL_PATH
from app.adapters.portal_safety import (
    PortalSafetyError,
    choose,
    validate_result,
    verify_filters,
)


def result(**changes):
    payload = SimpleNamespace(
        academic_year="2025-2026", semester=4, class_name="Class Four"
    )
    values = dict(
        academic_year="2025-2026",
        semester=4,
        class_identifier="Class Four",
        snapshot=payload,
        validation=SimpleNamespace(
            is_valid=True, quarantined=False, percentage_deviations=[]
        ),
    )
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "url",
    [
        "https://mrei.icloudems.com.evil.test/corecampus/student/home",
        "https://example.org/student/",
        "https://auth.mrei.ac.in/login",
    ],
)
def test_navigation_refuses_untrusted_origins(url):
    page = Mock(url=url)
    with pytest.raises(PortalSafetyError):
        LivePortalExtractor().navigate_to_view(page, SUBWISE_URL_PATH, "table")
    page.goto.assert_not_called()


def safe_page():
    page = Mock(url="https://mrei.icloudems.com/corecampus/student/student_index.php")
    page.locator.return_value.inner_text.return_value = "Student attendance"
    page.locator.return_value.count.return_value = 0
    return page


def test_missing_menu_has_no_direct_navigation_fallback():
    page = safe_page()
    with pytest.raises(PortalSafetyError, match="MENU_ROUTE_UNAVAILABLE"):
        LivePortalExtractor().navigate_to_view(page, SUBWISE_URL_PATH, "table")
    page.goto.assert_not_called()


def test_access_denial_stops_before_navigation():
    page = safe_page()
    page.locator.return_value.inner_text.return_value = (
        "Direct URL Access is not allowed"
    )
    with pytest.raises(PortalSafetyError, match="ACCESS_DENIED"):
        LivePortalExtractor().navigate_to_view(page, SUBWISE_URL_PATH, "table")
    page.goto.assert_not_called()


def test_required_filter_never_silently_skipped():
    page = safe_page()
    with pytest.raises(PortalSafetyError, match="FILTER_MISSING"):
        choose(page, "year", "2025-2026")


@pytest.mark.parametrize(
    "changes",
    [
        {"academic_year": "2026-2027"},
        {"semester": 5},
        {"class_identifier": "Other Class"},
        {
            "validation": SimpleNamespace(
                is_valid=False, quarantined=True, percentage_deviations=[]
            )
        },
        {
            "validation": SimpleNamespace(
                is_valid=True, quarantined=False, percentage_deviations=[{}]
            )
        },
        {
            "snapshot": SimpleNamespace(
                academic_year="2026-2027", semester=5, class_name="Class Four"
            )
        },
    ],
)
def test_invalid_results_cannot_cross_ingestion_boundary(changes):
    with pytest.raises(PortalSafetyError):
        validate_result(result(**changes), "2025-2026", 4, "2140", "Class Four")


def test_valid_results_preserve_explicit_identity():
    validate_result(result(), "2025-2026", 4, "2140", "Class Four")


def test_reloaded_filter_mismatch_is_rejected(monkeypatch):
    page = safe_page()
    monkeypatch.setattr(
        "app.adapters.portal_safety.selected", lambda page, kind: ("wrong", "Wrong")
    )
    with pytest.raises(PortalSafetyError, match="IDENTITY_MISMATCH"):
        verify_filters(page, "2025-2026", 4, "2140")


def test_dependent_discovery_does_not_cross_product_and_restores_selection(monkeypatch):
    from contextlib import nullcontext
    from app.adapters import live_portal_extractor as module

    state = {"year": "2026-2027", "semester": "5", "class": "C5"}
    choices = {"2025-2026": ("4", "C4"), "2026-2027": ("5", "C5")}
    browser = Mock()
    extractor = module.LivePortalExtractor()
    monkeypatch.setattr(module, "sync_playwright", lambda: nullcontext(None))
    monkeypatch.setattr(extractor, "_get_portal_page", lambda p: (browser, object()))
    monkeypatch.setattr(extractor, "navigate_to_view", lambda *a: None)

    def opts(page, kind):
        if kind == "year":
            return [{"value": y, "label": y} for y in choices]
        sem, cls = choices[state["year"]]
        value = sem if kind == "semester" else cls
        return [{"value": value, "label": value}]

    def choose_value(page, kind, value):
        assert value in {o["value"] for o in opts(page, kind)}
        state[kind] = value
        if kind == "year":
            state["semester"], state["class"] = choices[value]

    def verify(page, year, sem, cls):
        assert state == {"year": year, "semester": str(sem), "class": cls}

    monkeypatch.setattr(module, "options", opts)
    monkeypatch.setattr(module, "choose", choose_value)
    monkeypatch.setattr(
        module, "selected", lambda page, kind: (state[kind], state[kind])
    )
    monkeypatch.setattr(module, "verify_filters", verify)
    rows = extractor.discover_historical_combinations()
    assert [
        (row["academic_year"], row["semester"], row["class_id"]) for row in rows
    ] == [("2025-2026", "4", "C4"), ("2026-2027", "5", "C5")]
    assert state == {"year": "2026-2027", "semester": "5", "class": "C5"}
    browser.close.assert_called_once()


def test_explicit_month_rejects_other_year_or_month():
    from datetime import date

    payload = SimpleNamespace(
        academic_year="2025-2026",
        semester=4,
        class_identifier="2140",
        observations=[SimpleNamespace(attendance_date=date(2025, 3, 1))],
    )
    candidate = result(batch=payload)
    del candidate.snapshot
    with pytest.raises(PortalSafetyError, match="MONTH_SCOPE_MISMATCH"):
        validate_result(candidate, "2025-2026", 4, "2140", "Class Four", "2026-03")


def test_search_rejects_route_changed_by_filter_reload():
    page = safe_page()
    with pytest.raises(PortalSafetyError, match="ROUTE_MISMATCH"):
        LivePortalExtractor()._search(page, SUBWISE_URL_PATH)
    page.goto.assert_not_called()


def test_attendance_readiness_ignores_hidden_profile_select():
    from app.adapters.portal_safety import SELECTORS

    page = Mock(url="https://mrei.icloudems.com" + SUBWISE_URL_PATH)
    body = Mock()
    body.inner_text.return_value = "Attendance"
    year = Mock()
    year.count.return_value = 1
    other = Mock()
    other.count.return_value = 0
    page.locator.side_effect = (
        lambda selector: body
        if selector == "body"
        else year
        if selector == SELECTORS["year"]
        else other
    )
    LivePortalExtractor().navigate_to_view(page, SUBWISE_URL_PATH, "select")
    year.wait_for.assert_called_once()
    page.wait_for_selector.assert_not_called()


def test_performance_scope_requires_year_class_exam_and_division(monkeypatch):
    from app.adapters import performance_portal as portal
    from types import SimpleNamespace

    page = Mock(url="https://mrei.icloudems.com" + portal.PERFORMANCE_PATH)
    monkeypatch.setattr(portal, "check_page", lambda page: None)
    values = {
        "year": ("2025-2026", "2025-2026"),
        "class": ("SYNTHETIC4", "Synthetic Sem 4"),
        "exam_session": ("SYNTHETIC-EXAM", "Synthetic Exam"),
        "exam_type": ("3", "Internal"),
        "division": ("A", "A"),
    }
    monkeypatch.setattr(portal, "selected", lambda page, kind: values[kind])
    monkeypatch.setattr(
        portal, "options", lambda page, kind: [{"value": "A", "label": "A"}]
    )
    term = SimpleNamespace(
        academic_year="2025-2026", semester_number=4, class_identifier="SYNTHETIC4"
    )
    portal.validate_scope(page, term, "SYNTHETIC-EXAM", "3", "A")
    with pytest.raises(PortalSafetyError, match="DIVISION_MISMATCH"):
        portal.validate_scope(page, term, "SYNTHETIC-EXAM", "3", "B")
    with pytest.raises(PortalSafetyError, match="EXAM_SESSION_MISMATCH"):
        portal.validate_scope(page, term, "OTHER-EXAM", "3", "A")


def test_verified_unchanged_filters_do_not_trigger_redundant_reloads(monkeypatch):
    from app.adapters import live_portal_extractor as module

    page = Mock()
    monkeypatch.setattr(
        module,
        "selected",
        lambda page, kind: {
            "year": ("2025-2026", "Year"),
            "semester": ("4", "4"),
            "class": ("2508", "Class4"),
        }[kind],
    )
    choose_filter = Mock()
    verify = Mock()
    monkeypatch.setattr(module, "choose", choose_filter)
    monkeypatch.setattr(module, "verify_filters", verify)
    module.LivePortalExtractor()._apply_filters(page, "2025-2026", 4, "2508")
    choose_filter.assert_not_called()
    verify.assert_called_once_with(page, "2025-2026", 4, "2508")


def test_classify_daywise_outcomes():
    from app.adapters.portal_safety import DaywiseScopeOutcome, classify_daywise_html

    # 1. Empty / whitespace -> UNKNOWN
    assert classify_daywise_html("") == DaywiseScopeOutcome.UNKNOWN
    assert classify_daywise_html("   ") == DaywiseScopeOutcome.UNKNOWN

    # 2. Authentication required
    auth_html = "<html><body>Please login to continue. <input type='password' name='pwd'/></body></html>"
    assert classify_daywise_html(auth_html) == DaywiseScopeOutcome.AUTHENTICATION_REQUIRED

    # 3. Warning page (alert div without timetable table)
    warning_html = """
    <html>
      <body>
        <select name="acadyear"><option selected value="2026-2027">2026-2027</option></select>
        <select name="semNum"><option selected value="5">5</option></select>
        <div class="alert alert-warning">Warning: No attendance record found for the requested period.</div>
      </body>
    </html>
    """
    assert classify_daywise_html(warning_html) == DaywiseScopeOutcome.WARNING_PAGE

    # 4. Explicit empty result
    empty_html = """
    <html>
      <body>
        <select name="acadyear"><option selected value="2026-2027">2026-2027</option></select>
        <select name="semNum"><option selected value="5">5</option></select>
        <div id="content">Zero records found for the selected query.</div>
      </body>
    </html>
    """
    assert classify_daywise_html(empty_html) == DaywiseScopeOutcome.EXPLICIT_EMPTY_RESULT

    # 5. Unverified source (missing filters)
    missing_filter_html = "<html><body><table id='daywise'><tr><th>Date</th></tr></table></body></html>"
    assert classify_daywise_html(missing_filter_html) == DaywiseScopeOutcome.UNVERIFIED_SOURCE

    # 6. Parser failure (malformed table)
    bad_table_html = """
    <html>
      <body>
        <select name="acadyear"><option selected value="2026-2027">2026-2027</option></select>
        <select name="semNum"><option selected value="5">5</option></select>
        <table id="daywise"><tr><td>corrupted</td></tr></table>
      </body>
    </html>
    """
    assert classify_daywise_html(bad_table_html) == DaywiseScopeOutcome.PARSER_FAILURE


def test_choose_select2_sync_and_retry_success():
    """Verify choose() attempts Select2 jQuery sync and succeeds when selection settles."""
    page = Mock(url="https://mrei.icloudems.com/corecampus/student/attendance/myattendance.php")
    page.locator.return_value.inner_text.return_value = "Attendance View"
    page.locator.return_value.count.return_value = 0

    ctrl = Mock()
    ctrl.count.return_value = 1
    # options mock
    ctrl.evaluate.side_effect = [
        [{"value": "01", "label": "January"}, {"value": "02", "label": "February"}],  # options()
        None,  # jQuery trigger evaluate
        [{"value": "02", "label": "February"}],  # 1st selected() check (stale)
        None,  # retry jQuery trigger evaluate
        [{"value": "01", "label": "January"}],  # 2nd selected() check (settled)
    ]

    def mock_locator(selector):
        if "month" in selector:
            return ctrl
        loc = Mock()
        loc.count.return_value = 0
        loc.inner_text.return_value = "Normal Page"
        return loc

    page.locator.side_effect = mock_locator

    # Should succeed without raising PortalSafetyError
    choose(page, "month", "01")
    assert ctrl.select_option.call_count == 2


def test_choose_persistent_mismatch_raises_fail_closed():
    """Verify choose() raises FILTER_SELECTION_MISMATCH if value remains mismatched after retry."""
    page = Mock(url="https://mrei.icloudems.com/corecampus/student/attendance/myattendance.php")
    page.locator.return_value.inner_text.return_value = "Attendance View"
    page.locator.return_value.count.return_value = 0

    ctrl = Mock()
    ctrl.count.return_value = 1
    ctrl.evaluate.side_effect = [
        [{"value": "01", "label": "January"}, {"value": "02", "label": "February"}],  # options()
        None,  # jQuery trigger evaluate
        [{"value": "02", "label": "February"}],  # 1st selected() check
        None,  # retry jQuery trigger evaluate
        [{"value": "02", "label": "February"}],  # 2nd selected() check (still mismatched)
    ]

    def mock_locator(selector):
        if "month" in selector:
            return ctrl
        loc = Mock()
        loc.count.return_value = 0
        loc.inner_text.return_value = "Normal Page"
        return loc

    page.locator.side_effect = mock_locator

    with pytest.raises(PortalSafetyError, match="FILTER_SELECTION_MISMATCH"):
        choose(page, "month", "01")
