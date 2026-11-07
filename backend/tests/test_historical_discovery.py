"""Tests for historical term discovery service and preview generation (Milestone F2-E)."""

from __future__ import annotations

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.domain.historical_models import CoverageState, TermDiscoveryStatus
from app.services.historical_discovery_service import HistoricalDiscoveryService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_discover_terms_from_synthetic_html(test_db: Session):
    fixture_path = FIXTURES_DIR / "synthetic_historical_terms_discovery.html"
    assert fixture_path.exists()
    html_content = fixture_path.read_text(encoding="utf-8")

    service = HistoricalDiscoveryService(test_db)
    inventory = service.discover_inventory_from_html(html_content, provenance="SYNTHETIC_TEST_FIXTURE")

    assert inventory.total_terms_count > 0
    assert inventory.provenance == "SYNTHETIC_TEST_FIXTURE"

    assert inventory.total_terms_count == 1
    assert inventory.discovered_years == ["2026-2027"]
    assert inventory.terms[0].semester_number == 5
    assert inventory.terms[0].class_identifier == "2582"
    assert inventory.terms[0].status == TermDiscoveryStatus.NOT_CHECKED
    assert inventory.terms[0].coverage_state == CoverageState.NOT_IMPORTED


def test_historical_preview_generation(test_db: Session):
    fixture_path = FIXTURES_DIR / "synthetic_historical_terms_discovery.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    service = HistoricalDiscoveryService(test_db)
    inventory = service.discover_inventory_from_html(html_content)

    # Preview with specific selected terms
    selected_keys = [inventory.terms[0].term_key]
    preview = service.build_preview(inventory, selected_term_keys=selected_keys)

    assert preview.total_selected_terms == 1
    assert preview.total_estimated_requests == 1
    assert preview.estimated_pacing_seconds > 0
    assert preview.requires_user_approval is True
    assert "1.5s - 2.5s" in preview.pacing_guidance


def test_discover_empty_or_malformed_html(test_db: Session):
    service = HistoricalDiscoveryService(test_db)
    # Empty HTML fallback
    inv = service.discover_inventory_from_html("<html><body><p>No select controls</p></body></html>")
    assert inv.total_terms_count == 0
    assert inv.discovered_years == []


def test_verified_discovery_survives_session_restart(tmp_path, monkeypatch):
    from app.adapters.live_portal_extractor import LivePortalExtractor
    from app.db.session import build_sqlite_url, create_app_engine
    from app.db.models import AcademicTerm
    from sqlalchemy import select
    rows = [{"academic_year":"2025-2026","semester":"4","class_id":"2140","class_label":"Synthetic Class Four"}]
    monkeypatch.setattr(LivePortalExtractor,"discover_historical_combinations",lambda self: rows)
    engine = create_app_engine(build_sqlite_url(tmp_path / "discovery.sqlite3"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        inventory = HistoricalDiscoveryService(db).discover_live()
        assert inventory.total_terms_count == 1
        assert db.scalars(select(AcademicTerm)).all() == []
    engine.dispose()
    engine = create_app_engine(build_sqlite_url(tmp_path / "discovery.sqlite3"))
    with Session(engine) as db:
        service = HistoricalDiscoveryService(db)
        inventory = service.get_persisted_inventory()
        assert inventory.terms[0].term_key == "2025-2026_s4_2140"
        assert inventory.terms[0].details["selector_verified"] is True
        preview = service.build_preview(inventory,[inventory.terms[0].term_key])
        assert preview.total_estimated_requests == 1
    engine.dispose()
