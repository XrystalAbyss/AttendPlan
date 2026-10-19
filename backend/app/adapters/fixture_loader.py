"""Loader for offline sanitized portal fixtures."""

from pathlib import Path
from app.adapters.html_parser import ERPAttendanceParser
from app.domain.models import AttendanceSnapshot, DataProvenance

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_FIXTURE_PATH = FIXTURES_DIR / "sample_attendance.html"


def load_sample_snapshot(target_percentage: float = 75.0) -> AttendanceSnapshot:
    """Load and parse the sanitized historical sample snapshot."""
    if not SAMPLE_FIXTURE_PATH.exists():
        raise FileNotFoundError(f"Sample fixture not found at {SAMPLE_FIXTURE_PATH}")

    content = SAMPLE_FIXTURE_PATH.read_text(encoding="utf-8")
    parser = ERPAttendanceParser(target_percentage=target_percentage)
    return parser.parse_html(
        content,
        provenance=DataProvenance.SAMPLE_HISTORICAL,
        snapshot_id="snap-sample-fall-2026",
    )
