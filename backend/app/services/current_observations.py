"""Keep observation history while aggregating only the latest report of each slot."""

from collections.abc import Iterable
from app.db.models import AttendancePeriodObservation


def latest_observations(
    rows: Iterable[AttendancePeriodObservation],
) -> list[AttendancePeriodObservation]:
    selected: dict[tuple[str, ...], AttendancePeriodObservation] = {}
    for row in sorted(
        rows, key=lambda r: (str(r.batch.observed_at), str(r.created_at), r.id)
    ):
        slot = row.slot_start_time or row.source_period_identifier
        key = (
            (str(row.attendance_date), str(slot), str(row.slot_end_time))
            if slot
            else (row.id,)
        )
        selected[key] = row
    return sorted(
        selected.values(),
        key=lambda r: (r.attendance_date, r.slot_start_time or "", r.id),
    )
