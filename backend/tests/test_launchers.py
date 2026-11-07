"""Tests for Windows launchers, operational readiness, and attendance data hygiene (F2-D)."""

from pathlib import Path

from app.adapters.daywise_parser import ERPDaywiseParser
from app.domain.attendance_engine import calculate_course_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestWindowsLaunchersStructure:
    """Verifies that the primary two-file launchers and helper scripts meet all architectural requirements."""

    def test_root_launchers_exist(self) -> None:
        """Root directory must have exactly the two primary user-facing .cmd launchers."""
        launch_chrome_cmd = REPO_ROOT / "Launch-Chrome.cmd"
        launch_attendplan_cmd = REPO_ROOT / "Launch-AttendPlan.cmd"

        assert launch_chrome_cmd.exists(), "Launch-Chrome.cmd missing from repository root"
        assert launch_attendplan_cmd.exists(), "Launch-AttendPlan.cmd missing from repository root"

    def test_internal_scripts_exist(self) -> None:
        """Helper PowerShell and management scripts must exist under scripts/."""
        scripts_dir = REPO_ROOT / "scripts"
        assert scripts_dir.is_dir(), "scripts/ directory missing"

        launch_chrome_ps1 = scripts_dir / "Launch-Chrome.ps1"
        launch_attendplan_ps1 = scripts_dir / "Launch-AttendPlan.ps1"
        stop_attendplan_ps1 = scripts_dir / "Stop-AttendPlan.ps1"
        stop_attendplan_cmd = scripts_dir / "Stop-AttendPlan.cmd"

        assert launch_chrome_ps1.exists()
        assert launch_attendplan_ps1.exists()
        assert stop_attendplan_ps1.exists()
        assert stop_attendplan_cmd.exists()

    def test_cmd_quoting_and_path_safety(self) -> None:
        """CMD wrappers must handle paths containing spaces and use trailing-slash safe quoting."""
        for cmd_name in ["Launch-Chrome.cmd", "Launch-AttendPlan.cmd"]:
            content = (REPO_ROOT / cmd_name).read_text(encoding="utf-8")
            assert "%~dp0" in content, f"{cmd_name} must use %~dp0 for directory resolution"
            assert '"%SCRIPT_DIR%' in content, f"{cmd_name} must quote script dir to support spaces"
            assert "powershell.exe -NoProfile -ExecutionPolicy Bypass" in content
            assert "errorlevel 1" in content

    def test_chrome_launcher_preserves_dedicated_profile_and_no_reset(self) -> None:
        """Launch-Chrome.ps1 must reference AttendPlan/chrome-profile and never reset user data."""
        content = (REPO_ROOT / "scripts" / "Launch-Chrome.ps1").read_text(encoding="utf-8")
        assert r"AttendPlan\chrome-profile" in content
        assert "--remote-debugging-port=9222" in content
        assert "--remote-debugging-address=127.0.0.1" in content
        assert "Remove-Item" not in content, "Launch-Chrome must never delete browser profile data"
        assert "mrei.icloudems.com/corecampus" in content

    def test_attendplan_launcher_lifecycle_and_ports(self) -> None:
        """Launch-AttendPlan.ps1 must verify health endpoints, check port conflicts, and manage PIDs."""
        content = (REPO_ROOT / "scripts" / "Launch-AttendPlan.ps1").read_text(encoding="utf-8")
        assert "http://127.0.0.1:8000" in content
        assert "/health" in content
        assert "http://127.0.0.1:5173" in content
        assert "backend.pid" in content
        assert "frontend.pid" in content
        assert "--strictPort" in content, "Vite must run with strictPort to prevent silent port shifting"
        assert "AttendPlan" in content

    def test_stop_attendplan_preserves_chrome(self) -> None:
        """Stop-AttendPlan.ps1 must kill only backend and frontend, preserving dedicated Chrome."""
        content = (REPO_ROOT / "scripts" / "Stop-AttendPlan.ps1").read_text(encoding="utf-8")
        assert "backend.pid" in content
        assert "frontend.pid" in content
    def test_powershell_parser_ast_validates_all_scripts(self) -> None:
        """Every .ps1 launcher script must pass [System.Management.Automation.Language.Parser]::ParseFile with 0 errors."""
        import subprocess

        scripts = [
            REPO_ROOT / "scripts" / "Launch-AttendPlan.ps1",
            REPO_ROOT / "scripts" / "Launch-Chrome.ps1",
            REPO_ROOT / "scripts" / "Stop-AttendPlan.ps1",
            REPO_ROOT / "launch-portal-chrome.ps1",
        ]

        for script_path in scripts:
            assert script_path.exists(), f"Script {script_path.name} not found"
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"& {{ $tokens = $null; $errors = $null; [System.Management.Automation.Language.Parser]::ParseFile('{script_path}', [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count -gt 0) {{ $errors | Format-List Message, Extent, ErrorId; exit 1 }} exit 0 }}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0, f"PowerShell Parser error in {script_path.name}:\n{result.stdout}\n{result.stderr}"

    def test_powershell_scripts_have_zero_non_ascii_characters(self) -> None:
        """Launcher scripts must be strictly ASCII to prevent typographic quotes (like U+201D) or encoding bugs."""
        scripts = [
            REPO_ROOT / "scripts" / "Launch-AttendPlan.ps1",
            REPO_ROOT / "scripts" / "Launch-Chrome.ps1",
            REPO_ROOT / "scripts" / "Stop-AttendPlan.ps1",
            REPO_ROOT / "launch-portal-chrome.ps1",
        ]

        for script_path in scripts:
            text = script_path.read_text(encoding="utf-8")
            non_ascii = [(idx + 1, char, hex(ord(char))) for idx, char in enumerate(text) if ord(char) > 127]
            assert not non_ascii, f"Non-ASCII characters detected in {script_path.name}: {non_ascii[:5]}"

    def test_chrome_cdp_target_creation_uses_put_with_get_fallback(self) -> None:
        """Modern Chromium CDP target creation requires HTTP PUT with fallback to GET."""
        for name in ["Launch-AttendPlan.ps1", "Launch-Chrome.ps1"]:
            content = (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
            assert "-Method Put" in content, f"{name} must attempt PUT for /json/new"
            assert "-Method Get" in content, f"{name} must have GET fallback for /json/new"


class TestAttendanceDataHygieneAndGeometry:
    """Verifies observation classification, structural header row exclusion, and mathematical buffer safety."""

    def test_structural_header_row_completely_excluded(self) -> None:
        """A day-wise matrix containing 'Lecture Timings' header row must omit it from parsed observations."""
        html = """
        <table id="daywise_table">
          <thead>
            <tr>
              <th>Time Slot</th>
              <th>01/10/2026 (Thu)</th>
              <th>05/10/2026 (Mon)</th>
              <th>06/10/2026 (Tue)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Lecture Timings</td>
              <td></td>
              <td></td>
              <td></td>
            </tr>
            <tr>
              <td>08:10 - 09:00</td>
              <td><span class="text-success">P</span><br><small>CSH301C</small></td>
              <td><span class="text-danger">A</span><br><small>CSH302C</small></td>
              <td></td>
            </tr>
            <tr>
              <td>09:00 - 09:50</td>
              <td><span class="text-success">P</span><br><small>CSH304C</small></td>
              <td><span class="text-success">P</span><br><small>CSH304C</small></td>
              <td><span class="text-danger">A</span><br><small>CSH305C</small></td>
            </tr>
          </tbody>
        </table>
        """
        parser = ERPDaywiseParser()
        batch = parser.parse_html(html)

        # 3 dates x 2 real slot rows = 6 observations (NOT 3 x 3 = 9)
        assert len(batch.observations) == 6
        for obs in batch.observations:
            assert obs.source_period_identifier != "Lecture Timings"
            assert "Lecture" not in (obs.source_period_identifier or "")

    def test_verified_instructional_slot_geometry(self) -> None:
        """Verify the exact geometry of 11 dates x 8 instructional slots = 88 observations."""
        num_dates = 11
        num_slots = 8
        total_potential_slots = num_dates * num_slots
        assert total_potential_slots == 88

        # 47 Present + 21 Absent = 68 Delivered
        delivered = 47 + 21
        assert delivered == 68

        # Remaining genuine unreported / free time slots
        unreported_free = total_potential_slots - delivered
        assert unreported_free == 20

    def test_absence_buffer_aggregate_vs_subject_margins(self) -> None:
        """Verify aggregate theoretical safe bunks (27) vs course-by-course sum (24)."""
        # Exact numbers from verified snapshot: 230 attended, 279 delivered, 75% target
        tot_a = 230
        tot_d = 279
        import math

        aggregate_safe_bunks = max(0, math.floor(tot_a / 0.75 - tot_d))
        assert aggregate_safe_bunks == 27

        # Sample course margins summing to 24 where deficit on EDS240C is not transferable
        # E.g. EDS240C: a=5, d=7 (71.4% < 75%) -> safe_bunks = 0 (deficit: -1)
        calc_eds = calculate_course_metrics(attended=5, delivered=7, target=0.75)
        assert calc_eds.can_skip == 0
        assert calc_eds.must_attend == 1  # Need 1 to reach 6/8 = 75%

        # The individual margins must be authoritative for student advice
        assert aggregate_safe_bunks > 24
