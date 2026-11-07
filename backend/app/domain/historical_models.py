"""Domain models and enums for multi-semester historical discovery and backfill (F2-E).

Defines term discovery states, coverage classifications, reconciliation verdicts,
and multi-semester inventory models with zero network or database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TermDiscoveryStatus(str, Enum):
    """Status of discovering an academic term on the student portal."""

    AVAILABLE = "AVAILABLE"
    EMPTY = "EMPTY"
    INACCESSIBLE = "INACCESSIBLE"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    NOT_CHECKED = "NOT_CHECKED"


class CoverageState(str, Enum):
    """Granular state of historical attendance data imported for a term."""

    NOT_IMPORTED = "NOT_IMPORTED"
    DISCOVERED = "DISCOVERED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIAL = "PARTIAL"
    COMPLETE_FOR_REQUESTED_SCOPE = "COMPLETE_FOR_REQUESTED_SCOPE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TermReconciliationVerdict(str, Enum):
    """Reconciliation comparison between subject-wise summary and day-wise observations."""

    MATCHED = "MATCHED"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    SOURCE_DISCREPANCY = "SOURCE_DISCREPANCY"
    UNMAPPED_PERIODS = "UNMAPPED_PERIODS"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class HistoricalTermOption:
    """An individual selector option value and label extracted from portal DOM."""

    value: str
    label: str
    selected: bool = False


@dataclass
class HistoricalTermInventoryItem:
    """StructuredPersonal attendance history inventory item for a single academic term."""

    term_key: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str]
    display_label: str
    class_display_label: Optional[str]
    status: TermDiscoveryStatus
    has_subject_summary: bool = False
    has_daywise_data: bool = False
    existing_courses_count: int = 0
    existing_observations_count: int = 0
    attended_sum: int = 0
    delivered_sum: int = 0
    percentage: Optional[float] = None
    discovered_at: Optional[datetime] = None
    last_sync_timestamp: Optional[datetime] = None
    candidate_months: list[str] = field(default_factory=list)
    candidate_month_labels: list[str] = field(default_factory=list)
    estimated_requests: int = 1
    coverage_state: CoverageState = CoverageState.NOT_IMPORTED
    reconciliation_verdict: TermReconciliationVerdict = TermReconciliationVerdict.NOT_AVAILABLE
    error_message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoricalDiscoveryInventory:
    """Collection of all historical terms discovered across all academic years."""

    terms: list[HistoricalTermInventoryItem]
    discovered_years: list[str]
    total_terms_count: int
    available_terms_count: int
    imported_terms_count: int
    discovery_timestamp: datetime
    provenance: str = "VERIFIED_OFFLINE"


@dataclass
class HistoricalSyncPreview:
    """Pre-synchronization inspection and estimated workload summary."""

    selected_terms: list[HistoricalTermInventoryItem]
    total_selected_terms: int
    total_estimated_requests: int
    estimated_pacing_seconds: float
    pacing_guidance: str
    requires_user_approval: bool = True


@dataclass
class TermCoverageReport:
    """Granular coverage report tracking imported data completeness for a term."""

    term_id: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str]
    coverage_state: CoverageState
    has_subject_summary: bool
    subject_snapshot_count: int
    subject_courses_count: int
    candidate_months: list[str]
    candidate_month_labels: list[str]
    months_attempted: list[str]
    months_completed: list[str]
    unique_instructional_dates: int
    unique_instructional_periods: int
    mapped_periods: int
    unmapped_periods: int
    missing_or_unreported_periods: int
    source_errors_count: int
    reconciliation_verdict: TermReconciliationVerdict
    details: dict[str, Any] = field(default_factory=dict)

