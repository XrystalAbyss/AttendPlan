"""Tests for day-wise timetable parsing and atomic idempotent ingestion."""

from pathlib import Path
from typing import Generator
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.daywise_parser import ERPDaywiseParser
from app.adapters.fixture_loader import load_sample_snapshot
from app.db.enums import IngestionOutcome, PeriodStatus
from app.db.models import (
    AttendancePeriodObservation,
    Base,
    IngestionEvent,
)
from app.db.session import create_app_engine
from app.services.checksums import (
    compute_snapshot_checksum,
)
from app.services.ingestion_service import IngestionService

SYNTHETIC_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "synthetic_daywise_attendance.html"
)


class TestDaywiseParsingAndIngestion:
    @pytest.fixture
    def db_session(self) -> Generator[Session, None, None]:
        engine = create_app_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            yield session

    def test_daywise_parser_period_semantics(self) -> None:
        """Verify P, A, blank cells, and lab 2-period multipliers in timetable parsing."""
        html = SYNTHETIC_FIXTURE_PATH.read_text(encoding="utf-8")
        parser = ERPDaywiseParser()
        batch = parser.parse_html(html)

        assert batch.academic_year == "2026-2027"
        assert batch.semester == 5
        assert len(batch.observations) > 0

        # Filter observations by status
        present_obs = [o for o in batch.observations if o.status == PeriodStatus.PRESENT]
        absent_obs = [o for o in batch.observations if o.status == PeriodStatus.ABSENT]
        blank_obs = [o for o in batch.observations if o.status == PeriodStatus.NOT_REPORTED]

        assert len(present_obs) > 0
        assert len(absent_obs) > 0
        assert len(blank_obs) > 0

        # Invariant: Blank cells must NOT count as absence!
        for b in blank_obs:
            assert b.delivered_period_count == 0
            assert b.attended_period_count == 0
            assert b.status == PeriodStatus.NOT_REPORTED

        # Explicit (2P) in synthetic fixture gives delivered=2
        lab_explicit_2p = [
            o for o in batch.observations if o.delivered_period_count == 2
        ]
        assert len(lab_explicit_2p) > 0

    def test_regression_two_lab_slots_not_counted_as_four_periods(self) -> None:
        """Regression test: Two independently observed lab slot rows must count as 2 periods, not 4."""
        sample_lab_html = """
        <table id="daywise_table">
          <thead>
            <tr>
              <th>Time Slot</th>
              <th>15/10/2026 (Thu)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>08:10 - 09:00</td>
              <td><span class="text-success">P</span><br><small>CSH303C LAB</small></td>
            </tr>
            <tr>
              <td>09:00 - 09:50</td>
              <td><span class="text-success">P</span><br><small>CSH303C LAB</small></td>
            </tr>
            <tr>
              <td>09:50 - 10:40</td>
              <td>Holiday</td>
            </tr>
            <tr>
              <td>10:40 - 11:30</td>
              <td></td>
            </tr>
          </tbody>
        </table>
        """
        parser = ERPDaywiseParser()
        batch = parser.parse_html(sample_lab_html)
        assert len(batch.observations) == 4

        # Observations for CSH303C LAB
        lab_slots = [o for o in batch.observations if o.source_course_label == "CSH303C"]
        assert len(lab_slots) == 2
        # Crucial Gate A: Each observed 50-min lab slot row counts as 1 period (total 2), NOT 2 per slot (which would wrongly give 4)
        total_delivered = sum(o.delivered_period_count for o in lab_slots)
        total_attended = sum(o.attended_period_count for o in lab_slots)
        assert total_delivered == 2
        assert total_attended == 2

        # Cell with explicit text 'Holiday' is NO_CLASS
        holiday_obs = [o for o in batch.observations if o.status == PeriodStatus.NO_CLASS]
        assert len(holiday_obs) == 1

        # Blank cell is NOT_REPORTED
        blank_obs = [o for o in batch.observations if o.status == PeriodStatus.NOT_REPORTED]
        assert len(blank_obs) == 1

    def test_canonical_checksum_row_order_independence(self) -> None:
        """Verify canonical checksum is identical regardless of row order in input."""
        rows_order_a = [
            ("CSH301C", 17, 19),
            ("CSH302C", 19, 19),
            ("CDO331", 36, 40),
        ]
        rows_order_b = [
            ("CDO331", 36, 40),
            ("CSH302C", 19, 19),
            ("CSH301C", 17, 19),
        ]

        chk_a = compute_snapshot_checksum(rows_order_a)
        chk_b = compute_snapshot_checksum(rows_order_b)
        assert chk_a == chk_b, "Checksum must be row-order independent!"

    def test_subject_wise_ingestion_idempotency(self, db_session: Session) -> None:
        """Re-ingesting the exact same snapshot must skip insertion and return DUPLICATE_SKIPPED."""
        sample = load_sample_snapshot(target_percentage=75.0)
        service = IngestionService(db_session)

        # 1. First ingestion -> SUCCESS
        snap1, outcome1 = service.ingest_subject_wise_snapshot(sample)
        assert outcome1 == IngestionOutcome.SUCCESS
        assert snap1.record_count == 15

        # 2. Second ingestion of identical snapshot -> DUPLICATE_SKIPPED
        snap2, outcome2 = service.ingest_subject_wise_snapshot(sample)
        assert outcome2 == IngestionOutcome.DUPLICATE_SKIPPED
        assert snap1.id == snap2.id

        # Check IngestionEvent audit trail
        events = db_session.query(IngestionEvent).all()
        assert len(events) == 2
        assert events[0].outcome == "SUCCESS"
        assert events[1].outcome == "DUPLICATE_SKIPPED"

    def test_daywise_batch_ingestion_and_course_linking(self, db_session: Session) -> None:
        """Verify batch ingestion links observations to catalog courses."""
        # Pre-seed term and courses with sample snapshot
        sample = load_sample_snapshot(target_percentage=75.0)
        service = IngestionService(db_session)
        service.ingest_subject_wise_snapshot(sample)

        # Ingest synthetic day-wise batch
        html = SYNTHETIC_FIXTURE_PATH.read_text(encoding="utf-8")
        parsed_batch = ERPDaywiseParser().parse_html(html)

        batch_entity, outcome = service.ingest_daywise_batch(parsed_batch)
        assert outcome == IngestionOutcome.SUCCESS
        assert batch_entity.academic_term_id is not None

        # Check observations mapped to courses
        obs = db_session.query(AttendancePeriodObservation).filter_by(
            observation_batch_id=batch_entity.id
        ).all()
        assert len(obs) > 0
        mapped = [o for o in obs if o.course_id is not None]
        assert len(mapped) > 0
        for m in mapped:
            assert m.course_mapping_confidence >= 0.8
