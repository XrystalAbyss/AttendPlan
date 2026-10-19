"""Tests for the pure deterministic attendance mathematics engine.

Verifies all required mathematical invariants:
1. 0 <= a <= d
2. Percentage = 100*a/d for d > 0
3. Safe missing periods = max(0, floor(a/t - d))
4. Consecutive attendance periods needed = max(0, ceil((t*d-a)/(1-t)))
5. For d=0, percentage and attendance margins are unknown (None), not zero
6. All threshold decisions must use exact rational arithmetic
7. Scenario percentage = (a+x)/(d+x+y)
8. Scheduled lab blocks represent their actual counted periods
9. Aggregates use sum(a)/sum(d), never average of percentages
"""

import pytest

from app.domain.attendance_engine import (
    calculate_aggregate_metrics,
    calculate_course_metrics,
    simulate_period_change,
    validate_counts,
)
from app.domain.models import CourseStatus, InvalidAttendanceError


class TestAttendanceMathematicsEngine:
    def test_case_15_over_20(self) -> None:
        """15/20 -> exactly 75%, 0 safe misses, 0 consecutive needed, status SAFE."""
        calc = calculate_course_metrics(attended=15, delivered=20, target=0.75)
        assert calc.percent == 75.0
        assert calc.can_skip == 0
        assert calc.must_attend == 0
        assert calc.status == CourseStatus.SAFE
        assert "drop attendance below target" in calc.margin_summary

    def test_case_10_over_14(self) -> None:
        """10/14 -> 71.428..., 2 consecutive attended periods required."""
        calc = calculate_course_metrics(attended=10, delivered=14, target=0.75)
        assert calc.percent == 71.43
        assert calc.can_skip == 0
        assert calc.must_attend == 2
        assert calc.status == CourseStatus.AT_RISK
        assert "Need 2 consecutive periods" in calc.margin_summary

    def test_case_3_over_5(self) -> None:
        """3/5 -> 60%, 3 consecutive attended periods required."""
        calc = calculate_course_metrics(attended=3, delivered=5, target=0.75)
        assert calc.percent == 60.0
        assert calc.can_skip == 0
        assert calc.must_attend == 3
        assert calc.status == CourseStatus.AT_RISK
        assert "Need 3 consecutive periods" in calc.margin_summary

    def test_case_19_over_19(self) -> None:
        """19/19 -> 100%, 6 safely missed periods at 75%."""
        calc = calculate_course_metrics(attended=19, delivered=19, target=0.75)
        assert calc.percent == 100.0
        assert calc.can_skip == 6
        assert calc.must_attend == 0
        assert calc.status == CourseStatus.SAFE
        assert "Safe to miss up to 6 periods" in calc.margin_summary

    def test_case_0_over_0_unknown(self) -> None:
        """0/0 -> unknown percentage and margins (None), not 0% or 100%."""
        calc = calculate_course_metrics(attended=0, delivered=0, target=0.75)
        assert calc.percent is None
        assert calc.can_skip is None
        assert calc.must_attend is None
        assert calc.status == CourseStatus.UNRECORDED
        assert calc.exact_ratio is None
        assert "unrecorded" in calc.margin_summary.lower()

    def test_missing_two_lab_periods_changes_denominator_by_two(self) -> None:
        """Missing 2 lab periods changes denominator by 2 without changing numerator."""
        # Baseline: 10 attended / 14 delivered
        base = calculate_course_metrics(attended=10, delivered=14, target=0.75)
        assert base.attended == 10
        assert base.delivered == 14

        # Simulate missing a 2-period lab block (delta_attended=0, delta_missed=2)
        sim = simulate_period_change(
            attended=10,
            delivered=14,
            delta_attended=0,
            delta_missed=2,
            target=0.75,
        )
        assert sim.attended == 10
        assert sim.delivered == 16  # Denominator increased by 2
        assert sim.percent == 62.5  # 10/16 = 62.5%
        assert sim.status == CourseStatus.AT_RISK
        # Needed: ceil((0.75 * 16 - 10) / 0.25) = ceil((12 - 10) / 0.25) = 8
        assert sim.must_attend == 8

    def test_attending_two_lab_periods_increases_both(self) -> None:
        """Attending a 2-period lab block increases both numerator and denominator by 2."""
        sim = simulate_period_change(
            attended=10,
            delivered=14,
            delta_attended=2,
            delta_missed=0,
            target=0.75,
        )
        assert sim.attended == 12
        assert sim.delivered == 16
        assert sim.percent == 75.0
        assert sim.status == CourseStatus.SAFE
        assert sim.can_skip == 0
        assert sim.must_attend == 0

    def test_rejection_of_negative_counts(self) -> None:
        """Reject negative attended or delivered counts with InvalidAttendanceError."""
        with pytest.raises(InvalidAttendanceError, match="negative"):
            calculate_course_metrics(attended=-1, delivered=10)

        with pytest.raises(InvalidAttendanceError, match="negative"):
            calculate_course_metrics(attended=5, delivered=-2)

    def test_rejection_of_attended_greater_than_delivered(self) -> None:
        """Reject attended > delivered with InvalidAttendanceError."""
        with pytest.raises(InvalidAttendanceError, match="cannot exceed delivered"):
            calculate_course_metrics(attended=11, delivered=10)

        with pytest.raises(InvalidAttendanceError, match="cannot exceed delivered"):
            validate_counts(attended=21, delivered=20)

    def test_exact_rational_arithmetic_precision(self) -> None:
        """Threshold decisions must use exact rational arithmetic, avoiding float rounding issues."""
        # Ratio 299/400 = 0.7475 (< 0.75)
        calc = calculate_course_metrics(attended=299, delivered=400, target=0.75)
        assert calc.status == CourseStatus.AT_RISK
        assert calc.must_attend == 4  # ceil((300 - 299) / 0.25) = 4

        # Ratio 300/400 = 0.75 (exact threshold)
        calc_exact = calculate_course_metrics(attended=300, delivered=400, target=0.75)
        assert calc_exact.status == CourseStatus.SAFE
        assert calc_exact.must_attend == 0
        assert calc_exact.can_skip == 0

    def test_aggregate_calculation_never_averages_percentages(self) -> None:
        """Aggregate percentage must be sum(a)/sum(d), never average of course percentages.

        Example:
        Course 1: 1/1 (100%)
        Course 2: 0/9 (0%)
        Average of percentages = (100 + 0) / 2 = 50%
        True aggregate = (1 + 0) / (1 + 9) = 1/10 = 10%
        """
        records = [(1, 1), (0, 9)]
        tot_att, tot_del, pct, status = calculate_aggregate_metrics(records, target=0.75)
        assert tot_att == 1
        assert tot_del == 10
        assert pct == 10.0  # NOT 50.0%
        assert status == CourseStatus.AT_RISK
