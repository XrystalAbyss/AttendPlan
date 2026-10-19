"""Pure deterministic attendance mathematics engine for AttendPlan.

Enforces exact rational arithmetic, avoiding floating-point inaccuracies
before threshold and margin decisions are determined.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import NamedTuple, Optional

from app.domain.models import CourseStatus, InvalidAttendanceError


class AttendanceCalculation(NamedTuple):
    """Immutable calculation result for a single course record."""

    attended: int
    delivered: int
    target_fraction: Fraction
    exact_ratio: Optional[Fraction]
    percent: Optional[float]
    can_skip: Optional[int]
    must_attend: Optional[int]
    status: CourseStatus
    margin_summary: str


def to_target_fraction(target: float | Fraction | int) -> Fraction:
    """Normalize target attendance to a Fraction between 0 and 1.

    Supports inputs like 75, 75.0, 0.75, or Fraction(3, 4).
    """
    if isinstance(target, Fraction):
        frac = target
    elif isinstance(target, int):
        frac = Fraction(target, 100) if target > 1 else Fraction(target, 1)
    elif isinstance(target, float):
        # If passed as 75.0 -> 0.75
        frac = Fraction(round(target * 100), 10000) if target <= 1 else Fraction(round(target * 100), 10000)
        if target > 1:
            frac = Fraction(str(target)) / 100
        else:
            frac = Fraction(str(target))
    else:
        raise ValueError(f"Unsupported target type: {type(target)}")

    if frac <= 0 or frac >= 1:
        raise ValueError(f"Attendance target must be strictly between 0 and 1, got {frac}")

    return frac


def validate_counts(attended: int, delivered: int) -> None:
    """Validate mathematical domain invariants: 0 <= attended <= delivered."""
    if attended < 0:
        raise InvalidAttendanceError(
            f"Attended periods cannot be negative: attended={attended}, delivered={delivered}"
        )
    if delivered < 0:
        raise InvalidAttendanceError(
            f"Delivered periods cannot be negative: attended={attended}, delivered={delivered}"
        )
    if attended > delivered:
        raise InvalidAttendanceError(
            f"Attended periods ({attended}) cannot exceed delivered periods ({delivered})"
        )


def calculate_course_metrics(
    attended: int,
    delivered: int,
    target: float | Fraction | int = 0.75,
) -> AttendanceCalculation:
    """Calculate exact attendance metrics for a single course.

    Invariants:
    1. 0 <= attended <= delivered
    2. For delivered == 0: metrics are undefined (None)
    3. Safe missing periods = max(0, floor(attended / target - delivered))
    4. Consecutive attendance needed = max(0, ceil((target * delivered - attended) / (1 - target)))
    5. Exact rational comparisons used for threshold status
    """
    validate_counts(attended, delivered)
    t = to_target_fraction(target)

    # Invariant 5: For delivered == 0, percentage and margins are unknown
    if delivered == 0:
        return AttendanceCalculation(
            attended=attended,
            delivered=delivered,
            target_fraction=t,
            exact_ratio=None,
            percent=None,
            can_skip=None,
            must_attend=None,
            status=CourseStatus.UNRECORDED,
            margin_summary="No periods delivered yet (unrecorded/pending)",
        )

    exact_ratio = Fraction(attended, delivered)
    # Exact percentage float for presentation
    percent_float = round(float(exact_ratio * 100), 2)

    # Invariant 6: Exact comparison against target fraction
    if exact_ratio >= t:
        # Invariant 3: floor(a / t - d)
        # a / t = a * (1 / t)
        exact_margin = (Fraction(attended) / t) - Fraction(delivered)
        can_skip = max(0, math.floor(exact_margin))
        must_attend = 0
        status = CourseStatus.SAFE
        if can_skip > 0:
            summary = f"Safe to miss up to {can_skip} period{'s' if can_skip > 1 else ''} while staying >= {float(t*100):.0f}%"
        else:
            summary = f"Exactly at {float(t*100):.0f}% threshold; any missed period will drop attendance below target"
    else:
        # Invariant 4: ceil((t * d - a) / (1 - t))
        numerator = (t * Fraction(delivered)) - Fraction(attended)
        denominator = Fraction(1) - t
        needed_exact = numerator / denominator
        must_attend = max(0, math.ceil(needed_exact))
        can_skip = 0
        status = CourseStatus.AT_RISK
        summary = f"Need {must_attend} consecutive period{'s' if must_attend > 1 else ''} attended to reach {float(t*100):.0f}%"

    return AttendanceCalculation(
        attended=attended,
        delivered=delivered,
        target_fraction=t,
        exact_ratio=exact_ratio,
        percent=percent_float,
        can_skip=can_skip,
        must_attend=must_attend,
        status=status,
        margin_summary=summary,
    )


def simulate_period_change(
    attended: int,
    delivered: int,
    delta_attended: int = 0,
    delta_missed: int = 0,
    target: float | Fraction | int = 0.75,
) -> AttendanceCalculation:
    """Simulate additional attended and missed periods.

    Invariant 7: Scenario percentage = (a + x) / (d + x + y),
    where x = delta_attended, y = delta_missed.
    """
    if delta_attended < 0 or delta_missed < 0:
        raise ValueError("Simulation delta counts must be non-negative integers")

    new_attended = attended + delta_attended
    new_delivered = delivered + delta_attended + delta_missed
    return calculate_course_metrics(new_attended, new_delivered, target=target)


def calculate_aggregate_metrics(
    records: list[tuple[int, int]],
    target: float | Fraction | int = 0.75,
) -> tuple[int, int, Optional[float], CourseStatus]:
    """Calculate overall institutional aggregate attendance across multiple courses.

    Invariant 10: Aggregate ratio is sum(attended) / sum(delivered),
    never the average of individual course percentages.
    """
    t = to_target_fraction(target)
    total_attended = sum(a for a, _ in records)
    total_delivered = sum(d for _, d in records)

    validate_counts(total_attended, total_delivered)

    if total_delivered == 0:
        return (0, 0, None, CourseStatus.UNRECORDED)

    ratio = Fraction(total_attended, total_delivered)
    overall_percent = round(float(ratio * 100), 2)
    status = CourseStatus.SAFE if ratio >= t else CourseStatus.AT_RISK
    return (total_attended, total_delivered, overall_percent, status)
