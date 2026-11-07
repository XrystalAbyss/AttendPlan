import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.live_portal_extractor import LivePortalExtractor

extractor = LivePortalExtractor()
print("Extracting Sem 3 subject-wise...")
res3 = extractor.extract_live_subject_wise(
    academic_year="2025-2026",
    semester=3,
    class_id="1067",
)
print("Sem 3 Validation is_valid:", res3.validation.is_valid, "quarantined:", res3.validation.quarantined)
print(f"Courses: {len(res3.snapshot.courses)}, Attended: {res3.snapshot.summary.total_attended}, Delivered: {res3.snapshot.summary.total_delivered}, %: {res3.snapshot.summary.overall_percentage}%")

