"""Tests for historical multi-semester analytics and mathematical boundary invariants (F2-E)."""

from __future__ import annotations


from app.domain.analytics_engine import AttendanceAnalyticsEngine
from app.domain.attendance_engine import calculate_aggregate_metrics
from app.domain.models import CourseStatus


def test_cross_semester_aggregate_never_averages_percentages():
    """Verify Domain Invariant #10: aggregate attendance is sum(a)/sum(d), NOT average of percentages."""
    # Semester 1: 90 / 100 (90%)
    # Semester 2: 10 / 20 (50%)
    # Naive unweighted average of percentages: (90 + 50) / 2 = 70.0%
    # Exact aggregate: (90 + 10) / (100 + 20) = 100 / 120 = 83.33%
    term_records = [
        {"attended": 90, "delivered": 100, "term_id": "t1", "academic_year": "2024-2025", "semester_number": 1},
        {"attended": 10, "delivered": 20, "term_id": "t2", "academic_year": "2024-2025", "semester_number": 2},
    ]

    metrics = AttendanceAnalyticsEngine.compute_cross_semester_comparison(term_records, target=75.0)
    assert len(metrics) == 2
    assert metrics[0].percentage == 90.0
    assert metrics[1].percentage == 50.0

    tot_att, tot_del, agg_pct, agg_status = calculate_aggregate_metrics(
        [(90, 100), (10, 20)], target=75.0
    )
    assert tot_att == 100
    assert tot_del == 120
    assert agg_pct == 83.33
    assert agg_pct != 70.0  # Must NEVER equal average of percentages!
    assert agg_status == CourseStatus.SAFE


def test_boundary_rational_comparisons_around_75_percent():
    """Verify Domain Invariant #6: exact rational threshold comparisons at 75% boundary."""
    # 74 out of 99: 74/99 = 74.7474...% -> strictly < 75% (AT_RISK)
    # 75 out of 100: exactly 75.0% -> SAFE
    # 299 out of 400: 299/400 = 74.75% -> AT_RISK
    # 3 out of 4: exactly 75.0% -> SAFE
    # 7499 out of 10000: 74.99% -> strictly < 75% (AT_RISK)
    term_data = [
        {"attended": 74, "delivered": 99, "term_id": "t1", "academic_year": "2024-2025", "semester_number": 1},
        {"attended": 75, "delivered": 100, "term_id": "t2", "academic_year": "2024-2025", "semester_number": 2},
        {"attended": 7499, "delivered": 10000, "term_id": "t3", "academic_year": "2025-2026", "semester_number": 3},
        {"attended": 3, "delivered": 4, "term_id": "t4", "academic_year": "2025-2026", "semester_number": 4},
        {"attended": 0, "delivered": 0, "term_id": "t5", "academic_year": "2026-2027", "semester_number": 5},
    ]

    results = AttendanceAnalyticsEngine.compute_cross_semester_comparison(term_data, target=75.0)

    # 74/99 < 75%
    assert results[0].status == CourseStatus.AT_RISK
    # 75/100 == 75%
    assert results[1].status == CourseStatus.SAFE
    # 74.99% < 75%
    assert results[2].status == CourseStatus.AT_RISK
    # 3/4 == 75%
    assert results[3].status == CourseStatus.SAFE
    # 0/0 unrecorded
    assert results[4].status == CourseStatus.UNRECORDED
    assert results[4].percentage is None


def test_historical_semesters_purely_analytical_invariance():
    """Verify that completed historical semesters do not misrepresent retroactive bunk margins."""
    # In historical terms, safe bunk margins represent historical outcome, not future actionability
    term_records = [
        {"attended": 80, "delivered": 100, "term_id": "s1", "academic_year": "2024-2025", "semester_number": 1},
        {"attended": 60, "delivered": 100, "term_id": "s2", "academic_year": "2024-2025", "semester_number": 2},
    ]
    res = AttendanceAnalyticsEngine.compute_cross_semester_comparison(term_records, target=75.0)
    assert res[0].missed == 20
    assert res[1].missed == 40
    assert res[0].status == CourseStatus.SAFE
    assert res[1].status == CourseStatus.AT_RISK
