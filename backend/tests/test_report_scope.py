"""Synthetic report-scope regression coverage; no live browser or student data."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.adapters import live_portal_extractor as module
from app.adapters.live_portal_extractor import LivePortalExtractor, SUBWISE_URL_PATH
from app.adapters.portal_safety import PortalSafetyError


def test_credit_decimal_is_not_read_as_attendance_percentage():
    snapshot = SimpleNamespace(
        courses=[SimpleNamespace(code="TEST101", percent=75.0)],
        summary=SimpleNamespace(
            total_attended=3, total_delivered=4, overall_percentage=75.0
        ),
    )
    html = "<table><tr><th>Code</th><th>Credit</th><th>Percent</th></tr><tr><td>TEST101</td><td>3.00</td><td>75.00</td><td>Other</td></tr></table>"
    result = LivePortalExtractor()._validate_subject_wise_snapshot(html, snapshot)
    assert result.is_valid and not result.percentage_deviations
    mismatch = LivePortalExtractor()._validate_subject_wise_snapshot(
        html.replace("75.00", "50.00"), snapshot
    )
    assert len(mismatch.percentage_deviations) == 1


@pytest.mark.parametrize(
    "submitted_year,echo",
    [("2025-2026", []), ("2024-2025", []), ("2025-2026", ["wrong"])],
)
def test_report_bound_to_actual_post_and_rejects_conflicting_echo(
    monkeypatch, submitted_year, echo
):
    page = MagicMock(url="https://mrei.icloudems.com" + SUBWISE_URL_PATH)
    page.locator.return_value.count.return_value = 1
    page.locator.return_value.evaluate.return_value = page.url
    request = MagicMock(
        url=page.url,
        post_data=f"acadyear={submitted_year}&semNum%5B%5D=4&classid%5B%5D=2508",
    )
    request.response.return_value = SimpleNamespace(ok=True, request=request)
    page.expect_request.return_value.__enter__.return_value.value = request
    monkeypatch.setattr(module, "check_page", lambda page: None)
    monkeypatch.setattr(
        module,
        "selected",
        lambda page, kind: {
            "year": ("2025-2026", "2025-2026"),
            "semester": ("4", "4"),
            "class": ("2508", "Synthetic Class Four"),
        }[kind],
    )
    control = MagicMock()
    control.evaluate.return_value = echo
    monkeypatch.setattr(module, "control", lambda page, kind: control)
    if submitted_year == "2025-2026" and not echo:
        assert (
            LivePortalExtractor()._search(page, SUBWISE_URL_PATH)["class"][0] == "2508"
        )
    else:
        with pytest.raises(PortalSafetyError):
            LivePortalExtractor()._search(page, SUBWISE_URL_PATH)


def test_course_code_in_another_rows_short_name_is_not_a_percentage_match():
    snapshot = SimpleNamespace(
        courses=[SimpleNamespace(code="TEST101", percent=75.0)],
        summary=SimpleNamespace(
            total_attended=3, total_delivered=4, overall_percentage=75.0
        ),
    )
    html = "<table><tr><th>Course Code</th><th>Short Name</th><th>Credit</th><th>Percent</th></tr><tr><td>TEST101</td><td>Theory</td><td>3.0</td><td>75.0</td></tr><tr><td>TEST102</td><td>TEST101</td><td>1.0</td><td>20.0</td></tr></table>"
    result = LivePortalExtractor()._validate_subject_wise_snapshot(html, snapshot)
    assert result.is_valid and not result.percentage_deviations
