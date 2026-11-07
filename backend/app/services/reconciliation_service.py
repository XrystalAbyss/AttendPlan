"""Reconciliation service for AttendPlan F1.

Compares Subject-Wise snapshot totals against Date-Wise observation totals.
Never assumes one source is authoritative over another.
Flags discrepancies, unmapped observations, and coverage gaps.
"""

from __future__ import annotations
from app.services.current_observations import latest_observations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import ReconciliationStatus
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Course,
)


@dataclass(frozen=True)
class CourseReconciliationItem:
    course_code: str
    course_name: str
    subject_wise_attended: int
    subject_wise_delivered: int
    day_wise_attended: int
    day_wise_delivered: int
    attended_diff: int  # day_wise - subject_wise
    delivered_diff: int
    status: str  # "MATCHED" | "DISCREPANCY" | "UNMAPPED_ONLY" | "NO_DAY_DATA"


@dataclass(frozen=True)
class TermReconciliationReport:
    term_id: str
    academic_year: str
    semester_number: int
    subject_wise_available: bool
    day_wise_available: bool
    latest_snapshot_id: Optional[str]
    latest_batch_id: Optional[str]
    subject_wise_total_attended: int
    subject_wise_total_delivered: int
    day_wise_total_attended: int
    day_wise_total_delivered: int
    total_unmapped_observations: int
    coverage_start_date: Optional[date]
    coverage_end_date: Optional[date]
    reconciliation_status: ReconciliationStatus
    status_explanation: str
    course_breakdown: list[CourseReconciliationItem]


class ReconciliationService:
    """Service reconciling subject-wise and day-wise attendance data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def reconcile_term(self, term_id: str) -> TermReconciliationReport:
        """Alias for generate_reconciliation_report."""
        return self.generate_reconciliation_report(term_id)

    def generate_reconciliation_report(self, term_id: str) -> TermReconciliationReport:
        term = self.db.get(AcademicTerm, term_id)
        if not term:
            raise ValueError(f"Academic term not found: {term_id}")


        # 1. Fetch latest Subject-Wise Snapshot
        latest_snap_stmt = (
            select(AttendanceSnapshot)
            .where(AttendanceSnapshot.academic_term_id == term_id)
            .order_by(AttendanceSnapshot.captured_at.desc())
        )
        latest_snapshot = self.db.scalars(latest_snap_stmt).first()

        # 2. Fetch all Observation Batches
        batches_stmt = (
            select(AttendanceObservationBatch)
            .where(AttendanceObservationBatch.academic_term_id == term_id)
            .order_by(AttendanceObservationBatch.observed_at.desc())
        )
        batches = self.db.scalars(batches_stmt).all()
        latest_batch = batches[0] if batches else None

        # 3. Handle Insufficient Data Cases
        has_snap = latest_snapshot is not None
        has_day = len(batches) > 0

        if not has_snap and not has_day:
            return TermReconciliationReport(
                term_id=term_id,
                academic_year=term.academic_year,
                semester_number=term.semester_number,
                subject_wise_available=False,
                day_wise_available=False,
                latest_snapshot_id=None,
                latest_batch_id=None,
                subject_wise_total_attended=0,
                subject_wise_total_delivered=0,
                day_wise_total_attended=0,
                day_wise_total_delivered=0,
                total_unmapped_observations=0,
                coverage_start_date=None,
                coverage_end_date=None,
                reconciliation_status=ReconciliationStatus.INSUFFICIENT_DATA,
                status_explanation="No subject-wise snapshots or day-wise observations recorded for this term.",
                course_breakdown=[],
            )

        # 4. Aggregate Subject-Wise by Course
        snap_totals: dict[str, tuple[int, int]] = {}  # course_id -> (att, del)
        snap_tot_att = 0
        snap_tot_del = 0

        if latest_snapshot:
            rows_stmt = select(AttendanceSnapshotRow).where(
                AttendanceSnapshotRow.snapshot_id == latest_snapshot.id
            )
            for r in self.db.scalars(rows_stmt):
                snap_totals[r.course_id] = (r.attended_periods, r.delivered_periods)
                snap_tot_att += r.attended_periods
                snap_tot_del += r.delivered_periods

        # 5. Aggregate Day-Wise by Course
        day_totals: dict[str, tuple[int, int]] = {}  # course_id -> (att, del)
        day_tot_att = 0
        day_tot_del = 0
        unmapped_count = 0

        # Query all observations for this term
        obs_stmt = select(AttendancePeriodObservation).where(
            AttendancePeriodObservation.academic_term_id == term_id
        )
        all_obs = latest_observations(self.db.scalars(obs_stmt).all())

        for obs in all_obs:
            if obs.delivered_period_count == 0:
                continue

            day_tot_att += obs.attended_period_count
            day_tot_del += obs.delivered_period_count

            if obs.course_id:
                prev_att, prev_del = day_totals.get(obs.course_id, (0, 0))
                day_totals[obs.course_id] = (
                    prev_att + obs.attended_period_count,
                    prev_del + obs.delivered_period_count,
                )
            else:
                unmapped_count += obs.delivered_period_count

        # Coverage dates
        cov_start = min((b.coverage_start_date for b in batches), default=None)
        cov_end = max((b.coverage_end_date for b in batches), default=None)

        # 6. Build Course-by-Course Comparison
        term_courses = self.db.scalars(
            select(Course).where(Course.academic_term_id == term_id)
        ).all()

        breakdown: list[CourseReconciliationItem] = []

        for c in term_courses:
            s_att, s_del = snap_totals.get(c.id, (0, 0))
            d_att, d_del = day_totals.get(c.id, (0, 0))

            att_diff = d_att - s_att
            del_diff = d_del - s_del

            if not has_day:
                c_status = "NO_DAY_DATA"
            elif att_diff == 0 and del_diff == 0:
                c_status = "MATCHED"
            else:
                c_status = "DISCREPANCY"

            breakdown.append(
                CourseReconciliationItem(
                    course_code=c.course_code,
                    course_name=c.course_name,
                    subject_wise_attended=s_att,
                    subject_wise_delivered=s_del,
                    day_wise_attended=d_att,
                    day_wise_delivered=d_del,
                    attended_diff=att_diff,
                    delivered_diff=del_diff,
                    status=c_status,
                )
            )

        # 7. Evaluate Date Scope Compatibility
        is_scope_compatible = True
        scope_reason = ""

        snap_start = latest_snapshot.reporting_start_date if latest_snapshot else None
        snap_end = latest_snapshot.reporting_end_date if latest_snapshot else None

        if snap_start and snap_end and cov_start and cov_end:
            if cov_start > snap_start or cov_end < snap_end:
                is_scope_compatible = False
                scope_reason = (
                    f"Day-wise coverage ({cov_start.isoformat()} to {cov_end.isoformat()}) "
                    f"represents a partial subset of subject-wise reporting window ({snap_start.isoformat()} to {snap_end.isoformat()})."
                )
        elif cov_start and cov_end and snap_tot_del > 0 and day_tot_del < (snap_tot_del * 0.7) and (cov_end - cov_start).days < 60:
            is_scope_compatible = False
            scope_reason = (
                f"Day-wise coverage ({cov_start.isoformat()} to {cov_end.isoformat()}) represents a partial calendar window "
                f"({day_tot_del} delivered periods) compared to full-term subject-wise totals ({snap_tot_del} delivered periods)."
            )

        # 8. Evaluate Reconciliation Status
        if not has_snap:
            rec_status = ReconciliationStatus.PARTIAL_COVERAGE
            explanation = "Day-wise observations exist, but no subject-wise summary snapshot has been imported."
        elif not has_day:
            rec_status = ReconciliationStatus.PARTIAL_COVERAGE
            explanation = "Subject-wise snapshot exists, but no day-wise timetable observations have been imported."
        elif (
            snap_tot_att == day_tot_att
            and snap_tot_del == day_tot_del
            and unmapped_count == 0
            and all(c.status == "MATCHED" for c in breakdown)
        ):
            rec_status = ReconciliationStatus.MATCHED
            explanation = "Total delivered and attended periods across subject-wise and day-wise datasets match exactly (100% verified)."
        elif not is_scope_compatible:
            rec_status = ReconciliationStatus.SCOPE_MISMATCH
            explanation = (
                f"Scope non-comparability detected: {scope_reason} "
                "Totals are not directly comparable; this reflects partial date window extraction rather than a data integrity discrepancy."
            )
        elif unmapped_count > 0 and (snap_tot_del == day_tot_del + unmapped_count):
            rec_status = ReconciliationStatus.PARTIAL_COVERAGE
            explanation = f"Observation totals match after accounting for {unmapped_count} unmapped period(s)."
        else:
            rec_status = ReconciliationStatus.DISCREPANCY
            explanation = (
                f"Count divergence detected under comparable scopes: Subject-Wise ({snap_tot_att}/{snap_tot_del}) vs "
                f"Day-Wise ({day_tot_att}/{day_tot_del}). "
                "Possible causes: faculty corrections, unmapped period blocks, or missed attendance updates."
            )

        return TermReconciliationReport(
            term_id=term_id,
            academic_year=term.academic_year,
            semester_number=term.semester_number,
            subject_wise_available=has_snap,
            day_wise_available=has_day,
            latest_snapshot_id=latest_snapshot.id if latest_snapshot else None,
            latest_batch_id=latest_batch.id if latest_batch else None,
            subject_wise_total_attended=snap_tot_att,
            subject_wise_total_delivered=snap_tot_del,
            day_wise_total_attended=day_tot_att,
            day_wise_total_delivered=day_tot_del,
            total_unmapped_observations=unmapped_count,
            coverage_start_date=cov_start,
            coverage_end_date=cov_end,
            reconciliation_status=rec_status,
            status_explanation=explanation,
            course_breakdown=breakdown,
        )
