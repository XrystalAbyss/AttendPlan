import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import validate_result

extractor = LivePortalExtractor()
print("Extracting Sem 3 2025-09 day-wise...")
res = extractor.extract_live_day_wise(
    academic_year="2025-2026",
    semester=3,
    class_id="1067",
    month="09",
    from_date="2025-09-01",
    to_date="2025-09-30",
    show_course_name=True,
)
validate_result(
    res,
    academic_year="2025-2026",
    semester=3,
    class_id="1067",
    class_label="B.Tech CSE AIML-Sem 3",
    month="2025-09",
    require_dates=False,
)
print("Validation is_valid:", res.validation.is_valid, "quarantined:", res.validation.quarantined)
print(f"Observations: {len(res.batch.observations)}")
att = sum(o.attended_period_count for o in res.batch.observations)
deliv = sum(o.delivered_period_count for o in res.batch.observations)
print(f"Attended: {att}, Delivered: {deliv}")
courses_found = sorted(set(o.source_course_label for o in res.batch.observations if o.source_course_label))
print(f"Attributed course labels ({len(courses_found)}): {courses_found}")

