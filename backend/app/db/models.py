"""SQLAlchemy 2 database models for AttendPlan F1 schema.

Enforces strict relational integrity, foreign key cascades, uniqueness bounds,
and clean separation of terms, course catalogs, snapshots, and observation batches.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.enums import BatchStatus, CourseType, IngestionOutcome, PeriodStatus, SyncJobState



def generate_uuid() -> str:
    """Generate a random UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy entities."""
    pass


class AcademicTerm(Base):
    """Represents an academic term/semester at an institution."""

    __tablename__ = "academic_terms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    institution_key: Mapped[str] = mapped_column(String(64), nullable=False, default="mrei")
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    class_identifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    academic_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    academic_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    courses: Mapped[list[Course]] = relationship(
        "Course", back_populates="academic_term", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[AttendanceSnapshot]] = relationship(
        "AttendanceSnapshot", back_populates="academic_term", cascade="all, delete-orphan"
    )
    observation_batches: Mapped[list[AttendanceObservationBatch]] = relationship(
        "AttendanceObservationBatch", back_populates="academic_term", cascade="all, delete-orphan"
    )
    sync_jobs: Mapped[list[SyncJob]] = relationship(
        "SyncJob", back_populates="academic_term", cascade="all, delete-orphan"
    )


    __table_args__ = (
        UniqueConstraint(
            "institution_key",
            "academic_year",
            "semester_number",
            "class_identifier",
            name="uq_term_institution_year_sem_class",
        ),
        Index("ix_academic_terms_year_sem", "academic_year", "semester_number"),
    )


class Course(Base):
    """Represents a specific subject/course offered in an academic term."""

    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    academic_term_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False
    )
    course_code: Mapped[str] = mapped_column(String(32), nullable=False)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    course_short_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    faculty_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    credits: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=1.0)
    course_type: Mapped[str] = mapped_column(String(32), default=CourseType.THEORY.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    academic_term: Mapped[AcademicTerm] = relationship("AcademicTerm", back_populates="courses")
    snapshot_rows: Mapped[list[AttendanceSnapshotRow]] = relationship(
        "AttendanceSnapshotRow", back_populates="course", cascade="all, delete-orphan"
    )
    observations: Mapped[list[AttendancePeriodObservation]] = relationship(
        "AttendancePeriodObservation", back_populates="course"
    )

    __table_args__ = (
        UniqueConstraint("academic_term_id", "course_code", name="uq_course_term_code"),
        Index("ix_courses_term_code", "academic_term_id", "course_code"),
    )


class AttendanceSnapshot(Base):
    """Immutable snapshot of subject-wise attendance captured at a specific point in time."""

    __tablename__ = "attendance_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    academic_term_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="HTML_UPLOAD_SUBWISE")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reporting_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reporting_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    academic_term: Mapped[AcademicTerm] = relationship("AcademicTerm", back_populates="snapshots")
    rows: Mapped[list[AttendanceSnapshotRow]] = relationship(
        "AttendanceSnapshotRow", back_populates="snapshot", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("academic_term_id", "content_checksum", name="uq_snapshot_term_checksum"),
        Index("ix_snapshots_term_captured", "academic_term_id", "captured_at"),
    )


class AttendanceSnapshotRow(Base):
    """Individual course record inside an attendance snapshot."""

    __tablename__ = "attendance_snapshot_rows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    snapshot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("attendance_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    attended_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_periods: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    snapshot: Mapped[AttendanceSnapshot] = relationship("AttendanceSnapshot", back_populates="rows")
    course: Mapped[Course] = relationship("Course", back_populates="snapshot_rows")

    __table_args__ = (
        CheckConstraint(
            "attended_periods >= 0 AND delivered_periods >= attended_periods",
            name="ck_snapshot_row_counts_valid",
        ),
        UniqueConstraint("snapshot_id", "course_id", name="uq_snapshot_row_course"),
    )


class AttendanceObservationBatch(Base):
    """Batch of date-wise attendance observations imported together."""

    __tablename__ = "attendance_observation_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    academic_term_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="HTML_UPLOAD_DAYWISE")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    coverage_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_filter_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=BatchStatus.COMPLETE.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    academic_term: Mapped[AcademicTerm] = relationship("AcademicTerm", back_populates="observation_batches")
    observations: Mapped[list[AttendancePeriodObservation]] = relationship(
        "AttendancePeriodObservation", back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("academic_term_id", "content_checksum", name="uq_batch_term_checksum"),
        Index("ix_observation_batches_term_dates", "academic_term_id", "coverage_start_date", "coverage_end_date"),
    )


class AttendancePeriodObservation(Base):
    """Individual class period observation on a calendar date."""

    __tablename__ = "attendance_period_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    observation_batch_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("attendance_observation_batches.id", ondelete="CASCADE"), nullable=False
    )
    academic_term_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_start_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    slot_end_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    source_period_identifier: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    source_course_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=PeriodStatus.UNKNOWN.value, nullable=False)
    delivered_period_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attended_period_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    course_mapping_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    batch: Mapped[AttendanceObservationBatch] = relationship("AttendanceObservationBatch", back_populates="observations")
    academic_term: Mapped[AcademicTerm] = relationship("AcademicTerm")
    course: Mapped[Optional[Course]] = relationship("Course", back_populates="observations")

    __table_args__ = (
        Index("ix_obs_term_date", "academic_term_id", "attendance_date"),
        Index("ix_obs_course_date", "course_id", "attendance_date"),
    )


class IngestionEvent(Base):
    """Audit record for every ingestion attempt (successful, partial, duplicate, or failed)."""

    __tablename__ = "ingestion_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_term_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True
    )
    attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), default=IngestionOutcome.SUCCESS.value, nullable=False)
    safe_error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    associated_snapshot_or_batch: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_ingestion_events_term_attempt", "academic_term_id", "attempt_at"),
    )


class SyncJob(Base):
    """Persistent synchronization job tracking progress, state, and outcomes."""

    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    academic_term_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True
    )
    source_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="CURRENT_SEMESTER_PILOT")
    state: Mapped[str] = mapped_column(String(32), default=SyncJobState.IDLE.value, nullable=False)
    current_step: Mapped[str] = mapped_column(String(128), default="Initialized", nullable=False)
    start_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completion_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_batches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_batches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safe_diagnostic_message: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    academic_term: Mapped[Optional[AcademicTerm]] = relationship("AcademicTerm", back_populates="sync_jobs")

    @property
    def diagnostic(self) -> Optional[str]:
        return self.safe_diagnostic_message

    @diagnostic.setter
    def diagnostic(self, value: Optional[str]) -> None:
        self.safe_diagnostic_message = value

    __table_args__ = (
        Index("ix_sync_jobs_state", "state"),
        Index("ix_sync_jobs_created", "created_at"),
    )



class PerformanceSnapshot(Base):
    """Immutable portal-reported marks/result snapshot, isolated by discovered term."""

    __tablename__ = "performance_snapshots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    term_key: Mapped[str] = mapped_column(String(256), nullable=False)
    view: Mapped[str] = mapped_column(String(16), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="LIVE_PORTAL")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    __table_args__ = (
        UniqueConstraint("term_key", "view", "checksum", name="uq_performance_term_view_checksum"),
        Index("ix_performance_term_captured", "term_key", "captured_at"),
        Index("ix_performance_captured_at", "captured_at"),
    )


class OfficialResultSnapshot(Base):
    """Immutable portal-reported official result snapshot (Data Class B)."""

    __tablename__ = "official_result_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    academic_term_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False
    )
    term_key: Mapped[str] = mapped_column(String(256), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    class_identifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    exam_session: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    exam_session_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_origin: Mapped[str] = mapped_column(String(64), nullable=False, default="LIVE_PORTAL_RESULT_CARD")
    publication_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")
    declaration_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    credits_registered: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credits_earned: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_points_secured: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sgpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cgpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="LIVE_PORTAL")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    academic_term: Mapped[AcademicTerm] = relationship("AcademicTerm")
    courses: Mapped[list[OfficialCourseResultRow]] = relationship(
        "OfficialCourseResultRow", back_populates="snapshot", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("term_key", "checksum", name="uq_official_result_term_checksum"),
        Index("ix_official_result_term", "term_key"),
    )


class OfficialCourseResultRow(Base):
    """Individual subject/course entry in an official result snapshot."""

    __tablename__ = "official_course_result_rows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    snapshot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("official_result_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    course_code: Mapped[str] = mapped_column(String(32), nullable=False)
    course_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    credits: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    grade_point: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    snapshot: Mapped[OfficialResultSnapshot] = relationship("OfficialResultSnapshot", back_populates="courses")
    course: Mapped[Optional[Course]] = relationship("Course")

    __table_args__ = (
        UniqueConstraint("snapshot_id", "course_code", name="uq_official_course_result_snap_code"),
        Index("ix_official_course_result_code", "course_code"),
    )
