"""Tests for pure Attendance Analytics Engine and Reconciliation Service."""

from __future__ import annotations

from datetime import date
from sqlalchemy.orm import sessionmaker

from app.db.enums import ReconciliationStatus
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Base,
    Course,
)
from app.db.session import create_app_engine
from app.domain.analytics_engine import AttendanceAnalyticsEngine
from app.domain.models import CourseStatus
from app.services.reconciliation_service import ReconciliationService


class TestAttendanceAnalyticsEngine:
    def test_monthly_analytics_separates_years(self) -> None:
        """Invariant: The same month across different calendar years remains strictly separate."""
        observations = [
            # October 2025: 5 delivered, 4 attended
            {
                "attendance_date": date(2025, 10, 5),
                "delivered_period_count": 5,
                "attended_period_count": 4,
            },
            # October 2026: 8 delivered, 6 attended
            {
                "attendance_date": date(2026, 10, 5),
                "delivered_period_count": 8,
                "attended_period_count": 6,
            },
        ]
        monthly = AttendanceAnalyticsEngine.compute_monthly_analytics(observations)
        assert len(monthly) == 2

        oct_2025 = next(m for m in monthly if m.year == 2025 and m.month == 10)
        assert oct_2025.month_label == "October 2025"
        assert oct_2025.delivered == 5
        assert oct_2025.attended == 4
        assert oct_2025.missed == 1
        assert oct_2025.attendance_percentage == 80.0
        assert oct_2025.absence_percentage == 20.0
        assert oct_2025.coverage == "PARTIAL"

        oct_2026 = next(m for m in monthly if m.year == 2026 and m.month == 10)
        assert oct_2026.month_label == "October 2026"
        assert oct_2026.delivered == 8
        assert oct_2026.attended == 6
        assert oct_2026.missed == 2
        assert oct_2026.attendance_percentage == 75.0
        assert oct_2026.absence_percentage == 25.0

    def test_weekday_analytics_and_asia_kolkata_mapping(self) -> None:
        """Verify Monday through Sunday grouping, absence rates, and teaching day volume."""
        # 2026-10-05 is a Monday (weekday 0)
        # 2026-10-06 is a Tuesday (weekday 1)
        # 2026-10-07 is a Wednesday (weekday 2)
        observations = [
            # Monday: 4 delivered, 2 attended (50% absence)
            {
                "attendance_date": date(2026, 10, 5),
                "delivered_period_count": 4,
                "attended_period_count": 2,
            },
            # Tuesday: 6 delivered, 6 attended (0% absence)
            {
                "attendance_date": date(2026, 10, 6),
                "delivered_period_count": 6,
                "attended_period_count": 6,
            },
        ]
        weekday = AttendanceAnalyticsEngine.compute_weekday_analytics(observations)
        assert len(weekday) == 7  # All 7 days present

        monday = next(w for w in weekday if w.weekday_index == 0)
        assert monday.weekday_name == "Monday"
        assert monday.delivered == 4
        assert monday.attended == 2
        assert monday.missed == 2
        assert monday.absence_rate == 50.0
        assert monday.observed_teaching_dates == 1

        tuesday = next(w for w in weekday if w.weekday_index == 1)
        assert tuesday.weekday_name == "Tuesday"
        assert tuesday.delivered == 6
        assert tuesday.attended == 6
        assert tuesday.missed == 0
        assert tuesday.absence_rate == 0.0

        sunday = next(w for w in weekday if w.weekday_index == 6)
        assert sunday.weekday_name == "Sunday"
        assert sunday.delivered == 0
        assert sunday.attended == 0
        assert sunday.absence_rate == 0.0
        assert sunday.coverage == "UNAVAILABLE"

    def test_subject_analytics_and_absence_contribution(self) -> None:
        """Verify subject metrics calculation and absence share computation."""
        records = [
            {
                "code": "CSH301C",
                "name": "CAOR",
                "attended": 15,
                "delivered": 20,
                "course_type": "THEORY",
                "faculty": "Dr. Smith",
                "credits": 3.0,
            },
            {
                "code": "CSH302C",
                "name": "OS",
                "attended": 5,
                "delivered": 10,
                "course_type": "THEORY",
                "faculty": "Dr. Doe",
                "credits": 3.0,
            },
        ]
        # Total missed = (20-15) + (10-5) = 10 missed periods
        # CSH301C missed = 5 -> 50%
        # CSH302C missed = 5 -> 50%
        subj_summary = AttendanceAnalyticsEngine.compute_subject_analytics(records, target=75.0)
        assert len(subj_summary) == 2

        s1 = next(s for s in subj_summary if s.course_code == "CSH301C")
        assert s1.attended == 15
        assert s1.delivered == 20
        assert s1.missed == 5
        assert s1.percentage == 75.0
        assert s1.status == CourseStatus.SAFE
        assert s1.absence_contribution_percentage == 50.0

        s2 = next(s for s in subj_summary if s.course_code == "CSH302C")
        assert s2.attended == 5
        assert s2.delivered == 10
        assert s2.missed == 5
        assert s2.percentage == 50.0
        assert s2.status == CourseStatus.AT_RISK
        assert s2.absence_contribution_percentage == 50.0

    def test_subject_absence_rankings_multi_dimensional(self) -> None:
        """Verify 3 separate ranking dimensions measure distinct behaviors."""
        records = [
            {
                "code": "HIGH_ABS",
                "name": "High Absolute",
                "attended": 20,
                "delivered": 30,  # 10 missed, rate = 33.33%
            },
            {
                "code": "HIGH_RATE",
                "name": "High Rate",
                "attended": 1,
                "delivered": 5,   # 4 missed, rate = 80%
            },
        ]
        subjects = AttendanceAnalyticsEngine.compute_subject_analytics(records)
        rankings = AttendanceAnalyticsEngine.compute_subject_absence_rankings(subjects)

        # Dimension 1: Absolute missed (HIGH_ABS: 10 > HIGH_RATE: 4)
        assert rankings.by_absolute_missed[0][0] == "HIGH_ABS"
        assert rankings.by_absolute_missed[0][2] == 10

        # Dimension 2: Missed rate (HIGH_RATE: 80% > HIGH_ABS: 33.33%)
        assert rankings.by_missed_rate[0][0] == "HIGH_RATE"
        assert rankings.by_missed_rate[0][2] == 80.0

        # Dimension 3: Total delivered (HIGH_ABS: 30 > HIGH_RATE: 5)
        assert rankings.by_total_delivered[0][0] == "HIGH_ABS"
        assert rankings.by_total_delivered[0][2] == 30

    def test_cross_semester_aggregation_never_averages_percentages(self) -> None:
        """Invariant: Cross-semester attendance is sum(att)/sum(del), never average of course percentages."""
        term_data = [
            {
                "term_id": "term1",
                "academic_year": "2025-2026",
                "semester_number": 4,
                "attended": 75,
                "delivered": 100,
                "courses_below_threshold": 1,
                "total_courses": 6,
                "has_datewise_history": False,
            },
            {
                "term_id": "term2",
                "academic_year": "2026-2027",
                "semester_number": 5,
                "attended": 18,
                "delivered": 20,
                "courses_below_threshold": 0,
                "total_courses": 6,
                "has_datewise_history": True,
            },
        ]
        comparison = AttendanceAnalyticsEngine.compute_cross_semester_comparison(term_data, target=75.0)
        assert len(comparison) == 2
        assert comparison[0].semester_number == 4
        assert comparison[0].percentage == 75.0
        assert comparison[0].status == CourseStatus.SAFE
        assert comparison[0].has_datewise_history is False

        assert comparison[1].semester_number == 5
        assert comparison[1].percentage == 90.0
        assert comparison[1].status == CourseStatus.SAFE
        assert comparison[1].has_datewise_history is True


class TestReconciliationService:
    def test_reconciliation_insufficient_data(self) -> None:
        """When neither snapshots nor day-wise observations exist, status is INSUFFICIENT_DATA."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.commit()

            service = ReconciliationService(db)
            report = service.generate_reconciliation_report(term.id)
            assert report.reconciliation_status == ReconciliationStatus.INSUFFICIENT_DATA
            assert report.subject_wise_available is False
            assert report.day_wise_available is False

    def test_reconciliation_partial_coverage_subject_only(self) -> None:
        """When only subject-wise snapshots exist, status is PARTIAL_COVERAGE."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.flush()

            course = Course(academic_term_id=term.id, course_code="CS1", course_name="Course 1")
            snap = AttendanceSnapshot(academic_term_id=term.id, content_checksum="chk1", record_count=1)
            db.add_all([course, snap])
            db.flush()

            row = AttendanceSnapshotRow(
                snapshot_id=snap.id, course_id=course.id, attended_periods=10, delivered_periods=12
            )
            db.add(row)
            db.commit()

            service = ReconciliationService(db)
            report = service.generate_reconciliation_report(term.id)
            assert report.reconciliation_status == ReconciliationStatus.PARTIAL_COVERAGE
            assert report.subject_wise_available is True
            assert report.day_wise_available is False
            assert report.subject_wise_total_attended == 10
            assert report.subject_wise_total_delivered == 12

    def test_reconciliation_matched_and_discrepancy(self) -> None:
        """Verify MATCHED when counts agree, and DISCREPANCY when counts diverge."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.flush()

            course = Course(academic_term_id=term.id, course_code="CS1", course_name="Course 1")
            snap = AttendanceSnapshot(academic_term_id=term.id, content_checksum="chk1", record_count=1)
            batch = AttendanceObservationBatch(
                academic_term_id=term.id,
                coverage_start_date=date(2026, 10, 1),
                coverage_end_date=date(2026, 10, 10),
                content_checksum="chk_batch",
            )
            db.add_all([course, snap, batch])
            db.flush()

            row = AttendanceSnapshotRow(
                snapshot_id=snap.id, course_id=course.id, attended_periods=2, delivered_periods=2
            )
            # Add matching day-wise observations (2 periods delivered, 2 attended)
            obs1 = AttendancePeriodObservation(
                observation_batch_id=batch.id,
                academic_term_id=term.id,
                attendance_date=date(2026, 10, 1),
                course_id=course.id,
                source_course_label="CS1",
                delivered_period_count=1,
                attended_period_count=1,
            )
            obs2 = AttendancePeriodObservation(
                observation_batch_id=batch.id,
                academic_term_id=term.id,
                attendance_date=date(2026, 10, 2),
                course_id=course.id,
                source_course_label="CS1",
                delivered_period_count=1,
                attended_period_count=1,
            )
            db.add_all([row, obs1, obs2])
            db.commit()

            service = ReconciliationService(db)
            report = service.generate_reconciliation_report(term.id)
            assert report.reconciliation_status == ReconciliationStatus.MATCHED
            assert report.subject_wise_total_attended == 2
            assert report.day_wise_total_attended == 2
            assert report.subject_wise_total_delivered == 2
            assert report.day_wise_total_delivered == 2
            assert report.course_breakdown[0].status == "MATCHED"

            # Now add a discrepancy (an extra day observation not in snapshot)
            obs3 = AttendancePeriodObservation(
                observation_batch_id=batch.id,
                academic_term_id=term.id,
                attendance_date=date(2026, 10, 3),
                course_id=course.id,
                source_course_label="CS1",
                delivered_period_count=1,
                attended_period_count=0,
            )
            db.add(obs3)
            db.commit()

            report2 = service.generate_reconciliation_report(term.id)
            assert report2.reconciliation_status == ReconciliationStatus.DISCREPANCY
            assert report2.course_breakdown[0].status == "DISCREPANCY"
            assert report2.course_breakdown[0].delivered_diff == 1

    def test_reconciliation_scope_mismatch_date_window(self) -> None:
        """Verify that when day-wise covers a narrower date window than snapshot, status is SCOPE_MISMATCH."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.flush()

            course = Course(academic_term_id=term.id, course_code="CS1", course_name="Course 1")
            # Snapshot covers up to Oct 31 with 10 delivered periods
            snap = AttendanceSnapshot(
                academic_term_id=term.id,
                content_checksum="chk_snap_full",
                record_count=1,
                reporting_start_date=date(2026, 10, 1),
                reporting_end_date=date(2026, 10, 31),
            )
            # Day-wise batch only covers Oct 1 to Oct 10 with 3 delivered periods
            batch = AttendanceObservationBatch(
                academic_term_id=term.id,
                coverage_start_date=date(2026, 10, 1),
                coverage_end_date=date(2026, 10, 10),
                content_checksum="chk_batch_partial",
            )
            db.add_all([course, snap, batch])
            db.flush()

            row = AttendanceSnapshotRow(
                snapshot_id=snap.id, course_id=course.id, attended_periods=8, delivered_periods=10
            )
            obs = AttendancePeriodObservation(
                observation_batch_id=batch.id,
                academic_term_id=term.id,
                attendance_date=date(2026, 10, 5),
                course_id=course.id,
                source_course_label="CS1",
                delivered_period_count=3,
                attended_period_count=3,
            )
            db.add_all([row, obs])
            db.commit()

            service = ReconciliationService(db)
            report = service.generate_reconciliation_report(term.id)
            # Crucial Gate A: Must report SCOPE_MISMATCH, NOT false DISCREPANCY!
            assert report.reconciliation_status == ReconciliationStatus.SCOPE_MISMATCH
            assert "Scope non-comparability detected" in (report.status_explanation or "")
