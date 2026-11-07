"""Synthetic archive scopes and latest-observation regression checks."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from app.api import archive_routes as archive
from app.services.current_observations import latest_observations


def test_archive_plan_uses_only_verified_terms_and_excludes_future(monkeypatch):
    terms = [
        SimpleNamespace(
            term_key="synthetic4",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            class_display_label="Synthetic4",
            details={"selector_verified": True},
        ),
        SimpleNamespace(term_key="unverified", details={"selector_verified": False}),
    ]
    monkeypatch.setattr(
        archive.HistoricalDiscoveryService,
        "get_persisted_inventory",
        lambda self: SimpleNamespace(terms=terms),
    )
    plan = archive.make_plan(Mock(), date(2026, 3, 2))
    assert len(plan) == 1
    # Sem 4 (even semester, Jan-May 2026) capped at 2026-03: candidate months are 2026-03, 2026-02, 2026-01
    assert plan[0]["months"][0] == "2026-03" and plan[0]["months"][-1] == "2026-01"
    assert len(plan[0]["months"]) == 3


def test_latest_slot_correction_does_not_double_attendance():
    def row(key, captured, status):
        return SimpleNamespace(
            id=key,
            attendance_date=date(2026, 9, 1),
            slot_start_time="09:00",
            slot_end_time="09:50",
            source_period_identifier="1",
            batch=SimpleNamespace(observed_at=captured),
            created_at=captured,
            status=status,
        )

    old = row("old", "2026-09-01", "ABSENT")
    new = row("new", "2026-09-02", "PRESENT")
    assert latest_observations([new, old]) == [new]


def test_archive_approval_claims_plan_once_with_sqlite_timestamps(
    tmp_path, monkeypatch
):
    import pytest
    from fastapi import HTTPException
    from sqlalchemy.orm import Session
    from app.db.models import Base, SyncJob
    from app.db.session import build_sqlite_url, create_app_engine

    engine = create_app_engine(build_sqlite_url(tmp_path / "archive.sqlite3"))
    Base.metadata.create_all(engine)
    monkeypatch.setattr(archive.threading, "Thread", Mock())
    with Session(engine) as db:
        job = SyncJob(
            source_scope="ATTENDANCE_ARCHIVE_PLAN",
            state="PREVIEW_READY",
            details={"terms": []},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        result = archive.start(archive.Approval(plan_id=job.id, approved=True), db)
        assert result["state"] == "APPROVED"
        with pytest.raises(HTTPException):
            archive.start(archive.Approval(plan_id=job.id, approved=True), db)
    engine.dispose()


def test_archive_worker_saves_summary_and_month_to_same_term_and_deduplicates(
    tmp_path, monkeypatch
):
    from sqlalchemy import select
    from sqlalchemy.orm import Session, sessionmaker
    from app.db.models import (
        Base,
        SyncJob,
        AcademicTerm,
        AttendanceSnapshot,
        AttendanceObservationBatch,
    )
    from app.db.session import build_sqlite_url, create_app_engine
    from app.adapters.html_parser import ERPAttendanceParser
    from app.adapters.daywise_parser import ERPDaywiseParser

    fixture_dir = __import__("pathlib").Path(__file__).parent / "fixtures"
    snapshot = ERPAttendanceParser().parse_html(
        (fixture_dir / "synthetic_semester4_subjectwise.html").read_text()
    )
    batch = ERPDaywiseParser().parse_html(
        (fixture_dir / "synthetic_semester4_daywise.html").read_text()
    )
    valid = SimpleNamespace(is_valid=True, quarantined=False, percentage_deviations=[])
    extractor = Mock()
    extractor.extract_live_subject_wise.return_value = SimpleNamespace(
        snapshot=snapshot,
        academic_year="2025-2026",
        semester=4,
        class_identifier=snapshot.class_name,
        validation=valid,
    )
    extractor.extract_live_day_wise.return_value = SimpleNamespace(
        batch=batch,
        academic_year="2025-2026",
        semester=4,
        class_identifier=batch.class_identifier,
        validation=valid,
    )
    monkeypatch.setattr(archive.portal, "_live_portal_extractor", extractor)
    monkeypatch.setattr(
        archive.portal._login_orchestrator,
        "orchestrate_login",
        lambda: SimpleNamespace(success=True),
    )
    monkeypatch.setattr(archive.time, "sleep", lambda _: None)
    engine = create_app_engine(build_sqlite_url(tmp_path / "archive-worker.sqlite3"))
    Base.metadata.create_all(engine)
    monkeypatch.setattr(archive, "SessionLocal", sessionmaker(engine))
    for _ in range(2):
        with Session(engine) as db:
            job = SyncJob(
                source_scope="ATTENDANCE_ARCHIVE_PLAN",
                state="APPROVED",
                details={
                    "terms": [
                        {
                            "term_key": "synthetic4",
                            "year": "2025-2026",
                            "semester": 4,
                            "class_id": "2140",
                            "class_label": snapshot.class_name,
                            "months": ["2026-03"],
                        }
                    ]
                },
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            key = job.id
        archive.run(key)
        with Session(engine) as db:
            assert db.get(SyncJob, key).state == "COMPLETED"
            assert len(db.scalars(select(AcademicTerm)).all()) == 1
            assert len(db.scalars(select(AttendanceSnapshot)).all()) == 1
            assert len(db.scalars(select(AttendanceObservationBatch)).all()) == 1
    engine.dispose()


def test_restart_pauses_active_archive_and_resume_keeps_completed_reports(
    tmp_path, monkeypatch
):
    from sqlalchemy.orm import Session, sessionmaker
    from app.db.models import Base, SyncJob
    from app.db.session import build_sqlite_url, create_app_engine

    engine = create_app_engine(build_sqlite_url(tmp_path / "archive-recovery.sqlite3"))
    Base.metadata.create_all(engine)
    monkeypatch.setattr(archive, "SessionLocal", sessionmaker(engine))
    extractor = Mock()
    monkeypatch.setattr(archive.portal, "_live_portal_extractor", extractor)
    monkeypatch.setattr(
        archive.portal._login_orchestrator,
        "orchestrate_login",
        lambda: SimpleNamespace(success=True),
    )
    monkeypatch.setattr(archive.threading, "Thread", Mock())
    with Session(engine) as db:
        job = SyncJob(
            source_scope="ATTENDANCE_ARCHIVE_PLAN",
            state="SYNCING",
            progress_current=2,
            progress_total=2,
            details={
                "terms": [
                    {
                        "term_key": "synthetic4",
                        "year": "2025-2026",
                        "semester": 4,
                        "class_id": "2140",
                        "class_label": "Synthetic class 4",
                        "months": ["2026-03"],
                    }
                ],
                "results": [
                    {
                        "term_key": "synthetic4",
                        "scope": "summary",
                        "outcome": "SUCCESS",
                    },
                    {
                        "term_key": "synthetic4",
                        "month": "2026-03",
                        "outcome": "SUCCESS",
                    },
                ],
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        key = job.id
        archive.recover_interrupted(db)
        assert job.state == "PAUSED" and len(job.details["results"]) == 2
        archive.resume(archive.Approval(plan_id=key, approved=True), db)
    archive.run(key)
    extractor.extract_live_subject_wise.assert_not_called()
    extractor.extract_live_day_wise.assert_not_called()
    with Session(engine) as db:
        assert db.get(SyncJob, key).state == "COMPLETED"
    engine.dispose()
