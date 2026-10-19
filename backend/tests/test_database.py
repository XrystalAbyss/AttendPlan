"""Tests for AttendPlan database layer, relational constraints, and persistence."""

from __future__ import annotations

import tempfile
from pathlib import Path

from typing import Generator
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    AcademicTerm,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Base,
    Course,
)
from app.db.session import build_sqlite_url, create_app_engine


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Provide a temporary SQLite file path for persistence tests."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        p = Path(f.name)
    yield p
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass


class TestDatabasePersistenceAndIntegrity:
    def test_persistence_across_engine_restarts(self, temp_db_path: Path) -> None:
        """Verify data persists on disk when closing engine/session and reopening."""
        db_url = build_sqlite_url(temp_db_path)

        # 1. First process / session: Create tables and insert term & course
        engine1 = create_app_engine(db_url)
        Base.metadata.create_all(bind=engine1)
        Session1 = sessionmaker(bind=engine1)

        with Session1() as db1:
            term = AcademicTerm(
                institution_key="mrei",
                academic_year="2026-2027",
                semester_number=5,
                class_identifier="B.Tech CSE AIML-Sem 5",
            )
            db1.add(term)
            db1.flush()

            course = Course(
                academic_term_id=term.id,
                course_code="CSH301C",
                course_name="Computer Architecture",
                credits=3.0,
            )
            db1.add(course)
            db1.commit()
            term_id = term.id

        engine1.dispose()

        # 2. Second process / session: Open completely fresh engine to same file
        engine2 = create_app_engine(db_url)
        Session2 = sessionmaker(bind=engine2)

        with Session2() as db2:
            reloaded_term = db2.get(AcademicTerm, term_id)
            assert reloaded_term is not None
            assert reloaded_term.academic_year == "2026-2027"
            assert reloaded_term.semester_number == 5

            courses = db2.scalars(
                select(Course).where(Course.academic_term_id == term_id)
            ).all()
            assert len(courses) == 1
            assert courses[0].course_code == "CSH301C"
            assert courses[0].course_name == "Computer Architecture"

        engine2.dispose()

    def test_foreign_key_enforcement(self) -> None:
        """Verify foreign key constraint rejects orphan child insertions."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            # Attempt to insert a Course with non-existent academic_term_id
            orphan_course = Course(
                academic_term_id="non_existent_term_id",
                course_code="CSH999",
                course_name="Orphan Course",
            )
            db.add(orphan_course)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()

    def test_multi_semester_same_course_code_isolation(self) -> None:
        """Verify identical course codes can coexist in different semesters without collision."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term_sem4 = AcademicTerm(
                institution_key="mrei",
                academic_year="2025-2026",
                semester_number=4,
            )
            term_sem5 = AcademicTerm(
                institution_key="mrei",
                academic_year="2026-2027",
                semester_number=5,
            )
            db.add_all([term_sem4, term_sem5])
            db.flush()

            # Same course code in Sem 4 and Sem 5
            c1 = Course(
                academic_term_id=term_sem4.id,
                course_code="RDO202C",
                course_name="Research & Innovation Sem 4",
            )
            c2 = Course(
                academic_term_id=term_sem5.id,
                course_code="RDO202C",
                course_name="Research & Innovation Sem 5",
            )
            db.add_all([c1, c2])
            db.commit()

            assert c1.id != c2.id
            assert c1.course_code == c2.course_code

    def test_snapshot_row_check_constraint(self) -> None:
        """Verify CheckConstraint rejects attended > delivered or negative values."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.flush()

            course = Course(academic_term_id=term.id, course_code="CSH301C", course_name="CAOR")
            snap = AttendanceSnapshot(
                academic_term_id=term.id, content_checksum="chk1", record_count=1
            )
            db.add_all([course, snap])
            db.flush()

            # Invalid: attended (15) > delivered (10)
            invalid_row = AttendanceSnapshotRow(
                snapshot_id=snap.id,
                course_id=course.id,
                attended_periods=15,
                delivered_periods=10,
            )
            db.add(invalid_row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()

    def test_transaction_rollback_leaves_no_orphans(self) -> None:
        """Verify failed transaction rolls back cleanly."""
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as db:
            term = AcademicTerm(academic_year="2026-2027", semester_number=5)
            db.add(term)
            db.commit()
            term_id = term.id

        with SessionLocal() as db:
            try:
                c1 = Course(academic_term_id=term_id, course_code="CSH1", course_name="Valid")
                db.add(c1)
                # Intentionally trigger an error with invalid duplicate
                c2 = Course(academic_term_id=term_id, course_code="CSH1", course_name="Duplicate")
                db.add(c2)
                db.commit()
            except IntegrityError:
                db.rollback()

        # Check that c1 was rolled back and not persisted
        with SessionLocal() as db:
            courses = db.scalars(select(Course).where(Course.academic_term_id == term_id)).all()
            assert len(courses) == 0
