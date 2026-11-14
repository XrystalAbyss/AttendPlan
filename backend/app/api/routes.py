"""API routes for AttendPlan F0 + F1.

Preserves all F0 endpoints (/health, /sample, /simulate) and introduces
F1 persistent multi-semester, date-wise analytics, and reconciliation endpoints.
"""

from __future__ import annotations
from app.services.current_observations import latest_observations



import calendar
import logging
import os

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.adapters.fixture_loader import load_sample_snapshot
from app.api.schemas import (
    AcademicHistoryResponse,
    AcademicTermDiscoveryResponse,
    AcademicTermResponse,
    CourseReconciliationItemResponse,
    DailyAnalyticsItem,
    DailyCourseItem,
    DayWiseDiscoveryResponse,
    DiscoverRequest,
    HistoricalPlanResponse,
    IngestionEventResponse,
    IngestionUploadResponse,
    MonthlyAnalyticsItem,
    OverallDiscoveryResponse,
    PilotSyncRequest,
    PortalSessionStatusResponse,
    SemesterHistoricalItem,
    SnapshotListItem,
    SubjectAbsenceRankingsResponse,
    SubjectAnalyticsItem,
    SubjectAnalyticsResponse,
    SubjectWiseDiscoveryResponse,
    SyncDayWiseRequest,
    SyncDayWiseResponse,
    SyncJobResponse,
    SyncSubjectWiseRequest,
    SyncSubjectWiseResponse,
    TermAttendanceResponse,
    TermOptionItem,
    TermReconciliationResponse,
    TermSyncScopeItem,
    WeekdayAnalyticsItem,
    LoginOrchestrateRequest,
    LoginOrchestrationResponse,
    TotpCandidateResponse,
    TotpEnrollRequest,
    TotpInspectResponse,
    TotpMfaAutofillRequest,
    TotpMfaAutofillResponse,
    TotpSettingsUpdateRequest,
    TotpVerifyRequest,
    TotpVerifyResponse,
    HistoricalDiscoverRequest,
    HistoricalDiscoveryResponse,
    HistoricalImportRequest,
    HistoricalPreviewRequest,
    HistoricalPreviewResponse,
    HistoricalTermItemResponse,
    TermCoverageResponse,
)


from app.adapters.live_portal_extractor import (
    BrowserNotConnectedError,
    LivePortalExtractor,
    SessionNotAuthenticatedError,
)
from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    DayWiseAttendanceAdapter,
    OverallAttendanceAdapter,
    PortalSessionManager,
    SubjectWiseAttendanceAdapter,
    TermOption,
)
from app.adapters.qr_parser import QRParserAdapter, clean_base32_secret
from app.domain.totp_models import (
    SecureVaultUnavailableError,
    TotpAccountCandidate,
    TotpEnrollmentError,
    TotpEnrollmentMetadata,
    TotpStatusResponse,
)
from app.services.login_orchestrator import LoginOrchestrator
from app.services.settings_service import (
    SettingsPublicResponse,
    SettingsService,
    SettingsUpdateRequest,
)
from app.services.totp_vault_service import TotpVaultService



from app.services.historical_backfill_service import HistoricalBackfillService
from app.services.historical_discovery_service import HistoricalDiscoveryService
from app.services.historical_planner import HistoricalSyncPlanner
from app.services.sync_job_service import SyncJobService, _SYNC_LOCK


from app.db.enums import IngestionOutcome
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot as DbSnapshot,
    AttendanceSnapshotRow,
    Course,
    IngestionEvent,
)
from app.db.session import get_db
from app.domain.analytics_engine import AttendanceAnalyticsEngine
from app.domain.attendance_engine import (
    calculate_aggregate_metrics,
    calculate_course_metrics,
    simulate_period_change,
)
from app.domain.models import (
    AttendanceSnapshot as DomainSnapshot,
    CourseRecord,
    CourseStatus,
    SimulationRequest,
    SimulationResponse,
    SimulationResultItem,
    SnapshotSummary,
)
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService

router = APIRouter()


# ---------------------------------------------------------
# F0 Preserved Endpoints
# ---------------------------------------------------------

@router.get("/health", tags=["System"])
def get_health() -> dict[str, str]:
    """Health check endpoint confirming backend operational status."""
    return {
        "status": "healthy",
        "app": "AttendPlan",
        "version": "0.2.0-F1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v1/attendance/sample", response_model=DomainSnapshot, tags=["Attendance"])
def get_sample_attendance(
    target: float = Query(default=75.0, gt=0.0, lt=100.0, description="Target percentage threshold"),
) -> DomainSnapshot:
    """Return historical attendance snapshot from sanitized offline fixture (pure in-memory read).

    Invariant: Normal read endpoints NEVER silently insert records into the database.
    """
    try:
        return load_sample_snapshot(target_percentage=target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sample fixture: {str(e)}")


@router.post("/api/v1/demo/seed", response_model=IngestionUploadResponse, tags=["Demo"])
def seed_demo_sample_data(
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> IngestionUploadResponse:
    """Explicitly seed sanitized historical sample data into the database for demonstration or testing.

    This operation is explicit and user-initiated; it is never triggered automatically on reads.
    """
    if os.environ.get("ATTENDPLAN_ALLOW_SYNTHETIC_IMPORT") != "1":
        raise HTTPException(status_code=403, detail="Synthetic imports are disabled in normal runtime.")
    try:
        sample = load_sample_snapshot(target_percentage=target)
        ingestor = IngestionService(db)
        snap, outcome = ingestor.ingest_subject_wise_snapshot(sample, source="DEMO_SEED_MANUAL")
        return IngestionUploadResponse(
            type="SUBJECT_WISE_SNAPSHOT",
            id=snap.id,
            term_id=snap.academic_term_id,
            outcome=outcome.value,
            details={"record_count": snap.record_count, "checksum": snap.content_checksum},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed demo data: {str(e)}")


@router.post("/api/v1/simulation/simulate", response_model=SimulationResponse, tags=["Simulation"])
def simulate_attendance(payload: SimulationRequest) -> SimulationResponse:
    """Simulate the effect of attending or missing future lectures on course status."""
    results: list[SimulationResultItem] = []

    for item in payload.courses:
        orig = calculate_course_metrics(item.attended, item.delivered, target=payload.target_percentage)
        sim = simulate_period_change(
            attended=item.attended,
            delivered=item.delivered,
            delta_attended=item.delta_attended,
            delta_missed=item.delta_missed,
            target=payload.target_percentage,
        )

        status_changed = orig.status != sim.status
        summary_msg = f"Projected {sim.percent}% ({sim.status.value})"

        results.append(
            SimulationResultItem(
                code=item.code,
                original_attended=item.attended,
                original_delivered=item.delivered,
                original_percent=orig.percent,
                original_status=orig.status,
                simulated_attended=sim.attended,
                simulated_delivered=sim.delivered,
                simulated_percent=sim.percent,
                simulated_status=sim.status,
                simulated_can_skip=sim.can_skip,
                simulated_must_attend=sim.must_attend,
                status_changed=status_changed,
                summary=summary_msg,
            )
        )

    return SimulationResponse(
        target_percentage=payload.target_percentage,
        results=results,
    )


# ---------------------------------------------------------
# F1 Academic Terms & Multi-Semester Endpoints
# ---------------------------------------------------------

@router.get("/api/v1/terms", response_model=list[AcademicTermResponse], tags=["Terms"])
def list_academic_terms(
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> list[AcademicTermResponse]:
    """List all registered academic terms with attendance summaries.

    Starts with an empty list for fresh databases; never auto-seeds sample records.
    """
    stmt = select(AcademicTerm).order_by(
        AcademicTerm.academic_year.desc(), AcademicTerm.semester_number.desc()
    )
    terms = db.scalars(stmt).all()

    response: list[AcademicTermResponse] = []
    for t in terms:
        # Check latest snapshot
        snap_stmt = (
            select(DbSnapshot)
            .where(DbSnapshot.academic_term_id == t.id)
            .order_by(DbSnapshot.captured_at.desc())
        )
        snap = db.scalars(snap_stmt).first()

        tot_courses = 0
        tot_att = 0
        tot_del = 0
        pct = None
        status = CourseStatus.UNRECORDED

        if snap:
            rows = db.scalars(
                select(AttendanceSnapshotRow).where(AttendanceSnapshotRow.snapshot_id == snap.id)
            ).all()
            tot_courses = len(rows)
            records = [(r.attended_periods, r.delivered_periods) for r in rows]
            tot_att, tot_del, pct, status = calculate_aggregate_metrics(records, target=target)

        # Check if datewise observations exist
        has_daywise = bool(
            (
                db.scalar(
                    select(func.count(AttendanceObservationBatch.id)).where(
                        AttendanceObservationBatch.academic_term_id == t.id
                    )
                )
                or 0
            )
            > 0
        )

        response.append(
            AcademicTermResponse(
                id=t.id,
                institution_key=t.institution_key,
                academic_year=t.academic_year,
                semester_number=t.semester_number,
                class_identifier=t.class_identifier,
                academic_start_date=t.academic_start_date,
                academic_end_date=t.academic_end_date,
                created_at=t.created_at,
                total_courses=tot_courses,
                total_attended=tot_att,
                total_delivered=tot_del,
                overall_percentage=pct,
                overall_status=status,
                has_datewise_data=has_daywise,
            )
        )

    return response


@router.get("/api/v1/terms/{term_id}/attendance", response_model=TermAttendanceResponse, tags=["Terms"])
def get_term_attendance(
    term_id: str,
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> TermAttendanceResponse:
    """Retrieve subject-wise attendance and course roster for a specific term."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    snap_stmt = (
        select(DbSnapshot)
        .where(DbSnapshot.academic_term_id == term_id)
        .order_by(DbSnapshot.captured_at.desc())
    )
    snap = db.scalars(snap_stmt).first()

    courses_list: list[CourseRecord] = []
    if snap:
        rows_stmt = (
            select(AttendanceSnapshotRow, Course)
            .join(Course, AttendanceSnapshotRow.course_id == Course.id)
            .where(AttendanceSnapshotRow.snapshot_id == snap.id)
            .order_by(Course.course_code)
        )
        for row, c in db.execute(rows_stmt):
            calc = calculate_course_metrics(
                row.attended_periods, row.delivered_periods, target=target
            )
            courses_list.append(
                CourseRecord(
                    code=c.course_code,
                    name=c.course_name,
                    short_name=c.course_short_name or c.course_code,
                    faculty=c.faculty_name,
                    credits=c.credits or 1.0,
                    is_lab=c.course_type == "LAB",
                    attended=row.attended_periods,
                    delivered=row.delivered_periods,
                    percent=calc.percent,
                    status=calc.status,
                    can_skip=calc.can_skip,
                    must_attend=calc.must_attend,
                    margin_summary=calc.margin_summary,
                )
            )

    active = [c for c in courses_list if c.delivered > 0]
    unrec = [c for c in courses_list if c.delivered == 0]
    safe = [c for c in courses_list if c.status == CourseStatus.SAFE]
    risk = [c for c in courses_list if c.status == CourseStatus.AT_RISK]

    tot_att, tot_del, overall_pct, overall_status = calculate_aggregate_metrics(
        [(c.attended, c.delivered) for c in courses_list], target=target
    )

    summary = SnapshotSummary(
        total_courses=len(courses_list),
        active_courses=len(active),
        unrecorded_courses=len(unrec),
        safe_courses=len(safe),
        at_risk_courses=len(risk),
        total_attended=tot_att,
        total_delivered=tot_del,
        overall_percentage=overall_pct,
        overall_status=overall_status,
    )

    return TermAttendanceResponse(
        term_id=term.id,
        academic_year=term.academic_year,
        semester=term.semester_number,
        class_name=term.class_identifier,
        snapshot_id=snap.id if snap else None,
        captured_at=snap.captured_at if snap else None,
        summary=summary,
        courses=courses_list,
    )


@router.get("/api/v1/terms/{term_id}/snapshots", response_model=list[SnapshotListItem], tags=["Terms"])
def list_term_snapshots(
    term_id: str,
    db: Session = Depends(get_db),
) -> list[SnapshotListItem]:
    """List historical snapshots captured for a specific academic term."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    stmt = (
        select(DbSnapshot)
        .where(DbSnapshot.academic_term_id == term_id)
        .order_by(DbSnapshot.captured_at.desc())
    )
    snaps = db.scalars(stmt).all()
    return [
        SnapshotListItem(
            id=s.id,
            academic_term_id=s.academic_term_id,
            source=s.source,
            captured_at=s.captured_at,
            reporting_start_date=s.reporting_start_date,
            reporting_end_date=s.reporting_end_date,
            content_checksum=s.content_checksum,
            record_count=s.record_count,
        )
        for s in snaps
    ]


# ---------------------------------------------------------
# F1 Analytics Endpoints
# ---------------------------------------------------------

@router.get("/api/v1/terms/{term_id}/analytics/summary", response_model=SnapshotSummary, tags=["Analytics"])
def get_term_summary(
    term_id: str,
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> SnapshotSummary:
    """Retrieve aggregate summary analytics for a term."""
    resp = get_term_attendance(term_id=term_id, target=target, db=db)
    return resp.summary


@router.get("/api/v1/terms/{term_id}/analytics/monthly", response_model=list[MonthlyAnalyticsItem], tags=["Analytics"])
def get_monthly_analytics(
    term_id: str,
    db: Session = Depends(get_db),
) -> list[MonthlyAnalyticsItem]:
    """Retrieve monthly attendance and absence breakdown for a term."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    obs_stmt = select(AttendancePeriodObservation).where(
        AttendancePeriodObservation.academic_term_id == term_id
    )
    observations = latest_observations(db.scalars(obs_stmt).all())

    obs_dicts = [
        {
            "attendance_date": o.attendance_date,
            "delivered_period_count": o.delivered_period_count,
            "attended_period_count": o.attended_period_count,
        }
        for o in observations
    ]

    metrics = AttendanceAnalyticsEngine.compute_monthly_analytics(obs_dicts)
    return [
        MonthlyAnalyticsItem(
            year=m.year,
            month=m.month,
            month_label=m.month_label,
            delivered=m.delivered,
            attended=m.attended,
            missed=m.missed,
            attendance_percentage=m.attendance_percentage,
            absence_percentage=m.absence_percentage,
            observed_dates_count=m.observed_dates_count,
            coverage=m.coverage,
        )
        for m in metrics
    ]


@router.get("/api/v1/terms/{term_id}/analytics/weekday", response_model=list[WeekdayAnalyticsItem], tags=["Analytics"])
def get_weekday_analytics(
    term_id: str,
    db: Session = Depends(get_db),
) -> list[WeekdayAnalyticsItem]:
    """Retrieve weekday-wise attendance patterns (Monday - Sunday) in Asia/Kolkata dates."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    obs_stmt = select(AttendancePeriodObservation).where(
        AttendancePeriodObservation.academic_term_id == term_id
    )
    observations = latest_observations(db.scalars(obs_stmt).all())

    obs_dicts = [
        {
            "attendance_date": o.attendance_date,
            "delivered_period_count": o.delivered_period_count,
            "attended_period_count": o.attended_period_count,
        }
        for o in observations
    ]

    metrics = AttendanceAnalyticsEngine.compute_weekday_analytics(obs_dicts)
    return [
        WeekdayAnalyticsItem(
            weekday_index=w.weekday_index,
            weekday_name=w.weekday_name,
            delivered=w.delivered,
            attended=w.attended,
            missed=w.missed,
            absence_rate=w.absence_rate,
            observed_teaching_dates=w.observed_teaching_dates,
            coverage=w.coverage,
        )
        for w in metrics
    ]


@router.get("/api/v1/terms/{term_id}/analytics/daily", response_model=list[DailyAnalyticsItem], tags=["Analytics"])
def get_daily_analytics(
    term_id: str,
    db: Session = Depends(get_db),
) -> list[DailyAnalyticsItem]:
    """Retrieve day-by-day attendance observations."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    obs_stmt = (
        select(AttendancePeriodObservation)
        .where(AttendancePeriodObservation.academic_term_id == term_id)
        .order_by(AttendancePeriodObservation.attendance_date.asc())
    )
    observations = latest_observations(db.scalars(obs_stmt).all())

    obs_dicts = [
        {
            "attendance_date": o.attendance_date,
            "delivered_period_count": o.delivered_period_count,
            "attended_period_count": o.attended_period_count,
            "source_course_label": o.source_course_label,
            "source_period_identifier": o.source_period_identifier,
            "status": o.status,
        }
        for o in observations
    ]

    metrics = AttendanceAnalyticsEngine.compute_daily_analytics(obs_dicts)
    return [
        DailyAnalyticsItem(
            attendance_date=d.attendance_date,
            weekday_name=d.weekday_name,
            delivered=d.delivered,
            attended=d.attended,
            missed=d.missed,
            percentage=d.percentage,
            courses=[
                DailyCourseItem(
                    course_code=c.course_code,
                    slot_label=c.slot_label,
                    status=c.status,
                    attended=c.attended,
                    delivered=c.delivered,
                )
                for c in d.courses
            ],
            coverage=d.coverage,
        )
        for d in metrics
    ]


@router.get("/api/v1/terms/{term_id}/analytics/subjects", response_model=SubjectAnalyticsResponse, tags=["Analytics"])
def get_subject_analytics(
    term_id: str,
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> SubjectAnalyticsResponse:
    """Retrieve detailed subject analytics and multi-dimensional absence rankings."""
    resp = get_term_attendance(term_id=term_id, target=target, db=db)

    raw_records = [
        {
            "code": c.code,
            "name": c.name,
            "course_type": "LAB" if c.is_lab else "THEORY",
            "faculty": c.faculty,
            "credits": c.credits,
            "attended": c.attended,
            "delivered": c.delivered,
        }
        for c in resp.courses
    ]

    subject_metrics = AttendanceAnalyticsEngine.compute_subject_analytics(raw_records, target=target)
    rankings = AttendanceAnalyticsEngine.compute_subject_absence_rankings(subject_metrics)

    subjects_out = [
        SubjectAnalyticsItem(
            course_code=s.course_code,
            course_name=s.course_name,
            course_type=s.course_type,
            faculty_name=s.faculty_name,
            credits=s.credits,
            attended=s.attended,
            delivered=s.delivered,
            missed=s.missed,
            percentage=s.percentage,
            status=s.status,
            can_skip=s.can_skip,
            must_attend=s.must_attend,
            absence_contribution_percentage=s.absence_contribution_percentage,
            margin_summary=s.margin_summary,
        )
        for s in subject_metrics
    ]

    rankings_out = SubjectAbsenceRankingsResponse(
        by_absolute_missed=[
            {"code": r[0], "name": r[1], "missed_periods": r[2]}
            for r in rankings.by_absolute_missed
        ],
        by_missed_rate=[
            {"code": r[0], "name": r[1], "absence_rate": r[2]}
            for r in rankings.by_missed_rate
        ],
        by_total_delivered=[
            {"code": r[0], "name": r[1], "delivered_periods": r[2]}
            for r in rankings.by_total_delivered
        ],
    )

    return SubjectAnalyticsResponse(
        subjects=subjects_out,
        rankings=rankings_out,
    )


@router.get("/api/v1/terms/{term_id}/analytics/calendar", response_model=list[DailyAnalyticsItem], tags=["Analytics"])
def get_calendar_analytics(
    term_id: str,
    db: Session = Depends(get_db),
) -> list[DailyAnalyticsItem]:
    """Retrieve calendar-grid formatted daily attendance records."""
    return get_daily_analytics(term_id=term_id, db=db)


@router.get("/api/v1/analytics/academic-history", response_model=AcademicHistoryResponse, tags=["Analytics"])
def get_academic_history(
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> AcademicHistoryResponse:
    """Retrieve cross-semester attendance comparison and cumulative career statistics."""
    terms_stmt = select(AcademicTerm).order_by(
        AcademicTerm.academic_year.asc(), AcademicTerm.semester_number.asc()
    )
    terms = db.scalars(terms_stmt).all()

    term_data_list: list[dict[str, Any]] = []
    career_att = 0
    career_del = 0

    for t in terms:
        snap_stmt = (
            select(DbSnapshot)
            .where(DbSnapshot.academic_term_id == t.id)
            .order_by(DbSnapshot.captured_at.desc())
        )
        snap = db.scalars(snap_stmt).first()

        tot_att = 0
        tot_del = 0
        below_count = 0
        tot_courses = 0

        if snap:
            rows = db.scalars(
                select(AttendanceSnapshotRow).where(AttendanceSnapshotRow.snapshot_id == snap.id)
            ).all()
            tot_courses = len(rows)
            for r in rows:
                tot_att += r.attended_periods
                tot_del += r.delivered_periods
                if r.delivered_periods > 0:
                    c_calc = calculate_course_metrics(r.attended_periods, r.delivered_periods, target=target)
                    if c_calc.status == CourseStatus.AT_RISK:
                        below_count += 1

        has_day = bool(
            (
                db.scalar(
                    select(func.count(AttendanceObservationBatch.id)).where(
                        AttendanceObservationBatch.academic_term_id == t.id
                    )
                )
                or 0
            )
            > 0
        )

        career_att += tot_att
        career_del += tot_del

        term_data_list.append(
            {
                "term_id": t.id,
                "academic_year": t.academic_year,
                "semester_number": t.semester_number,
                "class_identifier": t.class_identifier,
                "attended": tot_att,
                "delivered": tot_del,
                "courses_below_threshold": below_count,
                "total_courses": tot_courses,
                "has_datewise_history": has_day,
            }
        )

    sem_metrics = AttendanceAnalyticsEngine.compute_cross_semester_comparison(term_data_list, target=target)

    career_pct = (
        round(float(calculate_aggregate_metrics([(career_att, career_del)], target=target)[2] or 0), 2)
        if career_del > 0
        else None
    )
    career_status = (
        CourseStatus.SAFE
        if (career_del > 0 and calculate_aggregate_metrics([(career_att, career_del)], target=target)[3] == CourseStatus.SAFE)
        else CourseStatus.UNRECORDED
    )

    items_out = [
        SemesterHistoricalItem(
            term_id=m.term_id,
            academic_year=m.academic_year,
            semester_number=m.semester_number,
            class_identifier=m.class_identifier,
            attended=m.attended,
            delivered=m.delivered,
            missed=m.missed,
            percentage=m.percentage,
            status=m.status,
            courses_below_threshold=m.courses_below_threshold,
            total_courses=m.total_courses,
            has_datewise_history=m.has_datewise_history,
        )
        for m in sem_metrics
    ]

    return AcademicHistoryResponse(
        semesters=items_out,
        career_attended=career_att,
        career_delivered=career_del,
        career_percentage=career_pct,
        career_status=career_status,
    )


# ---------------------------------------------------------
# F1 Reconciliation Endpoints
# ---------------------------------------------------------

@router.get("/api/v1/terms/{term_id}/reconciliation", response_model=TermReconciliationResponse, tags=["Reconciliation"])
def get_term_reconciliation(
    term_id: str,
    db: Session = Depends(get_db),
) -> TermReconciliationResponse:
    """Compare Subject-Wise snapshot totals against Day-Wise observation totals."""
    try:
        report = ReconciliationService(db).generate_reconciliation_report(term_id)
        return TermReconciliationResponse(
            term_id=report.term_id,
            academic_year=report.academic_year,
            semester_number=report.semester_number,
            subject_wise_available=report.subject_wise_available,
            day_wise_available=report.day_wise_available,
            latest_snapshot_id=report.latest_snapshot_id,
            latest_batch_id=report.latest_batch_id,
            subject_wise_total_attended=report.subject_wise_total_attended,
            subject_wise_total_delivered=report.subject_wise_total_delivered,
            day_wise_total_attended=report.day_wise_total_attended,
            day_wise_total_delivered=report.day_wise_total_delivered,
            total_unmapped_observations=report.total_unmapped_observations,
            coverage_start_date=report.coverage_start_date,
            coverage_end_date=report.coverage_end_date,
            reconciliation_status=report.reconciliation_status,
            status_explanation=report.status_explanation,
            course_breakdown=[
                CourseReconciliationItemResponse(
                    course_code=c.course_code,
                    course_name=c.course_name,
                    subject_wise_attended=c.subject_wise_attended,
                    subject_wise_delivered=c.subject_wise_delivered,
                    day_wise_attended=c.day_wise_attended,
                    day_wise_delivered=c.day_wise_delivered,
                    attended_diff=c.attended_diff,
                    delivered_diff=c.delivered_diff,
                    status=c.status,
                )
                for c in report.course_breakdown
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------
# F1 Ingestion & Upload Endpoints
# ---------------------------------------------------------

@router.post("/api/v1/attendance/imports/html", response_model=IngestionUploadResponse, tags=["Ingestion"])
async def import_attendance_html(
    file: Optional[UploadFile] = File(default=None),
    html_text: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
) -> IngestionUploadResponse:
    """Upload university portal HTML (auto-routes to Subject-Wise or Day-Wise parser)."""
    content = ""
    if file:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="replace")
    elif html_text:
        content = html_text
    else:
        raise HTTPException(status_code=400, detail="Must provide either file or html_text")

    if not content.strip():
        raise HTTPException(status_code=400, detail="HTML content cannot be empty")

    try:
        service = IngestionService(db)
        res = service.ingest_html_auto(content, source="USER_HTML_IMPORT")
        return IngestionUploadResponse(
            type=res["type"],
            id=res["id"],
            term_id=res["term_id"],
            outcome=res["outcome"],
            details=res,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ingestion failed: {str(e)}")


@router.get("/api/v1/attendance/ingestions", response_model=list[IngestionEventResponse], tags=["Ingestion"])
def list_ingestion_events(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[IngestionEventResponse]:
    """Retrieve audit history of recent ingestion events."""
    stmt = select(IngestionEvent).order_by(IngestionEvent.attempt_at.desc()).limit(limit)
    events = db.scalars(stmt).all()
    return [
        IngestionEventResponse(
            id=e.id,
            source=e.source,
            academic_term_id=e.academic_term_id,
            attempt_at=e.attempt_at,
            outcome=IngestionOutcome(e.outcome),
            safe_error_code=e.safe_error_code,
            associated_snapshot_or_batch=e.associated_snapshot_or_batch,
        )
        for e in events
    ]


# -------------------------------------------------------------
# F2-A Portal Session & Discovery Endpoints
# -------------------------------------------------------------

_portal_session_manager = PortalSessionManager()


@router.get("/api/v1/portal/session/status", response_model=PortalSessionStatusResponse, tags=["Portal Discovery"])
def get_portal_session_status() -> PortalSessionStatusResponse:
    """Check dedicated browser state, CDP loopback connectivity, and portal authentication."""
    info = _portal_session_manager.check_session_status()
    return PortalSessionStatusResponse(
        state=info.state.value,
        browser_launched=info.browser_launched,
        cdp_port=info.cdp_port,
        cdp_url=info.cdp_url,
        current_url=info.current_url,
        page_title=info.page_title,
        profile_dir=info.profile_dir,
        details=info.details,
        manual_fallback_available=info.manual_fallback_available,
    )


@router.post("/api/v1/portal/session/launch", response_model=PortalSessionStatusResponse, tags=["Portal Discovery"])
def launch_portal_browser() -> PortalSessionStatusResponse:
    """Launch dedicated Chrome process bound to loopback CDP and open the university portal."""
    info = _portal_session_manager.launch_dedicated_browser()
    return PortalSessionStatusResponse(
        state=info.state.value,
        browser_launched=info.browser_launched,
        cdp_port=info.cdp_port,
        cdp_url=info.cdp_url,
        current_url=info.current_url,
        page_title=info.page_title,
        profile_dir=info.profile_dir,
        details=info.details,
        manual_fallback_available=info.manual_fallback_available,
    )


@router.post("/api/v1/portal/session/close", response_model=PortalSessionStatusResponse, tags=["Portal Discovery"])
def close_portal_browser() -> PortalSessionStatusResponse:
    """Close dedicated browser process started by AttendPlan."""
    _portal_session_manager.close_session()
    info = _portal_session_manager.check_session_status()
    return PortalSessionStatusResponse(
        state=info.state.value,
        browser_launched=info.browser_launched,
        cdp_port=info.cdp_port,
        cdp_url=info.cdp_url,
        current_url=info.current_url,
        page_title=info.page_title,
        profile_dir=info.profile_dir,
        details="Browser closed successfully.",
        manual_fallback_available=True,
    )


@router.post("/api/v1/portal/session/disconnect", tags=["Portal Discovery"])
def disconnect_portal_session(request: Request) -> dict[str, Any]:
    """Disconnect and close dedicated browser process, freeing CDP resources."""
    from app.api.startup_routes import verify_same_instance_authorization
    verify_same_instance_authorization(request)
    _portal_session_manager.close_session()
    return {
        "status": "disconnected",
        "message": "Browser session closed and loopback CDP released successfully.",
    }


@router.post("/api/v1/portal/discover/terms", response_model=AcademicTermDiscoveryResponse, tags=["Portal Discovery"])
def discover_academic_terms(payload: Optional[DiscoverRequest] = None) -> AcademicTermDiscoveryResponse:
    """Discover available academic years, semesters, and class mappings."""
    html_content = payload.html_content if payload else None
    if not html_content:
        _url, html_content = _portal_session_manager.fetch_portal_page_content()
    if not html_content:
        raise HTTPException(
            status_code=400,
            detail="No portal tab available via CDP and no html_content provided. Please launch the browser and log in or supply HTML directly.",
        )

    res = AcademicTermDiscoveryAdapter.parse_from_html(html_content)
    return AcademicTermDiscoveryResponse(
        academic_years=[TermOptionItem(value=o.value, label=o.label, selected=o.selected) for o in res.academic_years],
        semesters=[TermOptionItem(value=o.value, label=o.label, selected=o.selected) for o in res.semesters],
        classes=[TermOptionItem(value=o.value, label=o.label, selected=o.selected) for o in res.classes],
        evidence=res.evidence,
    )


@router.post("/api/v1/portal/discover/subject-wise", response_model=SubjectWiseDiscoveryResponse, tags=["Portal Discovery"])
def discover_subject_wise_attendance(payload: Optional[DiscoverRequest] = None) -> SubjectWiseDiscoveryResponse:
    """Discover Subject-Wise table headers, columns, and records."""
    html_content = payload.html_content if payload else None
    if not html_content:
        _url, html_content = _portal_session_manager.fetch_portal_page_content("subwise")
    if not html_content:
        raise HTTPException(
            status_code=400,
            detail="No Subject-Wise portal tab available via CDP and no html_content provided.",
        )

    res = SubjectWiseAttendanceAdapter.parse_from_html(html_content)
    return SubjectWiseDiscoveryResponse(
        table_found=res.table_found,
        header_columns=res.header_columns,
        record_count=res.record_count,
        date_range_detected=res.date_range_detected,
        courses_found=res.courses_found,
        evidence=res.evidence,
    )


@router.post("/api/v1/portal/discover/day-wise", response_model=DayWiseDiscoveryResponse, tags=["Portal Discovery"])
def discover_day_wise_attendance(payload: Optional[DiscoverRequest] = None) -> DayWiseDiscoveryResponse:
    """Discover Day-Wise timetable schema, time slot rows, Show Course Name toggle, and date columns."""
    html_content = payload.html_content if payload else None
    if not html_content:
        _url, html_content = _portal_session_manager.fetch_portal_page_content("attendance")
    if not html_content:
        raise HTTPException(
            status_code=400,
            detail="No Day-Wise portal tab available via CDP and no html_content provided.",
        )

    res = DayWiseAttendanceAdapter.parse_from_html(html_content)
    return DayWiseDiscoveryResponse(
        table_found=res.table_found,
        date_columns=res.date_columns,
        time_slots=res.time_slots,
        has_course_name_toggle=res.has_course_name_toggle,
        course_name_mapping_mechanism=res.course_name_mapping_mechanism,
        sample_statuses_observed=res.sample_statuses_observed,
        evidence=res.evidence,
    )


@router.post("/api/v1/portal/discover/overall", response_model=OverallDiscoveryResponse, tags=["Portal Discovery"])
def discover_overall_attendance(payload: Optional[DiscoverRequest] = None) -> OverallDiscoveryResponse:
    """Discover Overall Attendance (allSubject.php) view schema and controls."""
    html_content = payload.html_content if payload else None
    if not html_content:
        _url, html_content = _portal_session_manager.fetch_portal_page_content("allsubject")
    if not html_content:
        raise HTTPException(
            status_code=400,
            detail="No Overall Attendance portal tab available via CDP and no html_content provided.",
        )

    res = OverallAttendanceAdapter.parse_from_html(html_content)
    return OverallDiscoveryResponse(
        view_found=res.view_found,
        filter_controls=res.filter_controls,
        displayed_columns=res.displayed_columns,
        macro_attendance_percentage=res.macro_attendance_percentage,
        evidence=res.evidence,
    )


# -------------------------------------------------------------
# F2-B Live Synchronization & Sync Job State Machine Endpoints
# -------------------------------------------------------------

_live_portal_extractor = LivePortalExtractor(_portal_session_manager)


@router.post("/api/v1/portal/sync/subject-wise", response_model=SyncSubjectWiseResponse, tags=["Portal Sync"])
def sync_subject_wise_live(
    payload: SyncSubjectWiseRequest,
    db: Session = Depends(get_db),
) -> SyncSubjectWiseResponse:
    """Live extract and optionally persist Subject-Wise Attendance from portal."""
    try:
        res = _live_portal_extractor.extract_live_subject_wise(
            academic_year=payload.academic_year,
            semester=payload.semester,
            class_id=payload.class_id,
        )

        snapshot_id = None
        term_id = None
        outcome_str = "PREVIEW_ONLY"

        if payload.persist:
            service = IngestionService(db)
            db_snap, outcome = service.ingest_subject_wise_snapshot(
                res.snapshot,
                source="LIVE_PORTAL_AUTOMATED_SUBWISE",
            )
            snapshot_id = db_snap.id
            term_id = db_snap.academic_term_id
            outcome_str = outcome.value

        return SyncSubjectWiseResponse(
            status="SUCCESS" if res.validation.is_valid else "QUARANTINED",
            snapshot_id=snapshot_id,
            term_id=term_id,
            outcome=outcome_str,
            record_count=len(res.snapshot.courses),
            academic_year=res.academic_year,
            semester=res.semester,
            class_name=res.class_identifier,
            aggregate_percentage=res.snapshot.summary.overall_percentage,
            validation={
                "is_valid": res.validation.is_valid,
                "percentage_deviations": res.validation.percentage_deviations,
                "warnings": res.validation.warnings,
                "quarantined": res.validation.quarantined,
                "quarantine_reason": res.validation.quarantine_reason,
            },
        )
    except SessionNotAuthenticatedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subject-wise extraction failed: {str(e)}")


@router.post("/api/v1/portal/sync/day-wise", response_model=SyncDayWiseResponse, tags=["Portal Sync"])
def sync_day_wise_live(
    payload: SyncDayWiseRequest,
    db: Session = Depends(get_db),
) -> SyncDayWiseResponse:
    """Live extract and optionally persist Day-Wise Attendance timetable matrix from portal."""
    try:
        res = _live_portal_extractor.extract_live_day_wise(
            academic_year=payload.academic_year,
            semester=payload.semester,
            class_id=payload.class_id,
            month=payload.month,
            from_date=payload.from_date,
            to_date=payload.to_date,
            show_course_name=payload.show_course_name,
        )

        batch_id = None
        term_id = None
        outcome_str = "PREVIEW_ONLY"

        if payload.persist:
            service = IngestionService(db)
            db_batch, outcome = service.ingest_daywise_batch(
                res.batch,
                source="LIVE_PORTAL_AUTOMATED_DAYWISE",
            )
            batch_id = db_batch.id
            term_id = db_batch.academic_term_id
            outcome_str = outcome.value

        present_periods = sum(o.attended_period_count for o in res.batch.observations)
        delivered_periods = sum(o.delivered_period_count for o in res.batch.observations)
        unmapped_count = sum(1 for o in res.batch.observations if o.delivered_period_count > 0 and not o.source_course_label)

        return SyncDayWiseResponse(
            status="SUCCESS" if res.validation.is_valid else "WARNING",
            batch_id=batch_id,
            term_id=term_id,
            outcome=outcome_str,
            coverage_start=res.coverage_start,
            coverage_end=res.coverage_end,
            total_observations=len(res.batch.observations),
            total_present=present_periods,
            total_delivered=delivered_periods,
            unmapped_count=unmapped_count,
            validation={
                "is_valid": res.validation.is_valid,
                "course_attribution_active": res.course_attribution_active,
                "warnings": res.validation.warnings,
                "locally_computed": res.validation.locally_computed_totals,
            },
        )
    except SessionNotAuthenticatedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except BrowserNotConnectedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Day-wise extraction failed: {str(e)}")


@router.post("/api/v1/portal/sync/pilot", response_model=SyncJobResponse, tags=["Portal Sync"])
def run_pilot_sync_endpoint(
    payload: PilotSyncRequest,
    db: Session = Depends(get_db),
) -> SyncJobResponse:
    """Execute Gate 4 Pilot Synchronization (Subject-Wise + Selected Month Day-Wise + Persistence + Reconciliation)."""
    service = SyncJobService(db, extractor=_live_portal_extractor)
    job = service.create_job(
        source_scope="CURRENT_SEMESTER_PILOT",
        progress_total=4,
        details={
            "month": payload.month,
            "academic_year": payload.academic_year,
            "semester": payload.semester,
        },
    )

    # Run pilot synchronously or state-machine tracked
    job = service.run_pilot_sync(
        job_id=job.id,
        month=payload.month,
        academic_year=payload.academic_year,
        semester=payload.semester,
        class_id=payload.class_id,
    )

    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=job.details,
    )


@router.get("/api/v1/portal/sync/historical-plan", response_model=HistoricalPlanResponse, tags=["Portal Sync"])
def get_historical_sync_plan(
    db: Session = Depends(get_db),
) -> HistoricalPlanResponse:
    """Discover accessible terms and construct a bounded multi-semester backfill plan."""
    html_content = None
    if _portal_session_manager.is_cdp_reachable():
        _url, html_content = _portal_session_manager.fetch_portal_page_content()

    if html_content:
        discovery = AcademicTermDiscoveryAdapter.parse_from_html(html_content)
        years = discovery.academic_years
        semesters = discovery.semesters
        classes = discovery.classes
    else:
        # Fallback to standard catalog terms for offline preview
        years = [TermOption(value="2026-2027", label="2026-2027"), TermOption(value="2025-2026", label="2025-2026")]
        semesters = [TermOption(value="5", label="Semester 5"), TermOption(value="4", label="Semester 4")]
        classes = [TermOption(value="2582", label="B.Tech CSE AIML-Sem 5")]

    planner = HistoricalSyncPlanner(db)
    summary = planner.build_plan(years, semesters, classes)

    return HistoricalPlanResponse(
        discovered_academic_years=summary.discovered_academic_years,
        terms=[
            TermSyncScopeItem(
                academic_year=t.academic_year,
                semester=t.semester,
                class_identifier=t.class_identifier,
                candidate_months=t.candidate_months,
                candidate_month_labels=t.candidate_month_labels,
                estimated_requests=t.estimated_requests,
                has_subject_snapshot=t.has_subject_snapshot,
                has_daywise_batches=t.has_daywise_batches,
                existing_batches_count=t.existing_batches_count,
                selected=t.selected,
            )
            for t in summary.terms
        ],
        total_terms_count=summary.total_terms_count,
        total_estimated_requests=summary.total_estimated_requests,
        pacing_guidance=summary.pacing_guidance,
    )


def sanitize_sync_job_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Ensure generic sync job responses never expose unscrubbed raw payloads."""
    if not details or "captured_payload" not in details:
        return details
    payload = details.get("captured_payload")
    if isinstance(payload, dict) and payload.get("redacted"):
        return details
    sanitized = dict(details)
    course_count = len(payload.get("courses", [])) if isinstance(payload, dict) and "courses" in payload else None
    sanitized["captured_payload"] = {
        "redacted": True,
        "course_count": course_count,
        "summary": "Source payload redacted from public sync job endpoint."
    }
    return sanitized


@router.get("/api/v1/portal/sync/jobs/latest", response_model=SyncJobResponse, tags=["Portal Sync"])
def get_latest_sync_job(db: Session = Depends(get_db)) -> SyncJobResponse:
    """Get the most recent synchronization job."""
    service = SyncJobService(db)
    job = service.get_latest_job()
    if not job:
        raise HTTPException(status_code=404, detail="No sync jobs have been created yet.")
    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=sanitize_sync_job_details(job.details),
    )


@router.get("/api/v1/portal/sync/jobs/{job_id}", response_model=SyncJobResponse, tags=["Portal Sync"])
def get_sync_job_by_id(job_id: str, db: Session = Depends(get_db)) -> SyncJobResponse:
    """Fetch sync job status by unique job identifier."""
    service = SyncJobService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Sync job {job_id} not found.")
    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=sanitize_sync_job_details(job.details),
    )


@router.post("/api/v1/portal/sync/jobs/{job_id}/cancel", response_model=SyncJobResponse, tags=["Portal Sync"])
def cancel_sync_job(job_id: str, db: Session = Depends(get_db)) -> SyncJobResponse:
    """Request safe cancellation of an active sync job."""
    service = SyncJobService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Sync job {job_id} not found.")
    updated = service.cancel_job(job_id)
    return SyncJobResponse(
        id=updated.id,
        academic_term_id=updated.academic_term_id,
        source_scope=updated.source_scope,
        state=updated.state,
        current_step=updated.current_step,
        start_timestamp=updated.start_timestamp,
        completion_timestamp=updated.completion_timestamp,
        completed_batches=updated.completed_batches,
        failed_batches=updated.failed_batches,
        progress_total=updated.progress_total,
        progress_current=updated.progress_current,
        safe_diagnostic_message=updated.safe_diagnostic_message,
        details=sanitize_sync_job_details(updated.details),
    )


# -------------------------------------------------------------
# F2-C & Addendum: Authentication, Vault & Login Orchestrator
# -------------------------------------------------------------

_settings_service = SettingsService()
_vault_service = TotpVaultService()
_login_orchestrator = LoginOrchestrator(
    session_manager=_portal_session_manager,
    settings_service=_settings_service,
    vault_service=_vault_service,
)


@router.get("/api/v1/auth/settings", response_model=SettingsPublicResponse, tags=["Authentication"])
def get_auth_settings() -> SettingsPublicResponse:
    """Retrieve non-sensitive authentication and automation settings with masked mobile."""
    public = _settings_service.get_public_settings()
    metadata = _vault_service.get_masked_account_metadata()
    if metadata:
        public.auto_totp_autofill = metadata.auto_autofill_enabled
        public.auto_totp_submit = metadata.auto_submit_enabled
    return public


@router.post("/api/v1/auth/settings", response_model=SettingsPublicResponse, tags=["Authentication"])
def update_auth_settings(req: SettingsUpdateRequest) -> SettingsPublicResponse:
    """Update student mobile number and login automation toggles."""
    try:
        _settings_service.update_settings(req)
        if req.auto_totp_autofill is not None or req.auto_totp_submit is not None:
            _vault_service.update_automation_settings(auto_autofill=req.auto_totp_autofill, auto_submit=req.auto_totp_submit)
        return get_auth_settings()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.get("/api/v1/auth/totp/status", response_model=TotpStatusResponse, tags=["Authentication"])
def get_totp_status() -> TotpStatusResponse:
    """Retrieve non-sensitive status of Windows Credential Manager TOTP vault."""
    return _vault_service.get_enrollment_status()


@router.post("/api/v1/auth/totp/inspect", response_model=TotpInspectResponse, tags=["Authentication"])
async def inspect_totp_input(
    file: Optional[UploadFile] = File(default=None),
    provisioning_input: Optional[str] = Form(default=None),
) -> TotpInspectResponse:
    """Inspect and decode offline QR image or provisioning URI without saving to vault."""
    raw_text = ""
    source_fmt = "UNKNOWN"
    if file:
        img_bytes = await file.read()
        raw_text = QRParserAdapter.decode_qr_image(img_bytes)
        source_fmt = "QR_IMAGE"
    elif provisioning_input:
        raw_text = provisioning_input.strip()
        if raw_text.startswith("otpauth-migration://"):
            source_fmt = "GOOGLE_MIGRATION"
        elif raw_text.startswith("otpauth://"):
            source_fmt = "STANDARD_TOTP"
        else:
            source_fmt = "MANUAL_BASE32"
    else:
        raise HTTPException(status_code=400, detail="Must provide either a QR image file or provisioning input text.")

    try:
        candidates = QRParserAdapter.parse_provisioning_input(raw_text)
        return TotpInspectResponse(
            candidates=[
                TotpCandidateResponse(
                    candidate_id=f"cand_{i}",
                    issuer=c.issuer,
                    masked_account=c.masked_account,
                    digits=c.digits,
                    period=c.period,
                    algorithm=c.algorithm,
                    source_type=c.source_type,
                )
                for i, c in enumerate(candidates)
            ],
            total_found=len(candidates),
            source_format=source_fmt,
        )
    except TotpEnrollmentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Inspection failed: {str(e)}")


@router.post("/api/v1/auth/totp/enroll", response_model=TotpEnrollmentMetadata, tags=["Authentication"])
def enroll_totp_secret(payload: TotpEnrollRequest) -> TotpEnrollmentMetadata:
    """Enroll candidate authenticator secret into Windows Credential Manager."""
    try:
        candidate: Optional[TotpAccountCandidate] = None

        if payload.provisioning_input and payload.provisioning_input.strip():
            candidates = QRParserAdapter.parse_provisioning_input(payload.provisioning_input.strip())
            if len(candidates) > 1:
                if not payload.candidate_id:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Migration export contains multiple accounts ({len(candidates)} found). "
                            "Explicit selection required via candidate_id."
                        ),
                    )
                target_idx: Optional[int] = None
                if payload.candidate_id.startswith("cand_"):
                    try:
                        target_idx = int(payload.candidate_id.replace("cand_", ""))
                    except ValueError:
                        pass
                else:
                    try:
                        target_idx = int(payload.candidate_id)
                    except ValueError:
                        pass

                if target_idx is not None and 0 <= target_idx < len(candidates):
                    candidate = candidates[target_idx]
                else:
                    matched = [c for c in candidates if c.account_name == payload.candidate_id]
                    if len(matched) == 1:
                        candidate = matched[0]
                    else:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Candidate ID '{payload.candidate_id}' not found among {len(candidates)} accounts.",
                        )
                # Discard bulk export from memory immediately
                candidates.clear()
            elif len(candidates) == 1:
                candidate = candidates[0]
                candidates.clear()
        elif payload.secret_base32 and payload.secret_base32.strip():
            cleaned = clean_base32_secret(payload.secret_base32)
            candidate = TotpAccountCandidate(
                issuer=payload.issuer or "iCloudEMS",
                account_name=payload.account_label or "student",
                secret_base32=cleaned,
            )

        if not candidate:
            raise HTTPException(
                status_code=400,
                detail="Must provide either provisioning_input (URI/export) or secret_base32 to enroll.",
            )

        meta = _vault_service.enroll(
            candidate=candidate,
            auto_autofill=payload.auto_autofill_enabled,
            auto_submit=payload.auto_submit_enabled,
        )
        return meta
    except HTTPException:
        raise
    except SecureVaultUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except TotpEnrollmentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")


@router.post("/api/v1/auth/totp/enroll-image", response_model=TotpEnrollmentMetadata, tags=["Authentication"])
async def enroll_totp_image(
    file: UploadFile = File(...),
    candidate_id: Optional[str] = Form(default=None),
    auto_autofill_enabled: bool = Form(default=False),
    auto_submit_enabled: bool = Form(default=False),
) -> TotpEnrollmentMetadata:
    """Decode offline QR image, select chosen candidate, and commit to Windows vault.

    The decoded image and any unselected account candidates are discarded immediately.
    """
    try:
        img_bytes = await file.read()
        raw_text = QRParserAdapter.decode_qr_image(img_bytes)
        del img_bytes

        candidates = QRParserAdapter.parse_provisioning_input(raw_text)
        del raw_text

        candidate: Optional[TotpAccountCandidate] = None
        if len(candidates) > 1:
            if not candidate_id:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Migration QR contains multiple accounts ({len(candidates)} found). "
                        "Explicit selection required via candidate_id."
                    ),
                )
            target_idx: Optional[int] = None
            if candidate_id.startswith("cand_"):
                try:
                    target_idx = int(candidate_id.replace("cand_", ""))
                except ValueError:
                    pass
            else:
                try:
                    target_idx = int(candidate_id)
                except ValueError:
                    pass

            if target_idx is not None and 0 <= target_idx < len(candidates):
                candidate = candidates[target_idx]
            else:
                matched = [c for c in candidates if c.account_name == candidate_id]
                if len(matched) == 1:
                    candidate = matched[0]
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Candidate ID '{candidate_id}' not found among {len(candidates)} accounts.",
                    )
            candidates.clear()
        elif len(candidates) == 1:
            candidate = candidates[0]
            candidates.clear()

        if not candidate:
            raise HTTPException(status_code=400, detail="No valid TOTP account found in uploaded QR image.")

        meta = _vault_service.enroll(
            candidate=candidate,
            auto_autofill=auto_autofill_enabled,
            auto_submit=auto_submit_enabled,
        )
        return meta
    except HTTPException:
        raise
    except SecureVaultUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except TotpEnrollmentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR image enrollment failed: {str(e)}")


@router.post("/api/v1/auth/totp/verify", response_model=TotpVerifyResponse, tags=["Authentication"])
def verify_totp_code(payload: TotpVerifyRequest) -> TotpVerifyResponse:
    """Verify test code against currently enrolled secret without exposing secret."""
    try:
        valid = _vault_service.verify_enrollment(payload.code)
        msg = "Verification successful. TOTP engine is synchronized." if valid else "Verification failed. Code did not match active window."
        return TotpVerifyResponse(valid=valid, message=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification error: {str(e)}")


@router.delete("/api/v1/auth/totp/enrollment", tags=["Authentication"])
def delete_totp_enrollment() -> dict[str, Any]:
    """Wipe authenticator secret from Windows Credential Manager and delete local metadata."""
    success = _vault_service.remove_enrollment()
    return {"success": success, "message": "Enrolled authenticator secret removed from local vault."}


@router.patch("/api/v1/auth/totp/settings", response_model=TotpEnrollmentMetadata, tags=["Authentication"])
def update_totp_settings(payload: TotpSettingsUpdateRequest) -> TotpEnrollmentMetadata:
    """Update TOTP automation flags (auto-autofill and auto-submit)."""
    meta = _vault_service.update_automation_settings(
        auto_autofill=payload.auto_autofill_enabled,
        auto_submit=payload.auto_submit_enabled,
    )
    if not meta:
        raise HTTPException(status_code=404, detail="No active enrollment found in vault.")
    _settings_service.update_settings(SettingsUpdateRequest(
        auto_totp_autofill=meta.auto_autofill_enabled, auto_totp_submit=meta.auto_submit_enabled,
    ))
    return meta


@router.post("/api/v1/auth/totp/autofill", response_model=TotpMfaAutofillResponse, tags=["Authentication"])
def autofill_totp_mfa(payload: TotpMfaAutofillRequest) -> TotpMfaAutofillResponse:
    """Autofill active Keycloak TOTP challenge from Windows Credential Manager."""
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(409, "The portal is busy connecting or discovering. Wait for it to finish before autofilling.")
    try:
        res = _portal_session_manager.autofill_keycloak_mfa(
            vault_service=_vault_service, force_submit=payload.force_submit,
        )
    finally:
        _SYNC_LOCK.release()
    return TotpMfaAutofillResponse(
        success=res.get("success", False),
        submitted=res.get("submitted", False),
        redirected=res.get("redirected", False),
        message=res.get("message", ""),
        error=res.get("error"),
    )


@router.post("/api/v1/auth/login/orchestrate", response_model=LoginOrchestrationResponse, tags=["Authentication"])
def orchestrate_login(payload: Optional[LoginOrchestrateRequest] = None) -> LoginOrchestrationResponse:
    """Execute complete end-to-end automated mobile + TOTP login orchestrator."""
    force_submit = payload.force_submit if payload else None
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(409, "The portal is busy connecting or discovering. Wait for it to finish before starting another login.")
    try:
        res = _login_orchestrator.orchestrate_login(force_submit=force_submit)
    finally:
        _SYNC_LOCK.release()
    return LoginOrchestrationResponse(
        state=res.state.value,
        step=res.step,
        success=res.success,
        redirected=res.redirected,
        message=res.message,
        current_url=res.current_url,
        has_saved_mobile=res.has_saved_mobile,
        is_totp_enrolled=res.is_totp_enrolled,
        details=res.details,
    )


@router.get("/api/v1/auth/login/status", response_model=LoginOrchestrationResponse, tags=["Authentication"])
def get_login_status() -> LoginOrchestrationResponse:
    """Get current status of the Keycloak login state machine."""
    res = _login_orchestrator.get_status()
    return LoginOrchestrationResponse(
        state=res.state.value,
        step=res.step,
        success=res.success,
        redirected=res.redirected,
        message=res.message,
        current_url=res.current_url,
        has_saved_mobile=res.has_saved_mobile,
        is_totp_enrolled=res.is_totp_enrolled,
        details=res.details,
    )


@router.post("/api/v1/auth/backup/export", tags=["Authentication"])
def export_database_backup(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Create a verified, timestamped backup of the user's SQLite database."""
    import datetime
    import sqlite3
    from app.api.startup_routes import verify_same_instance_authorization
    from app.db.session import get_default_db_path

    verify_same_instance_authorization(request)
    db_path = get_default_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file does not exist.")

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"attendplan_backup_{timestamp}.sqlite3"

    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(backup_file))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    backup_size = backup_file.stat().st_size
    return {
        "status": "success",
        "backup_path": str(backup_file),
        "backup_filename": backup_file.name,
        "backup_bytes": backup_size,
        "created_at": datetime.datetime.now().isoformat(),
    }


# -------------------------------------------------------------
# F2-E: Multi-Semester Historical Discovery, Backfill & Coverage
# -------------------------------------------------------------


def _map_inventory_item(item: Any) -> HistoricalTermItemResponse:
    return HistoricalTermItemResponse(
        term_key=item.term_key,
        academic_year=item.academic_year,
        semester_number=item.semester_number,
        class_identifier=item.class_identifier,
        display_label=item.display_label,
        class_display_label=item.class_display_label,
        status=item.status.value if hasattr(item.status, "value") else str(item.status),
        has_subject_summary=item.has_subject_summary,
        has_daywise_data=item.has_daywise_data,
        existing_courses_count=item.existing_courses_count,
        existing_observations_count=item.existing_observations_count,
        attended_sum=item.attended_sum,
        delivered_sum=item.delivered_sum,
        percentage=item.percentage,
        discovered_at=item.discovered_at,
        last_sync_timestamp=item.last_sync_timestamp,
        candidate_months=item.candidate_months,
        candidate_month_labels=item.candidate_month_labels,
        estimated_requests=item.estimated_requests,
        coverage_state=item.coverage_state.value if hasattr(item.coverage_state, "value") else str(item.coverage_state),
        reconciliation_verdict=item.reconciliation_verdict.value if hasattr(item.reconciliation_verdict, "value") else str(item.reconciliation_verdict),
        error_message=item.error_message,
    )


@router.get("/api/v1/historical/terms", response_model=HistoricalDiscoveryResponse, tags=["Historical Attendance"])
def get_historical_terms(db: Session = Depends(get_db)) -> HistoricalDiscoveryResponse:
    """Retrieve personal attendance history term inventory discovered or persisted locally."""
    service = HistoricalDiscoveryService(db)
    inv = service.get_persisted_inventory()
    return HistoricalDiscoveryResponse(
        terms=[_map_inventory_item(t) for t in inv.terms],
        discovered_years=inv.discovered_years,
        total_terms_count=inv.total_terms_count,
        available_terms_count=inv.available_terms_count,
        imported_terms_count=inv.imported_terms_count,
        discovery_timestamp=inv.discovery_timestamp,
        provenance=inv.provenance,
    )


@router.post("/api/v1/historical/discover", response_model=HistoricalDiscoveryResponse, tags=["Historical Attendance"])
def discover_historical_terms(
    payload: Optional[HistoricalDiscoverRequest] = None,
    db: Session = Depends(get_db),
) -> HistoricalDiscoveryResponse:
    """Discover available academic terms from live portal DOM or provided HTML."""
    service = HistoricalDiscoveryService(db)
    if payload and payload.html_content:
        inv = service.discover_inventory_from_html(payload.html_content, provenance="USER_SUPPLIED_HTML")
    else:
        try:
            inv = service.discover_live(_portal_session_manager)
        except Exception:
            raise HTTPException(status_code=409, detail="Discovery could not verify dependent filters. Open the authenticated attendance page and retry.") from None

    return HistoricalDiscoveryResponse(
        terms=[_map_inventory_item(t) for t in inv.terms],
        discovered_years=inv.discovered_years,
        total_terms_count=inv.total_terms_count,
        available_terms_count=inv.available_terms_count,
        imported_terms_count=inv.imported_terms_count,
        discovery_timestamp=inv.discovery_timestamp,
        provenance=inv.provenance,
    )


@router.post("/api/v1/historical/preview", response_model=HistoricalPreviewResponse, tags=["Historical Attendance"])
def preview_historical_import(
    payload: Optional[HistoricalPreviewRequest] = None,
    db: Session = Depends(get_db),
) -> HistoricalPreviewResponse:
    """Preview workload, requests, and conservative pacing for proposed term backfill."""
    service = HistoricalDiscoveryService(db)
    inv = service.get_persisted_inventory()
    keys = payload.selected_term_keys if payload else None
    try:
        prev = service.build_preview(inv, selected_term_keys=keys)
    except ValueError:
        raise HTTPException(status_code=400, detail="Selected term was not discovered.") from None
    approval_id = None
    source_course_count = None
    if len(prev.selected_terms) == 1 and prev.selected_terms[0].details.get("selector_verified"):
        from app.adapters.portal_safety import validate_result
        term = prev.selected_terms[0]
        if not _SYNC_LOCK.acquire(blocking=False):
            raise HTTPException(409, "The portal is busy. Wait for background discovery to finish before previewing.")
        try:
            source = _live_portal_extractor.extract_live_subject_wise(
                academic_year=term.academic_year, semester=term.semester_number, class_id=term.class_identifier,
            )
            validate_result(source, term.academic_year, term.semester_number, term.class_identifier or "", term.class_display_label or "")
            source_course_count = len(source.snapshot.courses)
        except Exception as error:
            logging.getLogger(__name__).warning("Historical preview stopped: %s", type(error).__name__)
            raise HTTPException(409, "The selected semester's source could not be verified. No attendance was imported.") from None
        finally:
            _SYNC_LOCK.release()
        from app.db.models import SyncJob
        preview_job = SyncJob(source_scope="HISTORICAL_PILOT_PREVIEW", state="COMPLETED",
                              details={"selected_term_keys": keys, "import_daywise": False})
        db.add(preview_job)
        db.commit()
        db.refresh(preview_job)
        approval_id = preview_job.id

    return HistoricalPreviewResponse(
        source_course_count=source_course_count,
        approval_id=approval_id,
        selected_terms=[_map_inventory_item(t) for t in prev.selected_terms],
        total_selected_terms=prev.total_selected_terms,
        total_estimated_requests=prev.total_estimated_requests,
        estimated_pacing_seconds=prev.estimated_pacing_seconds,
        pacing_guidance=prev.pacing_guidance,
        requires_user_approval=prev.requires_user_approval,
    )


@router.post("/api/v1/historical/import", response_model=SyncJobResponse, tags=["Historical Attendance"])
def start_historical_import(
    payload: HistoricalImportRequest,
    db: Session = Depends(get_db),
) -> SyncJobResponse:
    """Start controlled multi-semester historical synchronization with conservative pacing."""
    # Live route/selector verification is required before enabling the supervised pilot.
    if os.environ.get("ATTENDPLAN_ENABLE_HISTORICAL_PILOT") != "1":
        raise HTTPException(status_code=409, detail="Historical pilot is disabled pending supervised route verification.")
    if len(payload.selected_term_keys) != 1:
        raise HTTPException(status_code=400, detail="The supervised pilot requires exactly one term.")
    if payload.import_daywise or payload.max_months_per_term is not None:
        raise HTTPException(status_code=400, detail="First pilot is subject-summary only. Day-wise scope requires separate approval.")
    inv = HistoricalDiscoveryService(db).get_persisted_inventory()
    selected_item = next((t for t in inv.terms if t.term_key == payload.selected_term_keys[0]), None)
    if not selected_item or not selected_item.details.get("selector_verified"):
        raise HTTPException(status_code=409, detail="Run verified dependent-selector discovery before the pilot.")
    from app.db.models import SyncJob
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    preview_job = db.get(SyncJob, payload.approval_id) if payload.approval_id else None
    if not preview_job or preview_job.source_scope != "HISTORICAL_PILOT_PREVIEW" or preview_job.details != {
        "selected_term_keys": payload.selected_term_keys, "import_daywise": False
    }:
        raise HTTPException(status_code=409, detail="Preview this exact semester and approve its subject-summary scope first.")
    claimed = db.execute(update(SyncJob).where(
        SyncJob.id == preview_job.id, SyncJob.state == "COMPLETED", SyncJob.created_at >= cutoff
    ).values(state="APPROVED").returning(SyncJob.id).execution_options(synchronize_session=False)).scalar_one_or_none()
    if claimed is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="Preview expired or was already used. Create a fresh preview.")
    db.commit()

    sync_service = SyncJobService(db, extractor=_live_portal_extractor)
    job = sync_service.create_job(
        source_scope="HISTORICAL_MULTI_SEMESTER_BACKFILL",
        progress_total=1,
        details={
            "selected_term_keys": payload.selected_term_keys,
            "import_daywise": payload.import_daywise,
            "max_months_per_term": payload.max_months_per_term,
        },
    )

    backfill_service = HistoricalBackfillService(db, extractor=_live_portal_extractor)
    job = backfill_service.run_historical_backfill(
        job_id=job.id,
        selected_term_keys=payload.selected_term_keys,
        import_daywise=payload.import_daywise,
        max_months_per_term=payload.max_months_per_term,
    )

    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=job.details,
    )


@router.get("/api/v1/historical/import/progress", response_model=SyncJobResponse, tags=["Historical Attendance"])
def get_historical_import_progress(db: Session = Depends(get_db)) -> SyncJobResponse:
    """Fetch status and progress of the currently running or most recent historical sync job."""
    from app.db.models import SyncJob
    job = db.scalars(select(SyncJob).where(SyncJob.source_scope == "HISTORICAL_MULTI_SEMESTER_BACKFILL").order_by(SyncJob.created_at.desc())).first()

    if not job:
        raise HTTPException(status_code=404, detail="No historical synchronization jobs found.")

    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=job.details,
    )


@router.post("/api/v1/historical/import/cancel", response_model=SyncJobResponse, tags=["Historical Attendance"])
def cancel_historical_import(db: Session = Depends(get_db)) -> SyncJobResponse:
    """Request clean cancellation of an active historical synchronization job."""
    sync_service = SyncJobService(db)
    from app.db.models import SyncJob
    active = db.scalars(select(SyncJob).where(
        SyncJob.source_scope == "HISTORICAL_MULTI_SEMESTER_BACKFILL",
        SyncJob.state.in_(["IDLE", "SYNCING_SUBJECTS", "SYNCING_DAYWISE", "PERSISTING", "RECONCILING"]),
    ).order_by(SyncJob.created_at.desc())).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active historical synchronization job is running.")

    job = sync_service.cancel_job(active.id)
    return SyncJobResponse(
        id=job.id,
        academic_term_id=job.academic_term_id,
        source_scope=job.source_scope,
        state=job.state,
        current_step=job.current_step,
        start_timestamp=job.start_timestamp,
        completion_timestamp=job.completion_timestamp,
        completed_batches=job.completed_batches,
        failed_batches=job.failed_batches,
        progress_total=job.progress_total,
        progress_current=job.progress_current,
        safe_diagnostic_message=job.safe_diagnostic_message,
        details=job.details,
    )


@router.get("/api/v1/historical/overview", response_model=AcademicHistoryResponse, tags=["Historical Attendance"])
def get_historical_overview(
    target: float = Query(default=75.0, gt=0.0, lt=100.0),
    db: Session = Depends(get_db),
) -> AcademicHistoryResponse:
    """Retrieve cross-semester attendance summary and historical progression across all terms."""
    return get_academic_history(target=target, db=db)


@router.get("/api/v1/terms/{term_id}/coverage", response_model=TermCoverageResponse, tags=["Terms"])
def get_term_coverage_endpoint(term_id: str, db: Session = Depends(get_db)) -> TermCoverageResponse:
    """Retrieve granular data coverage report for a specific academic term."""
    service = HistoricalDiscoveryService(db)
    try:
        cov = service.get_term_coverage(term_id)
        return TermCoverageResponse(
            term_id=cov.term_id,
            academic_year=cov.academic_year,
            semester_number=cov.semester_number,
            class_identifier=cov.class_identifier,
            coverage_state=cov.coverage_state.value,
            has_subject_summary=cov.has_subject_summary,
            subject_snapshot_count=cov.subject_snapshot_count,
            subject_courses_count=cov.subject_courses_count,
            candidate_months=cov.candidate_months,
            candidate_month_labels=cov.candidate_month_labels,
            months_attempted=cov.months_attempted,
            months_completed=cov.months_completed,
            unique_instructional_dates=cov.unique_instructional_dates,
            unique_instructional_periods=cov.unique_instructional_periods,
            mapped_periods=cov.mapped_periods,
            unmapped_periods=cov.unmapped_periods,
            missing_or_unreported_periods=cov.missing_or_unreported_periods,
            source_errors_count=cov.source_errors_count,
            reconciliation_verdict=cov.reconciliation_verdict.value,
            details=cov.details,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))





@router.get("/api/v1/terms/{term_id}/attendance/periods", tags=["Analytics"])
def get_attendance_periods(term_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Local period ledger; preserve unknown status and explicit course mappings."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(404, "Semester not found")
    courses = {c.id: c for c in db.scalars(select(Course).where(Course.academic_term_id == term_id)).all()}
    observations = db.scalars(select(AttendancePeriodObservation).where(
        AttendancePeriodObservation.academic_term_id == term_id,
    ).order_by(AttendancePeriodObservation.attendance_date, AttendancePeriodObservation.slot_start_time,
               AttendancePeriodObservation.id)).all()
    observations = latest_observations(observations)
    return {"term_id": term_id, "coverage": "IMPORTED_OBSERVATIONS_ONLY", "periods": [
        {"id": o.id, "date": o.attendance_date.isoformat(), "start": o.slot_start_time,
         "end": o.slot_end_time, "period": o.source_period_identifier,
         "course_code": courses[o.course_id].course_code if o.course_id in courses else None,
         "course_name": courses[o.course_id].course_name if o.course_id in courses else o.source_course_label,
         "status": o.status, "attended": o.attended_period_count, "delivered": o.delivered_period_count}
        for o in observations
    ]}


@router.post("/api/v1/terms/{term_id}/attendance/month-preview", tags=["Analytics"])
def preview_attendance_month(term_id: str, month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
                             db: Session = Depends(get_db)) -> dict[str, Any]:
    """Read one exact calendar month from the verified semester; never ingest it."""
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(404, "Semester not found")
    verified = [t for t in HistoricalDiscoveryService(db).get_persisted_inventory().terms
                if t.details.get("selector_verified") and t.academic_year == term.academic_year
                and t.semester_number == term.semester_number]
    if len(verified) != 1:
        raise HTTPException(409, "Discover and verify this semester in Historical Attendance first.")
    if month[:4] not in term.academic_year.split("-"):
        raise HTTPException(422, "Month must be within this academic year.")
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(409, "The portal is busy. Wait for background discovery to finish.")
    try:
        scope = verified[0]
        result = _live_portal_extractor.extract_live_day_wise(
            academic_year=scope.academic_year, semester=scope.semester_number,
            class_id=scope.class_identifier, month=month[5:], show_course_name=True,
            from_date=month+"-01", to_date=f"{month}-{calendar.monthrange(int(month[:4]), int(month[5:]))[1]:02d}",
        )
        if any(o.attendance_date.isoformat()[:7] != month for o in result.batch.observations):
            raise ValueError("MONTH_YEAR_MISMATCH")
        courses = db.scalars(select(Course).where(Course.academic_term_id == term_id)).all()
        def mapped_code(label: Optional[str]) -> Optional[str]:
            if not label:
                return None
            key = " ".join(label.casefold().split())
            matches = [c.course_code for c in courses if key in {
                c.course_code.casefold(), " ".join(c.course_name.casefold().split()),
            }]
            return matches[0] if len(matches) == 1 else None
        return {"term_id": term_id, "month": month, "persisted": False, "coverage": "LIVE_PREVIEW_ONLY", "periods": [
            {"id": f"preview-{i}", "date": o.attendance_date.isoformat(), "start": o.slot_start_time,
             "end": o.slot_end_time, "period": o.source_period_identifier,
             "course_code": mapped_code(o.source_course_label), "course_name": o.source_course_label,
             "status": o.status.value, "attended": o.attended_period_count, "delivered": o.delivered_period_count}
            for i, o in enumerate(result.batch.observations)
        ]}
    except Exception:
        raise HTTPException(409, "The portal month could not be verified. No records were imported.") from None
    finally:
        _SYNC_LOCK.release()
