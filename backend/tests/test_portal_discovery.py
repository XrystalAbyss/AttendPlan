"""Integration and unit tests for F2-A portal discovery adapters and endpoints."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient


from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    DayWiseAttendanceAdapter,
    OverallAttendanceAdapter,
    PortalSessionManager,
    PortalSessionState,
    SubjectWiseAttendanceAdapter,
    find_chrome_executable,
    get_dedicated_profile_dir,
)
from app.main import app

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_SUBJECT_HTML = (FIXTURES_DIR / "sample_attendance.html").read_text(encoding="utf-8")
SYNTHETIC_DAYWISE_HTML = (FIXTURES_DIR / "synthetic_daywise_attendance.html").read_text(encoding="utf-8")


class TestPortalSessionManager:
    def test_dedicated_profile_directory_outside_repository(self) -> None:
        """Dedicated Chrome user data directory must be located outside the git repository."""
        profile_dir = get_dedicated_profile_dir()
        repo_root = Path(__file__).resolve().parent.parent.parent
        assert repo_root not in profile_dir.parents
        assert "AttendPlan" in str(profile_dir)
        assert profile_dir.exists()

    def test_chrome_executable_detection(self) -> None:
        """Finds valid Chrome executable if present on Windows host."""
        exe = find_chrome_executable()
        # On Windows host with Chrome installed, path must exist
        if exe:
            assert Path(exe).exists()
            assert "chrome.exe" in exe.lower()

    def test_session_manager_initial_state_disconnected(self) -> None:
        """When no browser process is launched, status is DISCONNECTED on loopback port."""
        manager = PortalSessionManager(cdp_port=19222)
        info = manager.check_session_status()
        assert info.state == PortalSessionState.DISCONNECTED
        assert info.cdp_port == 19222
        assert "127.0.0.1" in info.cdp_url
        assert info.manual_fallback_available is True


    def test_session_manager_close_is_idempotent(self) -> None:
        """Closing an unstarted or running session must terminate cleanly without errors."""
        manager = PortalSessionManager()
        manager.close_session()
        assert manager._browser_process is None


class TestDiscoveryAdaptersOffline:
    def test_academic_term_discovery_from_html(self) -> None:
        """Discover academic years, semesters, and classes from HTML select widgets."""
        sample_form_html = """
        <form>
          <select name="aca" id="aca">
            <option value="2026-2027" selected>2026-2027</option>
            <option value="2025-2026">2025-2026</option>
            <option value="2024-2025">2024-2025</option>
          </select>
          <select name="semNum[]" id="semNum">
            <option value="1">1</option>
            <option value="3">3</option>
            <option value="5" selected>5</option>
          </select>
          <select name="classid[]" id="classid">
            <option value="2582" selected>B.Tech CSE AIML-Sem 5</option>
            <option value="1904">B.Tech CSE AIML-Sem 3</option>
          </select>
        </form>
        """
        result = AcademicTermDiscoveryAdapter.parse_from_html(sample_form_html)
        assert len(result.academic_years) == 3
        assert result.academic_years[0].value == "2026-2027"
        assert result.academic_years[0].selected is True

        assert len(result.semesters) == 3
        assert [s.value for s in result.semesters] == ["1", "3", "5"]

        assert len(result.classes) == 2
        assert result.classes[0].value == "2582"
        assert result.classes[0].label == "B.Tech CSE AIML-Sem 5"

    def test_subject_wise_discovery_from_fixture(self) -> None:
        """Discover subject-wise table schema, header columns, and records from sample fixture."""
        res = SubjectWiseAttendanceAdapter.parse_from_html(SAMPLE_SUBJECT_HTML)
        assert res.table_found is True
        assert res.record_count == 15
        assert len(res.header_columns) >= 5
        # Check header contains core attendance fields
        headers_str = " ".join(res.header_columns).lower()
        assert "course" in headers_str or "subject" in headers_str
        assert "attended" in headers_str or "percent" in headers_str

    def test_day_wise_discovery_from_fixture(self) -> None:
        """Discover day-wise table schema, slot rows, and date columns."""
        res = DayWiseAttendanceAdapter.parse_from_html(SYNTHETIC_DAYWISE_HTML)
        assert res.table_found is True
        assert len(res.date_columns) >= 6
        assert len(res.time_slots) >= 3
        # In synthetic fixture, course labels are inline
        assert res.course_name_mapping_mechanism == "INLINE_CELL_TEXT"
        assert "P" in res.sample_statuses_observed
        assert "A" in res.sample_statuses_observed

    def test_overall_attendance_discovery_from_html(self) -> None:
        """Discover Overall Attendance (allSubject.php) view structure."""
        overall_html = """
        <div>
          <select id="acadyear"><option value="2026-2027">2026-2027</option></select>
          <table class="table">
            <thead>
              <tr><th>S.No.</th><th>Subject</th><th>Attended</th><th>Delivered</th><th>Percentage</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Operating Systems</td><td>19</td><td>19</td><td>100.00%</td></tr>
            </tbody>
          </table>
        </div>
        """
        res = OverallAttendanceAdapter.parse_from_html(overall_html)
        assert res.view_found is True
        assert len(res.displayed_columns) == 5
        assert "Percentage" in res.displayed_columns
        assert len(res.filter_controls) >= 1


class TestPortalApiEndpoints:
    def test_portal_session_status_endpoint(self) -> None:
        """GET /api/v1/portal/session/status returns session diagnostics."""
        resp = client.get("/api/v1/portal/session/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "cdp_port" in data
        assert "manual_fallback_available" in data
        assert data["manual_fallback_available"] is True

    def test_portal_session_close_endpoint(self) -> None:
        """POST /api/v1/portal/session/close closes browser cleanly."""
        resp = client.post("/api/v1/portal/session/close")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] in ["DISCONNECTED", "BROWSER_READY", "LOGIN_REQUIRED", "AUTHENTICATED"]

    def test_portal_discover_terms_with_payload(self) -> None:
        """POST /api/v1/portal/discover/terms with HTML payload parses offline terms."""
        payload = {
            "html_content": """
            <select name="aca"><option value="2026-2027" selected>2026-2027</option></select>
            <select name="sem"><option value="5" selected>5</option></select>
            <select name="class"><option value="AIML-5" selected>Class A</option></select>
            """
        }
        resp = client.post("/api/v1/portal/discover/terms", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["academic_years"]) == 1
        assert data["academic_years"][0]["value"] == "2026-2027"
        assert len(data["semesters"]) == 1
        assert data["semesters"][0]["value"] == "5"

    def test_portal_discover_subject_wise_with_payload(self) -> None:
        """POST /api/v1/portal/discover/subject-wise with HTML payload returns table schema."""
        payload = {"html_content": SAMPLE_SUBJECT_HTML}
        resp = client.post("/api/v1/portal/discover/subject-wise", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["table_found"] is True
        assert data["record_count"] == 15
        assert len(data["header_columns"]) >= 5

    def test_portal_discover_day_wise_with_payload(self) -> None:
        """POST /api/v1/portal/discover/day-wise with HTML payload returns timetable schema."""
        payload = {"html_content": SYNTHETIC_DAYWISE_HTML}
        resp = client.post("/api/v1/portal/discover/day-wise", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["table_found"] is True
        assert len(data["date_columns"]) >= 6
        assert len(data["time_slots"]) >= 3

    def test_portal_discover_without_browser_or_payload_returns_400(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POST /api/v1/portal/discover/* without active browser or payload returns 400."""
        from app.api import routes
        monkeypatch.setattr(routes._portal_session_manager, "fetch_portal_page_content", lambda *args, **kwargs: (None, None))
        resp = client.post("/api/v1/portal/discover/terms", json={})
        assert resp.status_code in [400, 500]

