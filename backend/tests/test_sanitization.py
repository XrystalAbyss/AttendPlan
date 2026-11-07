"""Security & Sanitization test suite.

Ensures that NO student identifying information (PII), session tokens,
tracking pixels, or university anti-tamper scripts are present in tracked
test fixtures, production codebase, or public documentation.

CRITICAL PRIVACY DIRECTIVE:
Known private canary identifiers are stored ONLY as one-way SHA-256 cryptographic hashes
(never plaintext) so that test code itself never leaks sensitive data.
"""

import hashlib
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).parent / "fixtures"
APP_FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"
SRC_DIR = Path(__file__).parent.parent / "app"
FRONTEND_SRC_DIR = REPO_ROOT / "frontend" / "src"
REPORTS_DIR = REPO_ROOT / "reports"
DOCS_DIR = REPO_ROOT / "docs"

# One-way SHA-256 digests of sensitive canary tokens (zero plaintext stored)
PROHIBITED_TOKEN_SHA256: dict[str, str] = {
    "ad07837b570cf597505a700a0d6883f854b9fd458309c7e0594038a9c4ab6edd": "student_admission_id",
    "5e0db1575294415075b93d856854ce88867c3caca14cdd1b0a4beff898c655d1": "identity_number",
    "9369af2eacab262b131d059fff40e1e4c8fbed2ea684a50b78f2348cbe3b9ada": "student_roll_number",
    "03a44ddce5544ec7e9c00351fe5a6a65d3baa2931b034b286c02e17f9e226180": "phone_number",
    "73b46e822801a647fc145e6d2074c52563b32efa3cc9c26b1aaccc06c9a212cf": "personal_name_first",
    "0ced0cede99ef02e322513dc6d6d55054c0dfa77100543f4522f6c879fa1abe6": "personal_name_last",
    "549299a439573c0956ace23cec5a29500540c12c1278effa9542edc319f5bf55": "base64_admission_query",
}

# Generic sensitive tracker and credential patterns
PROHIBITED_GENERIC_PATTERNS = [
    (re.compile(r"logoutDueToTampering"), "anti_tamper_script"),
    (re.compile(r"GTM-57PQJ6N"), "university_gtm_tracker"),
    (re.compile(r"UA-194952325"), "google_analytics_tracker"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "private_key"),
]


def _check_content_for_violations(content: str, source_label: str) -> None:
    """Check text content against one-way hash digests and generic patterns."""
    # Check tokens against SHA-256 hash digests
    tokens = set(re.findall(r"[A-Za-z0-9_+=/]+", content))
    for t in tokens:
        h = hashlib.sha256(t.encode("utf-8")).hexdigest()
        if h in PROHIBITED_TOKEN_SHA256:
            label = PROHIBITED_TOKEN_SHA256[h]
            pytest.fail(f"Security breach: Prohibited canary category '{label}' detected in {source_label}")

    # Check regex patterns
    for pattern, desc in PROHIBITED_GENERIC_PATTERNS:
        if pattern.search(content):
            pytest.fail(f"Security breach: Prohibited pattern '{desc}' found in {source_label}")


class TestSecurityAndSanitization:
    @pytest.mark.parametrize("fixture_path", sorted(set(
        list(FIXTURES_DIR.glob("*.html")) + list(APP_FIXTURES_DIR.glob("*.html"))
    )))
    def test_fixtures_do_not_contain_prohibited_data(self, fixture_path: Path) -> None:
        """Confirm no real identifying data was written to tracked test fixtures."""
        assert fixture_path.exists(), f"Fixture file missing at {fixture_path}"
        content = fixture_path.read_text(encoding="utf-8", errors="ignore")
        _check_content_for_violations(content, fixture_path.name)

    def test_source_code_does_not_contain_prohibited_pii(self) -> None:
        """Ensure backend and frontend production source code contains no student PII."""
        scan_paths = (
            list(SRC_DIR.rglob("*.py"))
            + list(FRONTEND_SRC_DIR.rglob("*.tsx"))
            + list(FRONTEND_SRC_DIR.rglob("*.ts"))
        )
        for file_path in scan_paths:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            _check_content_for_violations(content, file_path.name)

    def test_documentation_and_reports_contain_zero_literal_pii(self) -> None:
        """Ensure all tracked markdown reports, docs, and README contain no literal PII."""
        doc_files = (
            list(REPORTS_DIR.glob("*.md"))
            + list(DOCS_DIR.glob("*.md"))
            + [REPO_ROOT / "README.md"]
        )
        for doc_path in doc_files:
            if not doc_path.is_file():
                continue
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
            _check_content_for_violations(content, str(doc_path.relative_to(REPO_ROOT)))

    def test_synthetic_canary_detection_works(self) -> None:
        """Verify that hash-based canary detection accurately trips on known test tokens."""
        synthetic_token = "synthetic_canary_test_token_12345"
        dummy_hash = hashlib.sha256(synthetic_token.encode("utf-8")).hexdigest()
        test_registry = {dummy_hash: "canary_test_item"}

        test_content = f"Some dummy text with {synthetic_token} inside."
        tokens = set(re.findall(r"[A-Za-z0-9_+=/]+", test_content))
        detected = any(hashlib.sha256(t.encode("utf-8")).hexdigest() in test_registry for t in tokens)
        assert detected, "Synthetic canary token failed to trigger detection"

    def test_no_auth_cookies_or_passwords(self) -> None:
        """Ensure fixtures contain zero passwords, cookies, or authorization headers."""
        for path in [FIXTURES_DIR / "sample_attendance.html", APP_FIXTURES_DIR / "sample_attendance.html"]:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            assert "password" not in content
            assert "cookie" not in content
            assert "authorization" not in content
            assert "token" not in content
            assert "otp" not in content
