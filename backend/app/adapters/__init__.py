"""Adapters package for AttendPlan."""

from app.adapters.fixture_loader import load_sample_snapshot
from app.adapters.html_parser import ERPAttendanceParser, normalize_header
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    DayWiseAttendanceAdapter,
    OverallAttendanceAdapter,
    PortalSessionManager,
    SubjectWiseAttendanceAdapter,
)

__all__ = [
    "ERPAttendanceParser",
    "normalize_header",
    "load_sample_snapshot",
    "LivePortalExtractor",
    "PortalSessionManager",
    "AcademicTermDiscoveryAdapter",
    "SubjectWiseAttendanceAdapter",
    "DayWiseAttendanceAdapter",
    "OverallAttendanceAdapter",
]

