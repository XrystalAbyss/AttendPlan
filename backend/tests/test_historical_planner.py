"""Unit tests for HistoricalSyncPlanner service."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.portal_session import TermOption
from app.db.models import AcademicTerm, Base
from app.services.historical_planner import HistoricalSyncPlanner, get_standard_semester_months


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_standard_semester_months_odd_and_even() -> None:
    """Odd semesters map to Autumn (Aug-Dec), even semesters map to Spring (Jan-May)."""
    m_odd, labels_odd = get_standard_semester_months(5)
    assert m_odd == ["8", "9", "10", "11", "12"]
    assert "August" in labels_odd
    assert "December" in labels_odd

    m_even, labels_even = get_standard_semester_months(4)
    assert m_even == ["1", "2", "3", "4", "5"]
    assert "January" in labels_even
    assert "May" in labels_even


def test_historical_plan_construction(db_session: Session) -> None:
    """Constructs multi-semester plan with deterministic request counts."""
    planner = HistoricalSyncPlanner(db_session)
    years = [TermOption(value="2026-2027", label="2026-2027"), TermOption(value="2025-2026", label="2025-2026")]
    semesters = [TermOption(value="5", label="Sem 5"), TermOption(value="4", label="Sem 4")]
    classes = [TermOption(value="2582", label="AIML-5")]

    summary = planner.build_plan(years, semesters, classes)

    # 2 years * 2 semesters = 4 scopes
    assert summary.total_terms_count == 4
    assert len(summary.terms) == 4
    # Each odd semester has 1 summary + 4 candidate months (Aug-Nov) = 5 requests
    # Each even semester has 1 summary + 5 candidate months (Jan-May) = 6 requests
    # Total = 5 + 6 + 5 + 6 = 22 requests
    assert summary.total_estimated_requests == 22
    assert "Conservative pacing" in summary.pacing_guidance
    assert summary.recommended_pilot_term is not None


def test_historical_plan_detects_existing_persisted_terms(db_session: Session) -> None:
    """Flags terms that have already been imported to prevent duplicate work."""
    # Pre-insert a term in DB
    term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="AIML-5")
    db_session.add(term)
    db_session.commit()

    planner = HistoricalSyncPlanner(db_session)
    years = [TermOption(value="2026-2027", label="2026-2027")]
    semesters = [TermOption(value="5", label="Sem 5")]

    summary = planner.build_plan(years, semesters, [])
    assert len(summary.terms) == 1
    scope = summary.terms[0]
    assert scope.academic_year == "2026-2027"
    assert scope.semester == 5
