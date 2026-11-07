"""Tests for database migration safety, schema verification, and Alembic revision stamping."""
from __future__ import annotations

from sqlalchemy import create_engine, text

from app.db.models import Base
from app.db.session import HEAD_REQUIRED_TABLES, init_db


def test_clean_db_stamps_head_revision(tmp_path) -> None:
    """A completely empty database initialized via init_db() creates all tables and stamps head."""
    db_file = tmp_path / "clean_user.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")

    init_db(engine)

    with engine.connect() as conn:
        tables = set(engine.dialect.get_table_names(conn))
        assert HEAD_REQUIRED_TABLES.issubset(tables)

        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version is not None
        assert version[0] == "f2e2_official_results"


def test_partial_schema_does_not_blindly_stamp_head(tmp_path) -> None:
    """A partially initialized database missing head tables is NOT stamped with head revision."""
    db_file = tmp_path / "partial_db.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")

    # Create only a subset of tables (e.g. initial F1 tables)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE academic_terms ("
                "id VARCHAR(64) PRIMARY KEY, "
                "name VARCHAR(128) NOT NULL, "
                "academic_year VARCHAR(32) NOT NULL, "
                "semester_number INTEGER NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE courses ("
                "id VARCHAR(64) PRIMARY KEY, "
                "academic_term_id VARCHAR(64) NOT NULL, "
                "code VARCHAR(32) NOT NULL, "
                "title VARCHAR(256) NOT NULL"
                ")"
            )
        )
        # alembic_version table exists but is empty
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
            )
        )

    # Now run init_db without create_all on missing tables
    # (simulate an interrupted schema creation or older incomplete DB)
    # We patch Base.metadata.create_all to do nothing for this test
    original_create_all = Base.metadata.create_all
    try:
        Base.metadata.create_all = lambda bind: None
        init_db(engine)
    finally:
        Base.metadata.create_all = original_create_all

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version is None, "Partially initialized schema must NOT be stamped to head!"


def test_older_valid_database_preserves_its_alembic_revision(tmp_path) -> None:
    """An older database with an existing revision is never overwritten by init_db()."""
    db_file = tmp_path / "older_user.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('f2e1_performance_snapshots')")
        )

    init_db(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version is not None
        assert version[0] == "f2e1_performance_snapshots", "Existing revision must be preserved untouched!"


def test_init_db_is_idempotent(tmp_path) -> None:
    """Repeated calls to init_db() on an already-initialized database are safe and preserve head."""
    db_file = tmp_path / "reinstall_user.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")

    init_db(engine)
    init_db(engine)
    init_db(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "f2e2_official_results"

