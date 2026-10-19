"""Pure deterministic analytics engine for AttendPlan F1.

Independent of FastAPI, SQLAlchemy, Playwright, or React.
Operates on pure in-memory data structures, adhering to exact rational arithmetic
and strict institutional attendance domain invariants.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Any, Optional, Sequence

from app.domain.attendance_engine import (
    calculate_course_metrics,
    to_target_fraction,
    validate_counts,
)
from app.domain.models import CourseStatus


@dataclass(frozen=True)
class SubjectAttendanceSummary:
    """Aggregated attendance metrics for a single academic course."""

    course_code: str
    course_name: str
    course_type: str
    faculty_name: Optional[str]
    credits: float
    attended: int
    delivered: int
    missed: int
    percentage: Optional[float]
    status: CourseStatus
    can_skip: Optional[int]
    must_attend: Optional[int]
    absence_contribution_percentage: float  # Share of overall term absences
    margin_summary: str


@dataclass(frozen=True)
class MonthlyAttendanceMetrics:
    """Attendance metrics for a specific calendar month and year."""

    year: int
    month: int
    month_label: str  # e.g. "October 2026"
    delivered: int
    attended: int
    missed: int
    attendance_percentage: Optional[float]
    absence_percentage: Optional[float]
    observed_dates_count: int
    coverage: str  # "COMPLETE" | "PARTIAL"


@dataclass(frozen=True)
class WeekdayAttendanceMetrics:
    """Attendance metrics grouped by day of the week (Monday - Sunday)."""

    weekday_index: int  # 0 = Monday, 6 = Sunday
    weekday_name: str  # "Monday", "Tuesday", etc.
    delivered: int
    attended: int
    missed: int
    absence_rate: float
    observed_teaching_dates: int
    coverage: str


@dataclass(frozen=True)
class DailyCourseObservationSummary:
    """Course-level breakdown for a specific date."""

    course_code: str
    slot_label: Optional[str]
    status: str
    attended: int
    delivered: int


@dataclass(frozen=True)
class DailyAttendanceMetrics:
    """Summary of delivered and attended periods on a single calendar date."""

    attendance_date: date
    weekday_name: str
    delivered: int
    attended: int
    missed: int
    percentage: Optional[float]
    courses: list[DailyCourseObservationSummary]
    coverage: str


@dataclass(frozen=True)
class SubjectAbsenceRankings:
    """Multi-dimensional rankings of subjects by absence metrics."""

    by_absolute_missed: list[tuple[str, str, int]]  # (code, name, missed)
    by_missed_rate: list[tuple[str, str, float]]  # (code, name, absence_rate_pct)
    by_total_delivered: list[tuple[str, str, int]]  # (code, name, delivered)


@dataclass(frozen=True)
class SemesterHistoricalMetrics:
    """Summary metrics for cross-semester comparison."""

    term_id: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str]
    attended: int
    delivered: int
    missed: int
    percentage: Optional[float]
    status: CourseStatus
    courses_below_threshold: int
    total_courses: int
    has_datewise_history: bool


WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class AttendanceAnalyticsEngine:
    """Pure analytical engine computing deterministic academic metrics."""

    @staticmethod
    def compute_subject_analytics(
        records: Sequence[dict[str, Any]],
        target: float = 75.0,
    ) -> list[SubjectAttendanceSummary]:
        """Compute metrics for each subject, including absence share."""
        # 1. Total missed across all subjects
        total_missed_all = sum(
            max(0, r["delivered"] - r["attended"]) for r in records if r["delivered"] > 0
        )

        results: list[SubjectAttendanceSummary] = []
        for r in records:
            att = r["attended"]
            deliv = r["delivered"]
            validate_counts(att, deliv)

            missed = deliv - att
            calc = calculate_course_metrics(att, deliv, target=target)

            if total_missed_all > 0 and missed > 0:
                contrib = round((missed / total_missed_all) * 100, 2)
            else:
                contrib = 0.0

            results.append(
                SubjectAttendanceSummary(
                    course_code=r["code"],
                    course_name=r.get("name", r["code"]),
                    course_type=r.get("course_type", "THEORY"),
                    faculty_name=r.get("faculty"),
                    credits=float(r.get("credits", 1.0)),
                    attended=att,
                    delivered=deliv,
                    missed=missed,
                    percentage=calc.percent,
                    status=calc.status,
                    can_skip=calc.can_skip,
                    must_attend=calc.must_attend,
                    absence_contribution_percentage=contrib,
                    margin_summary=calc.margin_summary,
                )
            )

        return results

    @staticmethod
    def compute_monthly_analytics(
        dated_observations: Sequence[dict[str, Any]],
    ) -> list[MonthlyAttendanceMetrics]:
        """Group dated observations by (year, month).

        Invariant: Same month across different calendar years remains strictly separate.
        """
        # Group by (year, month)
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for obs in dated_observations:
            d: date = obs["attendance_date"]
            grouped[(d.year, d.month)].append(obs)

        results: list[MonthlyAttendanceMetrics] = []
        # Sort chronologically by (year, month)
        for (year, month), items in sorted(grouped.items()):
            tot_del = sum(i["delivered_period_count"] for i in items)
            tot_att = sum(i["attended_period_count"] for i in items)
            missed = max(0, tot_del - tot_att)

            observed_dates = len({i["attendance_date"] for i in items})

            # Determine month calendar boundaries
            _, last_day_num = calendar.monthrange(year, month)
            min_date = min(i["attendance_date"] for i in items)
            max_date = max(i["attendance_date"] for i in items)

            # Check explicit coverage indicators from source batch metadata
            is_explicit_complete = any(
                i.get("batch_coverage") == "COMPLETE"
                or (
                    i.get("batch_start")
                    and i.get("batch_end")
                    and i["batch_start"] <= date(year, month, 1)
                    and i["batch_end"] >= date(year, month, last_day_num)
                    and i.get("pagination_complete", True)
                )
                for i in items
            )

            if tot_del == 0:
                att_pct = None
                abs_pct = None
                cov = "UNAVAILABLE"
            elif is_explicit_complete:
                att_pct = round(float(Fraction(tot_att, tot_del) * 100), 2)
                abs_pct = round(float(Fraction(missed, tot_del) * 100), 2)
                cov = "COMPLETE"
            elif min_date > date(year, month, 1) or max_date < date(year, month, last_day_num):
                att_pct = round(float(Fraction(tot_att, tot_del) * 100), 2)
                abs_pct = round(float(Fraction(missed, tot_del) * 100), 2)
                cov = "PARTIAL"
            else:
                att_pct = round(float(Fraction(tot_att, tot_del) * 100), 2)
                abs_pct = round(float(Fraction(missed, tot_del) * 100), 2)
                cov = "UNKNOWN"

            month_str = f"{MONTH_NAMES[month]} {year}"
            results.append(
                MonthlyAttendanceMetrics(
                    year=year,
                    month=month,
                    month_label=month_str,
                    delivered=tot_del,
                    attended=tot_att,
                    missed=missed,
                    attendance_percentage=att_pct,
                    absence_percentage=abs_pct,
                    observed_dates_count=observed_dates,
                    coverage=cov,
                )
            )

        return results

    @staticmethod
    def compute_weekday_analytics(
        dated_observations: Sequence[dict[str, Any]],
    ) -> list[WeekdayAttendanceMetrics]:
        """Group observations by day of week (Monday through Sunday).

        Uses Asia/Kolkata date properties (weekday 0 = Monday).
        """
        # Group by weekday index 0..6
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        dates_per_weekday: dict[int, set[date]] = defaultdict(set)

        for obs in dated_observations:
            d: date = obs["attendance_date"]
            w_idx = d.weekday()  # Monday is 0, Sunday is 6
            grouped[w_idx].append(obs)
            if obs["delivered_period_count"] > 0:
                dates_per_weekday[w_idx].add(d)

        results: list[WeekdayAttendanceMetrics] = []
        # Include all weekdays 0 to 6 (Monday to Sunday)
        for w_idx in range(7):
            items = grouped.get(w_idx, [])
            tot_del = sum(i["delivered_period_count"] for i in items)
            tot_att = sum(i["attended_period_count"] for i in items)
            missed = max(0, tot_del - tot_att)
            teaching_dates_count = len(dates_per_weekday.get(w_idx, set()))

            if tot_del > 0:
                absence_rate = round(float(Fraction(missed, tot_del) * 100), 2)
                cov = "PARTIAL"
            else:
                absence_rate = 0.0
                cov = "UNAVAILABLE"

            results.append(
                WeekdayAttendanceMetrics(
                    weekday_index=w_idx,
                    weekday_name=WEEKDAY_NAMES[w_idx],
                    delivered=tot_del,
                    attended=tot_att,
                    missed=missed,
                    absence_rate=absence_rate,
                    observed_teaching_dates=teaching_dates_count,
                    coverage=cov,
                )
            )

        return results

    @staticmethod
    def compute_daily_analytics(
        dated_observations: Sequence[dict[str, Any]],
    ) -> list[DailyAttendanceMetrics]:
        """Group observations by specific calendar date."""
        grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for obs in dated_observations:
            d: date = obs["attendance_date"]
            grouped[d].append(obs)

        results: list[DailyAttendanceMetrics] = []
        for d, items in sorted(grouped.items()):
            tot_del = sum(i["delivered_period_count"] for i in items)
            tot_att = sum(i["attended_period_count"] for i in items)
            missed = max(0, tot_del - tot_att)

            pct = round(float(Fraction(tot_att, tot_del) * 100), 2) if tot_del > 0 else None

            courses: list[DailyCourseObservationSummary] = [
                DailyCourseObservationSummary(
                    course_code=i.get("source_course_label") or "UNMAPPED",
                    slot_label=i.get("source_period_identifier"),
                    status=i.get("status", "UNKNOWN"),
                    attended=i["attended_period_count"],
                    delivered=i["delivered_period_count"],
                )
                for i in items
                if i["delivered_period_count"] > 0
            ]

            results.append(
                DailyAttendanceMetrics(
                    attendance_date=d,
                    weekday_name=WEEKDAY_NAMES[d.weekday()],
                    delivered=tot_del,
                    attended=tot_att,
                    missed=missed,
                    percentage=pct,
                    courses=courses,
                    coverage="COMPLETE" if tot_del > 0 else "PARTIAL",
                )
            )

        return results

    @staticmethod
    def compute_subject_absence_rankings(
        subjects: Sequence[SubjectAttendanceSummary],
    ) -> SubjectAbsenceRankings:
        """Rank subjects across 3 distinct dimensions."""
        # Active courses with delivered > 0
        active = [s for s in subjects if s.delivered > 0]

        # 1. By absolute missed periods
        by_abs = sorted(
            [(s.course_code, s.course_name, s.missed) for s in active],
            key=lambda x: x[2],
            reverse=True,
        )

        # 2. By missed rate (percentage of subject missed)
        def missed_rate(s: SubjectAttendanceSummary) -> float:
            return round((s.missed / s.delivered) * 100, 2) if s.delivered > 0 else 0.0

        by_rate = sorted(
            [(s.course_code, s.course_name, missed_rate(s)) for s in active],
            key=lambda x: x[2],
            reverse=True,
        )

        # 3. By total delivered periods
        by_deliv = sorted(
            [(s.course_code, s.course_name, s.delivered) for s in active],
            key=lambda x: x[2],
            reverse=True,
        )

        return SubjectAbsenceRankings(
            by_absolute_missed=by_abs,
            by_missed_rate=by_rate,
            by_total_delivered=by_deliv,
        )

    @staticmethod
    def compute_cross_semester_comparison(
        term_data: Sequence[dict[str, Any]],
        target: float = 75.0,
    ) -> list[SemesterHistoricalMetrics]:
        """Aggregate cross-semester attendance summary.

        Invariant: Never averages course percentages to compute semester attendance.
        """
        t_frac = to_target_fraction(target)
        results: list[SemesterHistoricalMetrics] = []

        for item in term_data:
            tot_att = item["attended"]
            tot_del = item["delivered"]
            missed = max(0, tot_del - tot_att)

            if tot_del > 0:
                ratio = Fraction(tot_att, tot_del)
                pct = round(float(ratio * 100), 2)
                status = CourseStatus.SAFE if ratio >= t_frac else CourseStatus.AT_RISK
            else:
                pct = None
                status = CourseStatus.UNRECORDED

            results.append(
                SemesterHistoricalMetrics(
                    term_id=item["term_id"],
                    academic_year=item["academic_year"],
                    semester_number=item["semester_number"],
                    class_identifier=item.get("class_identifier"),
                    attended=tot_att,
                    delivered=tot_del,
                    missed=missed,
                    percentage=pct,
                    status=status,
                    courses_below_threshold=item.get("courses_below_threshold", 0),
                    total_courses=item.get("total_courses", 0),
                    has_datewise_history=item.get("has_datewise_history", False),
                )
            )

        # Sort chronologically by academic year then semester number
        results.sort(key=lambda x: (x.academic_year, x.semester_number))
        return results
