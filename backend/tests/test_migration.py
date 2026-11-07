"""Tests for Alembic migration execution, upgrade, and downgrade."""

from __future__ import annotations

import tempfile
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db.session import build_sqlite_url, create_app_engine


def test_alembic_upgrade_and_downgrade() -> None:
    """Verify that Alembic migrations run cleanly up to head and down to base."""
    # Create a fresh temporary SQLite database file
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        temp_path = Path(f.name)

    try:
        db_url = build_sqlite_url(temp_path)
        backend_dir = Path(__file__).parent.parent
        alembic_ini = backend_dir / "alembic.ini"

        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", db_url)
        config.set_main_option("script_location", str(backend_dir / "alembic"))

        # 1. Upgrade to head
        command.upgrade(config, "head")

        # Verify tables were created
        engine = create_app_engine(db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        expected_tables = {
            "academic_terms",
            "courses",
            "attendance_snapshots",
            "attendance_snapshot_rows",
            "attendance_observation_batches",
            "attendance_period_observations",
            "ingestion_events",
            "alembic_version",
        }
        assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"
        engine.dispose()

        # 2. Downgrade to base
        command.downgrade(config, "base")

        # Verify tables were removed (except alembic_version)
        engine = create_app_engine(db_url)
        inspector = inspect(engine)
        remaining_tables = set(inspector.get_table_names())
        assert "academic_terms" not in remaining_tables
        assert "attendance_snapshots" not in remaining_tables
        engine.dispose()

        # 3. Upgrade to head again (verifying idempotency and re-runnability)
        command.upgrade(config, "head")
        engine = create_app_engine(db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        assert expected_tables.issubset(table_names)
        engine.dispose()

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def test_performance_upgrade_preserves_existing_attendance(tmp_path):
    from sqlalchemy.orm import Session
    from app.db.models import AcademicTerm
    target = tmp_path / "legacy.sqlite3"
    backend_dir = Path(__file__).parent.parent
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("sqlalchemy.url",build_sqlite_url(target))
    config.set_main_option("script_location",str(backend_dir / "alembic"))
    command.upgrade(config,"3f1b44a7a3db")
    engine = create_app_engine(build_sqlite_url(target))
    with Session(engine) as db:
        term = AcademicTerm(academic_year="2025-2026",semester_number=4,class_identifier="Synthetic Class Four")
        db.add(term)
        db.commit()
        term_id = term.id
    engine.dispose()
    command.upgrade(config,"head")
    engine = create_app_engine(build_sqlite_url(target))
    with Session(engine) as db:
        term = db.get(AcademicTerm,term_id)
        assert term is not None
        assert term.academic_year == "2025-2026"
        assert term.class_identifier == "Synthetic Class Four"
    assert "performance_snapshots" in inspect(engine).get_table_names()
    engine.dispose()
    # Startup may create the additive table before the migration is stamped.
    command.stamp(config,"3f1b44a7a3db")
    command.upgrade(config,"head")
