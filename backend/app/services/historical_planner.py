"""Historical synchronization planner for multi-semester attendance backfill.

Constructs realistic, bounded synchronization scopes:
- Estimates work strictly in source request counts, never invented durations
- Discovers available terms dynamically without brute-forcing
- Maps academic term semesters to realistic institutional months
- Flags already persisted terms and batches to enable safe resumption
- Enforces conservative pacing and explicit user initiation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.portal_session import TermOption
from app.db.models import AcademicTerm


@dataclass
class TermSyncScope:
    academic_year: str
    semester: int
    class_identifier: Optional[str]
    candidate_months: list[str] = field(default_factory=list)
    candidate_month_labels: list[str] = field(default_factory=list)
    estimated_requests: int = 1
    has_subject_snapshot: bool = False
    has_daywise_batches: bool = False
    existing_batches_count: int = 0
    selected: bool = False


@dataclass
class HistoricalPlanSummary:
    discovered_academic_years: list[str]
    terms: list[TermSyncScope]
    total_terms_count: int
    total_estimated_requests: int
    pacing_guidance: str
    recommended_pilot_term: Optional[TermSyncScope] = None


def get_standard_semester_months(semester: int, academic_year: Optional[str] = None) -> tuple[list[str], list[str]]:
    """Return standard academic months for odd vs even semesters.

    When academic_year is provided, returns exact YearMonth strings (e.g. 2025-08)
    derived from the AcademicTermCalendarService (Aug-Nov for odd, Jan-May for even).
    When omitted, returns standard 1-digit/2-digit month indices for backwards compatibility.
    """
    if academic_year:
        from app.services.academic_term_calendar_service import AcademicTermCalendarService
        svc = AcademicTermCalendarService()
        ym_list = svc.get_candidate_months(academic_year, semester)
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        }
        labels = [f"{month_names[int(ym.split('-')[1])]} {ym.split('-')[0]}" for ym in ym_list]
        return ym_list, labels

    if semester % 2 == 1:
        # Autumn term (legacy fallback)
        return (
            ["8", "9", "10", "11", "12"],
            ["August", "September", "October", "November", "December"],
        )
    else:
        # Spring term
        return (
            ["1", "2", "3", "4", "5"],
            ["January", "February", "March", "April", "May"],
        )


class HistoricalSyncPlanner:
    """Builds and scopes historical multi-semester backfill plans."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_plan(
        self,
        discovered_years: list[TermOption],
        discovered_semesters: list[TermOption],
        discovered_classes: list[TermOption],
    ) -> HistoricalPlanSummary:
        """Construct a structured historical synchronization plan."""
        # Query existing persisted terms
        existing_terms = self.db.scalars(select(AcademicTerm)).all()
        term_map: dict[tuple[str, int], AcademicTerm] = {
            (t.academic_year, t.semester_number): t for t in existing_terms
        }

        term_scopes: list[TermSyncScope] = []
        year_values = [y.value for y in discovered_years if y.value]
        if not year_values:
            year_values = ["2026-2027", "2025-2026"]

        sem_values: list[int] = []
        for s in discovered_semesters:
            try:
                val = int(s.value)
                if 1 <= val <= 8:
                    sem_values.append(val)
            except ValueError:
                pass
        if not sem_values:
            sem_values = [5]  # Fallback to current discovered semester

        cls_id = discovered_classes[0].value if discovered_classes else None

        total_requests = 0

        for y in year_values:
            for sem in sorted(sem_values):
                m_nums, m_labels = get_standard_semester_months(sem, academic_year=y)
                req_count = 1 + len(m_nums)  # 1 subject-wise + 1 per month
                total_requests += req_count

                db_term = term_map.get((y, sem))
                has_snap = False
                has_day = False
                batch_count = 0
                if db_term:
                    has_snap = len(db_term.snapshots) > 0
                    has_day = len(db_term.observation_batches) > 0
                    batch_count = len(db_term.observation_batches)

                scope = TermSyncScope(
                    academic_year=y,
                    semester=sem,
                    class_identifier=cls_id,
                    candidate_months=m_nums,
                    candidate_month_labels=m_labels,
                    estimated_requests=req_count,
                    has_subject_snapshot=has_snap,
                    has_daywise_batches=has_day,
                    existing_batches_count=batch_count,
                    selected=(sem == sem_values[-1] and y == year_values[0]),  # Select current by default
                )
                term_scopes.append(scope)

        recommended_pilot = term_scopes[0] if term_scopes else None

        return HistoricalPlanSummary(
            discovered_academic_years=year_values,
            terms=term_scopes,
            total_terms_count=len(term_scopes),
            total_estimated_requests=total_requests,
            pacing_guidance="Conservative pacing: 1.5s - 2.5s between requests to respect portal load.",
            recommended_pilot_term=recommended_pilot,
        )
