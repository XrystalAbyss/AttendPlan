"""Security & Sanitization test suite.

Ensures that NO real student identifying information (PII), session tokens,
tracking pixels, or university anti-tamper scripts are present in tracked
test fixtures or production codebase.
"""

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
APP_FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"
SRC_DIR = Path(__file__).parent.parent / "app"
FRONTEND_SRC_DIR = Path(__file__).parent.parent.parent / "frontend" / "src"

# Known private student credentials and IDs from legacy dumps that must NEVER appear
PROHIBITED_STRINGS = [
    "[REDACTED_STUDENT_IDENTIFIER]",  # Real student admission number
    "[REDACTED_BASE64_ADMISSION_QUERY]",  # Base64 encoded student admission query
    "logoutDueToTampering",  # Client-side anti-debugging / tamper script
    "GTM-57PQJ6N",  # University GTM tracker
    "UA-194952325",  # Google Analytics ID
    "aws-sdk",  # AWS SDK scripts
    "debugger;",  # Active debugger pause loops
    "[REDACTED_IDENTITY_NUMBER]",  # Student identity
    "[REDACTED_STUDENT_ROLL_NO]",  # Student roll number
    "[REDACTED_STUDENT_PHONE]",  # Phone number
    "[REDACTED_PERSONAL_NAME]",  # Student first name
    "[REDACTED_PERSONAL_SURNAME]",  # Student last name
]


class TestSecurityAndSanitization:
    @pytest.mark.parametrize("fixture_path", sorted(set(
        list(FIXTURES_DIR.glob("*.html")) + list(APP_FIXTURES_DIR.glob("*.html"))
    )))
    def test_fixtures_do_not_contain_prohibited_data(self, fixture_path: Path) -> None:
        """Confirm no real identifying data was written to tracked test fixtures."""
        assert fixture_path.exists(), f"Fixture file missing at {fixture_path}"
        content = fixture_path.read_text(encoding="utf-8")

        for prohibited in PROHIBITED_STRINGS:
            assert prohibited not in content, (
                f"Security breach: Prohibited student PII or session artifact found in "
                f"{fixture_path.name}: '{prohibited}'"
            )

    def test_source_code_does_not_contain_prohibited_pii(self) -> None:
        """Ensure backend and frontend production source code contains no student PII."""
        scan_paths = list(SRC_DIR.rglob("*.py")) + list(FRONTEND_SRC_DIR.rglob("*.tsx")) + list(FRONTEND_SRC_DIR.rglob("*.ts"))
        for file_path in scan_paths:
            content = file_path.read_text(encoding="utf-8")
            for prohibited in PROHIBITED_STRINGS:
                assert prohibited not in content, (
                    f"Security breach: Prohibited student PII found in {file_path.name}: '{prohibited}'"
                )

    def test_no_auth_cookies_or_passwords(self) -> None:
        """Ensure fixtures contain zero passwords, cookies, or authorization headers."""
        for path in [FIXTURES_DIR / "sample_attendance.html", APP_FIXTURES_DIR / "sample_attendance.html"]:
            content = path.read_text(encoding="utf-8").lower()
            assert "password" not in content
            assert "cookie" not in content
            assert "authorization" not in content
            assert "token" not in content
            assert "otp" not in content
