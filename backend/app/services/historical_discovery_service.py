"""Historical term discovery service for AttendPlan F2-E.

Inspects portal DOM selection options, discovers available historical academic years,
semesters, and class identifiers without brute-forcing, and correlates with persisted
local database records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import PortalSafetyError
from app.db.models import SyncJob
from app.db.enums import SyncJobState
from sqlalchemy.orm import Session

from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    PortalSessionManager,
)
from app.db.models import (
    AcademicTerm,
    AttendancePeriodObservation,
    Course,
)
from app.domain.historical_models import (
    CoverageState,
    HistoricalDiscoveryInventory,
    HistoricalSyncPreview,
    HistoricalTermInventoryItem,
    TermCoverageReport,
    TermDiscoveryStatus,
    TermReconciliationVerdict,
)
from app.services.historical_planner import get_standard_semester_months
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)



def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HistoricalDiscoveryService:
    """Service discovering accessible academic terms and personal attendance history inventory."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.reconciliation_service = ReconciliationService(db)

    def discover_inventory_from_html(
        self,
        html_content: str,
        provenance: str = "VERIFIED_OFFLINE",
    ) -> HistoricalDiscoveryInventory:
        """Parse available selector combinations from a portal HTML page and construct inventory."""
        discovery = AcademicTermDiscoveryAdapter.parse_from_html(html_content)
        years = discovery.academic_years
        semesters = discovery.semesters
        classes = discovery.classes

        # Static HTML proves only the explicitly selected tuple, never dependent combinations.
        selected_years = [x for x in years if x.selected]
        selected_semesters = [x for x in semesters if x.selected]
        selected_classes = [x for x in classes if x.selected]
        rows = []
        if len(selected_years) == len(selected_semesters) == len(selected_classes) == 1:
            rows = [{"academic_year": selected_years[0].value, "semester": selected_semesters[0].value,
                     "class_id": selected_classes[0].value, "class_label": selected_classes[0].label}]
        return self._inventory_from_rows(rows, provenance, verified=False)

    def _inventory_from_rows(self, rows: list[dict[str, str]], provenance: str, verified: bool, reconcile: bool = True) -> HistoricalDiscoveryInventory:
        db_terms = self.db.scalars(select(AcademicTerm)).all()
        items = []
        for row in rows:
            if not row["semester"].isdigit():
                continue
            number = int(row["semester"])
            term = next((t for t in db_terms if t.academic_year == row["academic_year"]
                         and t.semester_number == number and t.class_identifier == row["class_label"]), None)
            item = self._correlate_term_item(
                row["academic_year"], number, row["class_id"], row["class_label"],
                TermDiscoveryStatus.AVAILABLE if verified else TermDiscoveryStatus.NOT_CHECKED, term,
                reconcile=reconcile,
            )
            item.details["selector_verified"] = verified
            items.append(item)
        unique = {t.term_key: t for t in items}
        terms = sorted(unique.values(), key=lambda t: (t.academic_year, t.semester_number, t.term_key))
        return HistoricalDiscoveryInventory(
            terms=terms, discovered_years=sorted({t.academic_year for t in terms}),
            total_terms_count=len(terms), available_terms_count=len(terms) if verified else 0,
            imported_terms_count=sum(t.has_subject_summary for t in terms),
            discovery_timestamp=utc_now(), provenance=provenance,
        )

    def get_discovered_term_labels(self) -> list[dict[str, Any]]:
        """Fast extraction of discovered term keys and labels without querying full attendance or lazy-loading observations."""
        job = self.db.scalars(select(SyncJob).where(
            SyncJob.source_scope == "HISTORICAL_SELECTOR_DISCOVERY",
            SyncJob.state == SyncJobState.COMPLETED.value,
        ).order_by(SyncJob.created_at.desc())).first()
        if job and job.details and "combinations" in job.details:
            seen_keys = set()
            res = []
            for row in job.details["combinations"]:
                sem_str = str(row.get("semester", "")).strip()
                if not sem_str.isdigit():
                    continue
                sem = int(sem_str)
                ay = row.get("academic_year", "").strip()
                cid = row.get("class_id") or "default"
                key = f"{ay}_s{sem}_{cid}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                res.append({"term_key": key, "label": f"Semester {sem} ({ay})", "selector_verified": True})
            return res

        terms = self.db.scalars(select(AcademicTerm)).all()
        seen_keys = set()
        res = []
        for t in terms:
            key = f"{t.academic_year}_s{t.semester_number}_{t.class_identifier or 'default'}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            res.append({
                "term_key": key,
                "label": f"Semester {t.semester_number} ({t.academic_year})",
                "selector_verified": False,
            })
        return res

    def get_persisted_inventory(self, reconcile: bool = True) -> HistoricalDiscoveryInventory:
        """Use the latest verified discovery across sessions; stored attendance is fallback only."""
        job = self.db.scalars(select(SyncJob).where(
            SyncJob.source_scope == "HISTORICAL_SELECTOR_DISCOVERY",
            SyncJob.state == SyncJobState.COMPLETED.value,
        ).order_by(SyncJob.created_at.desc())).first()
        if job and job.details:
            return self._inventory_from_rows(job.details["combinations"], "VERIFIED_SELECTOR_DISCOVERY", True, reconcile=reconcile)
        terms = self.db.scalars(select(AcademicTerm)).all()
        rows = [{"academic_year": t.academic_year, "semester": str(t.semester_number),
                 "class_id": t.class_identifier or "", "class_label": t.class_identifier or ""} for t in terms]
        return self._inventory_from_rows(rows, "LOCAL_DATABASE", False, reconcile=reconcile)

    def _correlate_term_item(
        self,
        academic_year: str,
        semester_number: int,
        class_id: Optional[str],
        class_label: Optional[str],
        status: TermDiscoveryStatus,
        db_term: Optional[AcademicTerm],
        reconcile: bool = True,
    ) -> HistoricalTermInventoryItem:
        """Calculate metrics, coverage, and reconciliation state for a term item."""
        term_key = f"{academic_year}_s{semester_number}_{class_id or 'default'}"
        display_label = f"Semester {semester_number} ({academic_year})"

        m_nums, m_labels = get_standard_semester_months(semester_number, academic_year=academic_year)
        req_count = 1 + len(m_nums)

        has_summary = False
        has_day = False
        courses_count = 0
        obs_count = 0
        attended_sum = 0
        delivered_sum = 0
        pct: Optional[float] = None
        last_sync: Optional[datetime] = None
        cov_state = CoverageState.NOT_IMPORTED
        rec_verdict = TermReconciliationVerdict.NOT_AVAILABLE

        if db_term:
            has_summary = len(db_term.snapshots) > 0
            has_day = len(db_term.observation_batches) > 0

            # Count courses
            courses = self.db.scalars(select(Course).where(Course.academic_term_id == db_term.id)).all()
            courses_count = len(courses)

            if has_summary:
                latest_snap = db_term.snapshots[-1]
                last_sync = latest_snap.captured_at
                for row in latest_snap.rows:
                    attended_sum += row.attended_periods
                    delivered_sum += row.delivered_periods
                if delivered_sum > 0:
                    pct = round((attended_sum / delivered_sum) * 100, 2)

            if has_day:
                for b in db_term.observation_batches:
                    obs_count += len(b.observations)

            # Determine coverage state
            if has_summary and has_day and obs_count > 0:
                cov_state = CoverageState.PARTIAL
            elif has_summary or has_day:
                cov_state = CoverageState.PARTIAL
            else:
                cov_state = CoverageState.DISCOVERED

            # Determine reconciliation verdict if both are present
            if reconcile and has_summary and has_day:
                try:
                    rep = self.reconciliation_service.reconcile_term(db_term.id)
                    rec_verdict = TermReconciliationVerdict(rep.reconciliation_status.value)
                except Exception:
                    rec_verdict = TermReconciliationVerdict.PARTIAL_COVERAGE

        else:
            cov_state = CoverageState.NOT_IMPORTED

        return HistoricalTermInventoryItem(
            term_key=term_key,
            academic_year=academic_year,
            semester_number=semester_number,
            class_identifier=class_id,
            display_label=display_label,
            class_display_label=class_label,
            status=status,
            has_subject_summary=has_summary,
            has_daywise_data=has_day,
            existing_courses_count=courses_count,
            existing_observations_count=obs_count,
            attended_sum=attended_sum,
            delivered_sum=delivered_sum,
            percentage=pct,
            discovered_at=utc_now(),
            last_sync_timestamp=last_sync,
            candidate_months=m_nums,
            candidate_month_labels=m_labels,
            estimated_requests=req_count,
            coverage_state=cov_state,
            reconciliation_verdict=rec_verdict,
        )

    def build_preview(
        self,
        inventory: HistoricalDiscoveryInventory,
        selected_term_keys: Optional[list[str]] = None,
    ) -> HistoricalSyncPreview:
        """Generate pre-synchronization preview and estimated work."""
        if selected_term_keys is not None:
            selected = [t for t in inventory.terms if t.term_key in selected_term_keys]
        else:
            selected = []

        if selected_term_keys and set(selected_term_keys) != {t.term_key for t in selected}:
            raise ValueError("Selected term was not discovered.")
        # First pilot has one subject-summary request and no inferred months.
        for item in selected:
            item.estimated_requests = 1
        total_requests = len(selected)
        pacing_sec = total_requests * 2.0  # Conservative 2.0s per request average

        return HistoricalSyncPreview(
            selected_terms=selected,
            total_selected_terms=len(selected),
            total_estimated_requests=total_requests,
            estimated_pacing_seconds=pacing_sec,
            pacing_guidance="Conservative pacing: 1.5s - 2.5s between requests to respect portal load limits.",
            requires_user_approval=True,
        )

    def get_term_coverage(self, term_id: str) -> TermCoverageReport:
        """Construct detailed coverage report for an academic term."""
        term = self.db.get(AcademicTerm, term_id)
        if not term:
            raise ValueError(f"Term with ID '{term_id}' not found.")

        has_summary = len(term.snapshots) > 0
        snap_count = len(term.snapshots)
        courses_count = 0
        if has_summary:
            latest_snap = term.snapshots[-1]
            courses_count = len(latest_snap.rows)

        candidate_months, candidate_month_labels = get_standard_semester_months(term.semester_number, academic_year=term.academic_year)

        # Observations across all batches for this term
        obs = self.db.scalars(
            select(AttendancePeriodObservation).where(
                AttendancePeriodObservation.academic_term_id == term.id
            )
        ).all()

        batches = term.observation_batches
        months_attempted: set[str] = set()
        months_completed: set[str] = set()
        for b in batches:
            if b.coverage_start_date:
                m_str = str(b.coverage_start_date.month)
                months_attempted.add(m_str)
                if b.status != "FAILED":
                    months_completed.add(m_str)

        # Instructional dates where delivered > 0
        inst_dates = {o.attendance_date for o in obs if o.delivered_period_count > 0}
        inst_periods = sum(o.delivered_period_count for o in obs)

        # Mapped vs unmapped
        mapped_count = sum(
            o.delivered_period_count
            for o in obs
            if o.delivered_period_count > 0 and (o.course_id is not None or o.source_course_label is not None)
        )
        unmapped_count = sum(
            o.delivered_period_count
            for o in obs
            if o.delivered_period_count > 0 and o.course_id is None and not o.source_course_label
        )
        unreported_count = sum(
            1 for o in obs if o.delivered_period_count == 0 and o.attended_period_count == 0
        )

        source_errors = sum(1 for b in batches if b.status == "FAILED")

        # Coverage state
        if not has_summary and len(batches) == 0:
            cov_state = CoverageState.NOT_IMPORTED
        elif has_summary or len(batches) > 0:
            cov_state = CoverageState.PARTIAL
        else:
            cov_state = CoverageState.DISCOVERED

        # Reconciliation verdict
        rec_verdict = TermReconciliationVerdict.NOT_AVAILABLE
        if has_summary and len(batches) > 0:
            try:
                rep = self.reconciliation_service.reconcile_term(term.id)
                rec_verdict = TermReconciliationVerdict(rep.reconciliation_status.value)
            except Exception:
                rec_verdict = TermReconciliationVerdict.PARTIAL_COVERAGE


        return TermCoverageReport(
            term_id=term.id,
            academic_year=term.academic_year,
            semester_number=term.semester_number,
            class_identifier=term.class_identifier,
            coverage_state=cov_state,
            has_subject_summary=has_summary,
            subject_snapshot_count=snap_count,
            subject_courses_count=courses_count,
            candidate_months=candidate_months,
            candidate_month_labels=candidate_month_labels,
            months_attempted=sorted(list(months_attempted)),
            months_completed=sorted(list(months_completed)),
            unique_instructional_dates=len(inst_dates),
            unique_instructional_periods=inst_periods,
            mapped_periods=mapped_count,
            unmapped_periods=unmapped_count,
            missing_or_unreported_periods=unreported_count,
            source_errors_count=source_errors,
            reconciliation_verdict=rec_verdict,
            details={
                "batches_count": len(batches),
                "total_observations": len(obs),
            },
        )

    def discover_live(
        self,
        portal_session_manager: Optional[PortalSessionManager] = None,
    ) -> HistoricalDiscoveryInventory:
        """Persist only successfully traversed selector combinations, never portal HTML."""
        extractor = LivePortalExtractor(portal_session_manager)
        from app.services.sync_job_service import _SYNC_LOCK
        if not _SYNC_LOCK.acquire(blocking=False):
            raise PortalSafetyError("ANOTHER_PORTAL_JOB_IS_ACTIVE")
        try:
            rows = extractor.discover_historical_combinations()
            if not rows:
                raise PortalSafetyError("NO_VERIFIED_TERM_COMBINATIONS")
            job = SyncJob(source_scope="HISTORICAL_SELECTOR_DISCOVERY", state=SyncJobState.COMPLETED.value,
                          completion_timestamp=utc_now(), details={"combinations": rows})
            self.db.add(job)
            self.db.commit()
            return self._inventory_from_rows(rows, "VERIFIED_SELECTOR_DISCOVERY", True)
        except Exception:
            self.db.rollback()
            raise PortalSafetyError("HISTORICAL_DISCOVERY_NOT_VERIFIED") from None
        finally:
            _SYNC_LOCK.release()
