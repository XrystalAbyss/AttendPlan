"""Adapters package for AttendPlan."""

from app.adapters.html_parser import ERPAttendanceParser, normalize_header
from app.adapters.fixture_loader import load_sample_snapshot

__all__ = ["ERPAttendanceParser", "normalize_header", "load_sample_snapshot"]
