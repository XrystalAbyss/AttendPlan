"""Local marks/result snapshots with explicit source values and conservative insights."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    Course,
    OfficialResultSnapshot as OfficialResultSnapshotModel,
    PerformanceSnapshot,
)


class AssessmentClassification(str, Enum):
    INTERNAL_CONTINUOUS_EVALUATION = "INTERNAL_CONTINUOUS_EVALUATION"
    INTERNAL_MIDTERM = "INTERNAL_MIDTERM"
    PRACTICAL_ASSESSMENT = "PRACTICAL_ASSESSMENT"
    VIVA = "VIVA"
    END_SEMESTER_SOURCE_FIELD = "END_SEMESTER_SOURCE_FIELD"
    UNKNOWN_ASSESSMENT = "UNKNOWN_ASSESSMENT"


class CourseCoverageCategory(str, Enum):
    SOURCE_COURSE_PRESENT = "SOURCE_COURSE_PRESENT"
    SOURCE_COURSE_ABSENT = "SOURCE_COURSE_ABSENT"
    COMPONENT_AGGREGATED = "COMPONENT_AGGREGATED"
    SOURCE_IDENTITY_AMBIGUOUS = "SOURCE_IDENTITY_AMBIGUOUS"
    UNMAPPED_SOURCE_ROW = "UNMAPPED_SOURCE_ROW"


ALIASES = {
    "course_code": {"course code", "subject code", "code"},
    "course_name": {"course name", "subject name", "subject", "course"},
    "internal": {"internal", "internal marks", "cia"},
    "external": {"external", "external marks", "ese"},
    "total": {"total", "total marks", "marks obtained"},
    "maximum": {"maximum", "max marks", "maximum marks"},
    "credits": {"credits", "credit"},
    "grade": {"grade", "letter grade"},
    "grade_point": {"grade point", "grade points"},
    "result": {"result", "status"},
}


def classify_assessment(group: str, name: str, course_code: str = "") -> AssessmentClassification:
    """Classify assessment into standard academic categories based on source column headers."""
    norm_name = " ".join(name.strip().lower().split())
    norm_group = " ".join(group.strip().lower().split())

    # 1. Viva / Oral exams
    if "viva" in norm_name or "viva" in norm_group:
        return AssessmentClassification.VIVA

    # 2. End Semester Examination (even if appearing in internal continuous report)
    if (
        "end semester" in norm_name
        or "end-sem" in norm_name
        or "ese" in norm_name
        or ("external" in norm_group and "end semester" in norm_name)
        or norm_name == "end semester examination"
    ):
        return AssessmentClassification.END_SEMESTER_SOURCE_FIELD

    # 3. Midterm / MST examinations
    if (
        "mid term" in norm_name
        or "midterm" in norm_name
        or "mst" in norm_name
        or "mid-term" in norm_name
    ):
        return AssessmentClassification.INTERNAL_MIDTERM

    # 4. Practical / Laboratory assessments
    if (
        "practical" in norm_name
        or "lab" in norm_name
        or "practical" in norm_group
    ):
        return AssessmentClassification.PRACTICAL_ASSESSMENT

    # 5. Continuous evaluations (CE, assignments, quizzes, etc.)
    if (
        re.match(r"^ce\b", norm_name)
        or "continuous" in norm_name
        or "assignment" in norm_name
        or "quiz" in norm_name
        or "internal" in norm_group
    ):
        return AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION

    return AssessmentClassification.UNKNOWN_ASSESSMENT


def number(text: str) -> float | None:
    if text.strip().lower() in {"", "--", "-", "na", "n/a", "not published", "pending", "ab", "absent", "not applicable"}:
        return None
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        raise ValueError("UNSUPPORTED_MARKS_VALUE") from None
    if not value.is_finite() or value < 0:
        raise ValueError("INVALID_MARKS_VALUE")
    return float(value)


def parse_grouped_marks(table: Any) -> list[dict[str, Any]]:
    """Preserve raw assessment ratios; never invent weighted totals or decode masking."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []
    top = rows[0].find_all("th", recursive=False)
    if not top or not any(int(cell.get("colspan", 1)) > 1 for cell in top):
        return []
    columns: list[dict[str, str]] = []
    leaves = iter(rows[1].find_all("th", recursive=False))
    for cell in top:
        label = cell.get_text(" ", strip=True)
        span = int(cell.get("colspan", 1))
        if int(cell.get("rowspan", 1)) > 1:
            if span != 1:
                raise ValueError("UNSUPPORTED_GROUPED_IDENTITY")
            columns.append({"group":"", "label":label})
        else:
            for _ in range(span):
                leaf = next(leaves, None)
                if leaf is None or int(leaf.get("colspan", 1)) != 1:
                    raise ValueError("UNSUPPORTED_GROUPED_HEADER")
                columns.append({"group":label, "label":leaf.get_text(" ", strip=True)})
    if next(leaves, None) is not None:
        raise ValueError("GROUPED_HEADER_WIDTH_MISMATCH")
    identities = {" ".join(c["label"].lower().split()):i for i,c in enumerate(columns) if not c["group"]}
    code_index = identities.get("subject code", identities.get("course code"))
    name_index = identities.get("subject name", identities.get("course name"))
    if code_index is None or name_index is None:
        return []
    courses = []
    seen_codes: dict[str, int] = {}
    for row in rows[2:]:
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        if len(cells) != len(columns):
            raise ValueError("GROUPED_MARKS_ROW_WIDTH_MISMATCH")
        course: dict[str, Any] = {key: None for key in ALIASES}
        raw_code = cells[code_index].get_text(" ", strip=True)
        raw_name = cells[name_index].get_text(" ", strip=True)
        if not raw_code:
            raise ValueError("MISSING_COURSE_CODE")
        code = raw_code
        if code in seen_codes:
            seen_codes[code] += 1
            n_up = raw_name.upper()
            if "- TUT" in n_up or n_up.endswith("TUT") or "TUTORIAL" in n_up:
                code = f"{code}-TUT"
            elif "- PR" in n_up or n_up.endswith("PR") or "LAB" in n_up:
                code = f"{code}-PR"
            else:
                raise ValueError("DUPLICATE_COURSE_CODE")
        else:
            seen_codes[code] = 1

        course.update(course_code=code, course_name=raw_name, percentage=None, assessments=[])
        for index, column in enumerate(columns):
            if not column["group"]:
                continue
            text = cells[index].get_text(" ",strip=True)
            obtained = maximum = None
            status = "UNREPORTED"
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?\s*/\s*[0-9]+(?:\.[0-9]+)?",text):
                left,right = text.split("/")
                obtained,maximum = number(left),number(right)
                if maximum is None or obtained is None or maximum <= 0 or obtained > maximum:
                    raise ValueError("INVALID_ASSESSMENT_RATIO")
                status = "REPORTED"
            elif text in {"", "-", "--"}:
                pass
            elif set(text) == {"*"}:
                status = "MASKED_BY_PORTAL"
            elif text.lower() in {"ab","absent","na","n/a","not applicable","pending"}:
                status = text.upper()
            else:
                obtained = number(text)
                status = "REPORTED_WITHOUT_MAXIMUM"
            classification = classify_assessment(column["group"], column["label"], course["course_code"]).value
            course["assessments"].append({
                "group": column["group"],
                "name": column["label"],
                "classification": classification,
                "obtained": obtained,
                "maximum": maximum,
                "percentage": round(obtained * 100 / maximum, 2) if obtained is not None and maximum else None,
                "status": status,
            })
        courses.append(course)
    return courses


def parse_performance(html: str) -> dict[str, Any]:
    """Parse recognized columns only. Unknown table formats never become invented marks."""
    soup = BeautifulSoup(html, "html.parser")
    courses: list[dict[str, Any]] = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        grouped = parse_grouped_marks(table)
        if grouped:
            for grouped_course in grouped:
                if grouped_course["course_code"] in seen:
                    raise ValueError("DUPLICATE_COURSE_CODE")
                seen.add(grouped_course["course_code"])
            courses.extend(grouped)
            continue
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [" ".join(c.get_text(" ", strip=True).lower().split()) for c in rows[0].find_all(["th", "td"])]
        mapping = {i: key for i, label in enumerate(header) for key, aliases in ALIASES.items() if label in aliases}
        if "course_code" not in mapping.values() or not {"total", "grade", "internal", "external"}.intersection(mapping.values()):
            continue
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("AMBIGUOUS_MARKS_COLUMNS")
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells or not row.get_text(strip=True):
                continue
            if len(cells) != len(header):
                raise ValueError("UNSUPPORTED_MARKS_ROW")
            course: dict[str, Any] = {key: None for key in ALIASES}
            for index, key in mapping.items():
                text = cells[index].get_text(" ", strip=True)
                course[key] = text or None if key in {"course_code", "course_name", "grade", "result"} else number(text)
            code = course["course_code"]
            if not code or code in seen:
                raise ValueError("MISSING_OR_DUPLICATE_COURSE_CODE")
            seen.add(code)
            if course["total"] is not None and course["maximum"] is not None:
                if course["maximum"] <= 0 or course["total"] > course["maximum"]:
                    raise ValueError("MARKS_EXCEED_MAXIMUM")
            course["percentage"] = (
                round(course["total"] * 100 / course["maximum"], 2)
                if course["total"] is not None and course["maximum"] else None
            )
            courses.append(course)
    # GPA values must be explicitly labelled; never infer a grade scale or formula.
    summary: dict[str, float | None] = {"sgpa": None, "cgpa": None}
    text = soup.get_text(" ", strip=True)
    for key in summary:
        values = re.findall(rf"\b{key}\s*[:=]\s*(\d+(?:\.\d+)?)\b", text, re.I)
        if len(set(values)) > 1:
            raise ValueError("AMBIGUOUS_SEMESTER_RESULT")
        if values:
            summary[key] = number(values[0])
    if not courses and all(v is None for v in summary.values()):
        raise ValueError("NO_RECOGNIZED_MARKS_OR_RESULTS")
    return {"courses": sorted(courses, key=lambda c: c["course_code"]), **summary}


def persist_performance(db: Session, term_key: str, view: str, parsed: dict[str, Any]) -> PerformanceSnapshot:
    checksum = hashlib.sha256(json.dumps(parsed, sort_keys=True).encode()).hexdigest()
    existing = db.scalars(select(PerformanceSnapshot).where(
        PerformanceSnapshot.term_key == term_key, PerformanceSnapshot.view == view,
        PerformanceSnapshot.checksum == checksum,
    )).first()
    if existing:
        return existing
    snapshot = PerformanceSnapshot(term_key=term_key, view=view, checksum=checksum, payload=parsed)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def reconcile_course_coverage(
    db: Session,
    term_key: str,
    payload: dict[str, Any],
    catalog_courses_preloaded: Optional[list[Course]] = None,
) -> dict[str, Any]:
    """Reconcile courses in performance snapshot against academic term catalog courses."""
    perf_courses = {c["course_code"]: c for c in payload.get("courses", [])}
    catalog_courses: list[Course] = []

    if catalog_courses_preloaded is not None:
        catalog_courses = catalog_courses_preloaded
    else:
        parts = term_key.split("_")
        academic_term = None
        if len(parts) >= 2 and parts[1].startswith("s"):
            try:
                academic_year = parts[0]
                semester_number = int(parts[1][1:])
                academic_term = db.scalars(
                    select(AcademicTerm).where(
                        AcademicTerm.academic_year == academic_year,
                        AcademicTerm.semester_number == semester_number,
                    )
                ).first()
            except Exception:
                academic_term = None

        if academic_term:
            catalog_courses = list(
                db.scalars(
                    select(Course).where(Course.academic_term_id == academic_term.id).order_by(Course.course_code)
                ).all()
            )

    reconciled_items = []
    catalog_codes = set()
    for cat in catalog_courses:
        catalog_codes.add(cat.course_code)
        if cat.course_code in perf_courses:
            reconciled_items.append({
                "course_code": cat.course_code,
                "course_name": cat.course_name,
                "category": CourseCoverageCategory.SOURCE_COURSE_PRESENT.value,
                "reason": "Direct 1:1 match in source marks report",
            })
        elif cat.course_code.endswith("-TUT") and cat.course_code[:-4] in perf_courses:
            reconciled_items.append({
                "course_code": cat.course_code,
                "course_name": cat.course_name,
                "category": CourseCoverageCategory.COMPONENT_AGGREGATED.value,
                "reason": f"Tutorial component aggregated under parent course {cat.course_code[:-4]}",
            })
        elif cat.course_code.endswith("-PR") and cat.course_code[:-3] in perf_courses and cat.course_code not in perf_courses:
            reconciled_items.append({
                "course_code": cat.course_code,
                "course_name": cat.course_name,
                "category": CourseCoverageCategory.COMPONENT_AGGREGATED.value,
                "reason": f"Practical component aggregated under parent course {cat.course_code[:-3]}",
            })
        else:
            reconciled_items.append({
                "course_code": cat.course_code,
                "course_name": cat.course_name,
                "category": CourseCoverageCategory.SOURCE_COURSE_ABSENT.value,
                "reason": "Not reported in marks portal (e.g. audit, zero-credit, or external certification)",
            })

    unmapped_rows = []
    for code, pcourse in perf_courses.items():
        if code not in catalog_codes:
            reconciled_items.append({
                "course_code": code,
                "course_name": pcourse.get("course_name", ""),
                "category": CourseCoverageCategory.UNMAPPED_SOURCE_ROW.value,
                "reason": "Course present in marks report but not in attendance catalog",
            })
            unmapped_rows.append(code)

    summary = {
        "total_catalog_courses": len(catalog_courses),
        "total_performance_courses": len(perf_courses),
        "present_count": sum(1 for i in reconciled_items if i["category"] == CourseCoverageCategory.SOURCE_COURSE_PRESENT.value),
        "aggregated_count": sum(1 for i in reconciled_items if i["category"] == CourseCoverageCategory.COMPONENT_AGGREGATED.value),
        "absent_count": sum(1 for i in reconciled_items if i["category"] == CourseCoverageCategory.SOURCE_COURSE_ABSENT.value),
        "unmapped_count": len(unmapped_rows),
        "items": reconciled_items,
    }
    return summary


def overview(db: Session) -> dict[str, Any]:
    snapshots = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.captured_at.desc())).all()
    latest: dict[tuple[str, str], PerformanceSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault((snapshot.term_key, snapshot.view), snapshot)

    if not latest:
        return {
            "terms": [],
            "note": "Only imported semesters are shown. GPA values are portal-reported; passing rules and GPA scales are not assumed.",
        }

    # Batch preload all terms, catalog courses, and official results to eliminate N+1 roundtrips
    all_terms = db.scalars(select(AcademicTerm)).all()
    term_by_key_prefix: dict[str, AcademicTerm] = {}
    for t in all_terms:
        term_by_key_prefix[f"{t.academic_year}_s{t.semester_number}"] = t

    all_courses = db.scalars(select(Course).order_by(Course.course_code)).all()
    courses_by_term_id: dict[str, list[Course]] = {}
    for c in all_courses:
        courses_by_term_id.setdefault(c.academic_term_id, []).append(c)

    all_official = db.scalars(
        select(OfficialResultSnapshotModel).order_by(OfficialResultSnapshotModel.captured_at.desc())
    ).all()
    official_by_term: dict[str, OfficialResultSnapshotModel] = {}
    for off in all_official:
        official_by_term.setdefault(off.term_key, off)

    terms: dict[str, dict[str, Any]] = {}
    for (term_key, view), snap in latest.items():
        term = terms.setdefault(term_key, {"term_key": term_key, "views": {}, "insights": []})
        payload = copy.deepcopy(snap.payload)

        # Dynamically ensure all assessment items have classification populated
        for course in payload.get("courses", []):
            for item in course.get("assessments", []):
                if not item.get("classification"):
                    item["classification"] = classify_assessment(
                        item.get("group", ""), item.get("name", ""), course.get("course_code", "")
                    ).value

        # Resolve preloaded catalog courses for this term_key
        parts = term_key.split("_")
        matched_term = None
        if len(parts) >= 2 and parts[1].startswith("s"):
            matched_term = term_by_key_prefix.get(f"{parts[0]}_{parts[1]}")
        catalog_preloaded = courses_by_term_id.get(matched_term.id, []) if matched_term else []

        course_coverage = reconcile_course_coverage(
            db, term_key, payload, catalog_courses_preloaded=catalog_preloaded
        )
        term["views"][view] = {
            **payload,
            "captured_at": snap.captured_at.isoformat(),
            "provenance": snap.provenance,
            "course_coverage": course_coverage,
        }
        comparable = [c for c in payload["courses"] if c["percentage"] is not None]
        if comparable:
            weakest = min(comparable, key=lambda c: c["percentage"])
            strongest = max(comparable, key=lambda c: c["percentage"])
            term["insights"].append(
                f"{view}: highest recorded percentage {strongest['course_code']} ({strongest['percentage']}%); "
                f"lowest {weakest['course_code']} ({weakest['percentage']}%)."
            )
        assessments: dict[str, list[tuple[str, float]]] = {}
        end_sem_count = 0
        for course in payload["courses"]:
            for item in course.get("assessments", []):
                # Filter out END_SEMESTER_SOURCE_FIELD from internal continuous evaluation insights
                if item.get("classification") == AssessmentClassification.END_SEMESTER_SOURCE_FIELD.value:
                    end_sem_count += 1
                    continue
                if item["percentage"] is not None:
                    assessments.setdefault(item["name"], []).append((course["course_code"], item["percentage"]))
        for name, values in list(assessments.items())[:3]:
            strongest = max(values, key=lambda value: value[1])
            weakest = min(values, key=lambda value: value[1])
            term["insights"].append(
                f"{name}: highest recorded assessment percentage {strongest[0]} ({strongest[1]}%); "
                f"lowest {weakest[0]} ({weakest[1]}%). These are assessment ratios, not weighted final grades."
            )
        if end_sem_count > 0:
            term["insights"].append(
                f"{view}: {end_sem_count} End Semester Examination entries preserved as raw source fields; "
                f"excluded from continuous evaluation analytics."
            )
        missing = sum(c["total"] is None for c in payload["courses"])
        if missing:
            term["insights"].append(f"{view}: {missing} course totals are unpublished or missing; they are excluded from comparisons.")

        # Check for Data Class B Official Academic Results (preloaded)
        official_snap = official_by_term.get(term_key)
        if official_snap:
            term["official_result"] = {
                "publication_status": official_snap.publication_status,
                "sgpa": official_snap.sgpa,
                "cgpa": official_snap.cgpa,
                "captured_at": official_snap.captured_at.isoformat(),
                "provenance": official_snap.provenance,
                "declaration_date": official_snap.declaration_date,
                "credits_registered": official_snap.credits_registered,
                "credits_earned": official_snap.credits_earned,
                "courses_count": len(official_snap.courses),
                "institutional_notice": (official_snap.raw_payload or {}).get("institutional_notice"),
            }
            if official_snap.publication_status == "WITHHELD":
                notice = (official_snap.raw_payload or {}).get("institutional_notice", "")
                term["insights"].append(f"Official Results: Portal feature deactivated by COE Office. {notice}".strip())
            elif official_snap.publication_status == "PUBLISHED":
                term["insights"].append(f"Official Results: PUBLISHED (SGPA: {official_snap.sgpa or '—'}, CGPA: {official_snap.cgpa or '—'}).")
    return {
        "terms": sorted(terms.values(), key=lambda t: t["term_key"]),
        "note": "Only imported semesters are shown. GPA values are portal-reported; passing rules and GPA scales are not assumed.",
    }
