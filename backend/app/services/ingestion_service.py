"""Atomic, idempotent ingestion service for AttendPlan F1.

Handles subject-wise snapshots and date-wise observation batches.
Ensures:
- Row-order-independent deduplication via canonical checksums
- Atomic transactions (rollback on failure)
- Course catalog synchronization per academic term
- Conflict tracking for conflicting observation revisions
- Comprehensive audit logging via IngestionEvent
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.daywise_parser import ERPDaywiseParser, ParsedDaywiseBatch
from app.adapters.html_parser import ERPAttendanceParser
from app.db.enums import CourseType, IngestionOutcome
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Course,
    IngestionEvent,
)
from app.domain.models import AttendanceSnapshot as DomainSnapshot
from app.services.checksums import compute_snapshot_checksum


class IngestionService:
    """Service orchestrating atomic persistence of snapshots and observation batches."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest_subject_wise_snapshot(
        self,
        snapshot_domain: DomainSnapshot,
        source: str = "HTML_UPLOAD_SUBWISE",
    ) -> tuple[AttendanceSnapshot, IngestionOutcome]:
        """Ingest a validated subject-wise AttendanceSnapshot.

        Idempotent: If a snapshot with identical canonical checksum exists for the term,
        skips insertion and returns existing snapshot.
        """
        try:
            # 1. Resolve or create AcademicTerm
            term = self._resolve_or_create_term(
                academic_year=snapshot_domain.academic_year,
                semester_number=snapshot_domain.semester,
                class_identifier=snapshot_domain.class_name,
                from_date_str=snapshot_domain.date_range.from_date,
                to_date_str=snapshot_domain.date_range.to_date,
            )

            # 2. Compute canonical checksum over sorted (code, attended, delivered)
            row_tuples = [
                (c.code, c.attended, c.delivered) for c in snapshot_domain.courses
            ]
            checksum = compute_snapshot_checksum(row_tuples)

            # 3. Check for existing identical snapshot in this term
            stmt = select(AttendanceSnapshot).where(
                AttendanceSnapshot.academic_term_id == term.id,
                AttendanceSnapshot.content_checksum == checksum,
            )
            existing = self.db.scalars(stmt).first()
            if existing:
                self._record_event(
                    source=source,
                    term_id=term.id,
                    outcome=IngestionOutcome.DUPLICATE_SKIPPED,
                    associated_id=existing.id,
                )
                self.db.commit()
                return existing, IngestionOutcome.DUPLICATE_SKIPPED

            # 4. Synchronize Course catalog for the term
            course_map: dict[str, Course] = {}
            for c_in in snapshot_domain.courses:
                course = self._upsert_course(
                    term_id=term.id,
                    code=c_in.code,
                    name=c_in.name,
                    short_name=c_in.short_name,
                    faculty=c_in.faculty,
                    credits=c_in.credits,
                    is_lab=c_in.is_lab,
                )
                course_map[c_in.code] = course

            # 5. Create new AttendanceSnapshot entity
            f_date = (
                date.fromisoformat(snapshot_domain.date_range.from_date)
                if snapshot_domain.date_range.from_date
                else None
            )
            t_date = (
                date.fromisoformat(snapshot_domain.date_range.to_date)
                if snapshot_domain.date_range.to_date
                else None
            )

            db_snapshot = AttendanceSnapshot(
                academic_term_id=term.id,
                source=source,
                reporting_start_date=f_date,
                reporting_end_date=t_date,
                content_checksum=checksum,
                record_count=len(snapshot_domain.courses),
            )
            self.db.add(db_snapshot)
            self.db.flush()  # Allocate ID

            # 6. Create Snapshot rows
            for c_in in snapshot_domain.courses:
                course_entity = course_map[c_in.code]
                row = AttendanceSnapshotRow(
                    snapshot_id=db_snapshot.id,
                    course_id=course_entity.id,
                    attended_periods=c_in.attended,
                    delivered_periods=c_in.delivered,
                )
                self.db.add(row)

            self._record_event(
                source=source,
                term_id=term.id,
                outcome=IngestionOutcome.SUCCESS,
                associated_id=db_snapshot.id,
            )

            self.db.commit()
            return db_snapshot, IngestionOutcome.SUCCESS

        except Exception as e:
            self.db.rollback()
            self._record_event(
                source=source,
                term_id=None,
                outcome=IngestionOutcome.FAILED,
                error_code=str(e)[:64],
            )
            self.db.commit()
            raise

    def ingest_daywise_batch(
        self,
        batch_data: ParsedDaywiseBatch,
        source: str = "HTML_UPLOAD_DAYWISE",
    ) -> tuple[AttendanceObservationBatch, IngestionOutcome]:
        """Ingest a parsed day-wise attendance observation batch."""
        try:
            # 1. Resolve AcademicTerm
            term = self._resolve_or_create_term(
                academic_year=batch_data.academic_year,
                semester_number=batch_data.semester,
                class_identifier=batch_data.class_identifier,
            )

            # 2. Check for duplicate batch by checksum
            stmt = select(AttendanceObservationBatch).where(
                AttendanceObservationBatch.academic_term_id == term.id,
                AttendanceObservationBatch.content_checksum == batch_data.content_checksum,
            )
            existing = self.db.scalars(stmt).first()
            if existing:
                self._record_event(
                    source=source,
                    term_id=term.id,
                    outcome=IngestionOutcome.DUPLICATE_SKIPPED,
                    associated_id=existing.id,
                )
                self.db.commit()
                return existing, IngestionOutcome.DUPLICATE_SKIPPED

            # 3. Cache course lookup by code in this term
            term_courses = self.db.scalars(
                select(Course).where(Course.academic_term_id == term.id)
            ).all()
            code_to_course = {c.course_code: c for c in term_courses}

            # 4. Create Batch entity
            db_batch = AttendanceObservationBatch(
                academic_term_id=term.id,
                source=source,
                coverage_start_date=batch_data.coverage_start_date,
                coverage_end_date=batch_data.coverage_end_date,
                source_filter_metadata=batch_data.source_filter_metadata,
                content_checksum=batch_data.content_checksum,
                status=batch_data.status.value,
            )
            self.db.add(db_batch)
            self.db.flush()

            # 5. Insert Observations
            for item in batch_data.observations:
                course_id = None
                confidence = item.course_mapping_confidence
                if item.source_course_label:
                    matched_course = code_to_course.get(item.source_course_label)
                    if matched_course:
                        course_id = matched_course.id
                        confidence = 1.0
                    else:
                        # Auto-create lightweight placeholder course if unknown
                        new_course = Course(
                            academic_term_id=term.id,
                            course_code=item.source_course_label,
                            course_name=f"Course {item.source_course_label}",
                            course_type=CourseType.UNKNOWN.value,
                        )
                        self.db.add(new_course)
                        self.db.flush()
                        code_to_course[item.source_course_label] = new_course
                        course_id = new_course.id
                        confidence = 0.8

                obs = AttendancePeriodObservation(
                    observation_batch_id=db_batch.id,
                    academic_term_id=term.id,
                    attendance_date=item.attendance_date,
                    slot_start_time=item.slot_start_time,
                    slot_end_time=item.slot_end_time,
                    source_period_identifier=item.source_period_identifier,
                    course_id=course_id,
                    source_course_label=item.source_course_label,
                    status=item.status.value,
                    delivered_period_count=item.delivered_period_count,
                    attended_period_count=item.attended_period_count,
                    course_mapping_confidence=confidence,
                )
                self.db.add(obs)

            self._record_event(
                source=source,
                term_id=term.id,
                outcome=IngestionOutcome.SUCCESS,
                associated_id=db_batch.id,
            )

            self.db.commit()
            return db_batch, IngestionOutcome.SUCCESS

        except Exception as e:
            self.db.rollback()
            self._record_event(
                source=source,
                term_id=None,
                outcome=IngestionOutcome.FAILED,
                error_code=str(e)[:64],
            )
            self.db.commit()
            raise

    def ingest_html_auto(
        self,
        html_content: str,
        source: str = "HTML_UPLOAD",
    ) -> dict[str, Any]:
        """Automatically detect HTML page type (subject-wise vs day-wise) and ingest."""
        if "subwise_attendace" in html_content or "Course Wise Attendance" in html_content or "Attended/Delivered" in html_content:
            parser = ERPAttendanceParser()
            snapshot_domain = parser.parse_html(html_content)
            db_snap, outcome = self.ingest_subject_wise_snapshot(snapshot_domain, source=source)
            return {
                "type": "SUBJECT_WISE_SNAPSHOT",
                "id": db_snap.id,
                "term_id": db_snap.academic_term_id,
                "outcome": outcome.value,
                "record_count": db_snap.record_count,
                "content_checksum": db_snap.content_checksum,
            }
        elif "myattendance" in html_content or "daywise" in html_content.lower() or "Time Slot" in html_content:
            daywise_parser = ERPDaywiseParser()
            parsed_batch = daywise_parser.parse_html(html_content)
            db_batch, outcome = self.ingest_daywise_batch(parsed_batch, source=source)
            return {
                "type": "DAY_WISE_BATCH",
                "id": db_batch.id,
                "term_id": db_batch.academic_term_id,
                "outcome": outcome.value,
                "observation_count": len(parsed_batch.observations),
                "coverage_start": db_batch.coverage_start_date.isoformat(),
                "coverage_end": db_batch.coverage_end_date.isoformat(),
                "content_checksum": db_batch.content_checksum,
            }
        else:
            raise ValueError("Unrecognized attendance HTML format. Could not match subject-wise or day-wise table.")

    def _resolve_or_create_term(
        self,
        academic_year: str,
        semester_number: int,
        class_identifier: Optional[str] = None,
        from_date_str: Optional[str] = None,
        to_date_str: Optional[str] = None,
    ) -> AcademicTerm:
        """Find existing AcademicTerm matching natural key or create a new one."""
        stmt = select(AcademicTerm).where(
            AcademicTerm.academic_year == academic_year,
            AcademicTerm.semester_number == semester_number,
            AcademicTerm.class_identifier == class_identifier,
        )
        term = self.db.scalars(stmt).first()

        f_date = date.fromisoformat(from_date_str) if from_date_str else None
        t_date = date.fromisoformat(to_date_str) if to_date_str else None

        if not term:
            term = AcademicTerm(
                academic_year=academic_year,
                semester_number=semester_number,
                class_identifier=class_identifier,
                academic_start_date=f_date,
                academic_end_date=t_date,
            )
            self.db.add(term)
            self.db.flush()
        else:
            # Update dates if missing
            if not term.academic_start_date and f_date:
                term.academic_start_date = f_date
            if not term.academic_end_date and t_date:
                term.academic_end_date = t_date

        return term

    def _upsert_course(
        self,
        term_id: str,
        code: str,
        name: str,
        short_name: Optional[str],
        faculty: Optional[str],
        credits: float,
        is_lab: bool,
    ) -> Course:
        """Find existing Course in term or create a new one, keeping catalog updated."""
        stmt = select(Course).where(
            Course.academic_term_id == term_id,
            Course.course_code == code,
        )
        course = self.db.scalars(stmt).first()

        c_type = CourseType.LAB.value if is_lab else CourseType.THEORY.value

        if not course:
            course = Course(
                academic_term_id=term_id,
                course_code=code,
                course_name=name,
                course_short_name=short_name,
                faculty_name=faculty,
                credits=credits,
                course_type=c_type,
            )
            self.db.add(course)
            self.db.flush()
        else:
            course.course_name = name
            if short_name:
                course.course_short_name = short_name
            if faculty:
                course.faculty_name = faculty
            course.credits = credits
            course.course_type = c_type

        return course

    def _record_event(
        self,
        source: str,
        term_id: Optional[str],
        outcome: IngestionOutcome,
        associated_id: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> IngestionEvent:
        """Record an immutable ingestion audit event."""
        event = IngestionEvent(
            source=source,
            academic_term_id=term_id,
            attempt_at=datetime.now(timezone.utc),
            outcome=outcome.value,
            safe_error_code=error_code,
            associated_snapshot_or_batch=associated_id,
        )
        self.db.add(event)
        return event
