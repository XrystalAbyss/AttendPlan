"""API routes for AttendPlan F0 + F1.

Preserves all F0 endpoints (/health, /sample, /simulate) and introduces
F1 persistent multi-semester, date-wise analytics, and reconciliation endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
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
    IngestionEventResponse,
    IngestionUploadResponse,
    MonthlyAnalyticsItem,
    OverallDiscoveryResponse,
    PortalSessionStatusResponse,
    SemesterHistoricalItem,
    SnapshotListItem,
    SubjectAbsenceRankingsResponse,
    SubjectAnalyticsItem,
    SubjectAnalyticsResponse,
    SubjectWiseDiscoveryResponse,
    TermAttendanceResponse,
    TermOptionItem,
    TermReconciliationResponse,
    WeekdayAnalyticsItem,
)
from app.adapters.portal_session import (
    AcademicTermDiscoveryAdapter,
    DayWiseAttendanceAdapter,
    OverallAttendanceAdapter,
    PortalSessionManager,
    SubjectWiseAttendanceAdapter,
)
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
    observations = db.scalars(obs_stmt).all()

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
    observations = db.scalars(obs_stmt).all()

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
    observations = db.scalars(obs_stmt).all()

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
