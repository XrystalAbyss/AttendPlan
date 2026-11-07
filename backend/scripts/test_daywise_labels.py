import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.live_portal_extractor import LivePortalExtractor

extractor = LivePortalExtractor()
for sem, year, cid, m_str in [
    (3, "2025-2026", "1067", "09"),
    (2, "2024-2025", "1048", "02"),
    (1, "2024-2025", "918", "09"),
]:
    res = extractor.extract_live_day_wise(
        academic_year=year,
        semester=sem,
        class_id=cid,
        month=m_str,
        from_date=None,
        to_date=None,
        show_course_name=True,
    )
    labels = sorted(set(o.source_course_label for o in res.batch.observations if o.source_course_label))
    print(f"\n=== Sem {sem} Month {m_str}: {len(res.batch.observations)} observations, {len(labels)} distinct course labels ===")
    for l in labels:
        print(f"  '{l}'")

