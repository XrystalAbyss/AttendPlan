"""Add immutable official result snapshots and course rows without modifying attendance or internal marks data."""
from alembic import op
import sqlalchemy as sa

revision = "f2e2_official_results"
down_revision = "f2e1_performance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("official_result_snapshots"):
        op.create_table(
            "official_result_snapshots",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("academic_term_id", sa.String(64), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
            sa.Column("term_key", sa.String(256), nullable=False),
            sa.Column("academic_year", sa.String(32), nullable=False),
            sa.Column("semester_number", sa.Integer(), nullable=False),
            sa.Column("class_identifier", sa.String(128), nullable=True),
            sa.Column("exam_session", sa.String(64), nullable=True),
            sa.Column("exam_session_label", sa.String(128), nullable=True),
            sa.Column("source_origin", sa.String(64), nullable=False, server_default="LIVE_PORTAL_RESULT_CARD"),
            sa.Column("publication_status", sa.String(32), nullable=False, server_default="PUBLISHED"),
            sa.Column("declaration_date", sa.String(32), nullable=True),
            sa.Column("credits_registered", sa.Float(), nullable=True),
            sa.Column("credits_earned", sa.Float(), nullable=True),
            sa.Column("total_points_secured", sa.Float(), nullable=True),
            sa.Column("sgpa", sa.Float(), nullable=True),
            sa.Column("cgpa", sa.Float(), nullable=True),
            sa.Column("checksum", sa.String(64), nullable=False),
            sa.Column("provenance", sa.String(32), nullable=False, server_default="LIVE_PORTAL"),
            sa.Column("raw_payload", sa.JSON(), nullable=False),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("term_key", "checksum", name="uq_official_result_term_checksum"),
        )
        op.create_index("ix_official_result_term", "official_result_snapshots", ["term_key"])

    if not insp.has_table("official_course_result_rows"):
        op.create_table(
            "official_course_result_rows",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("snapshot_id", sa.String(64), sa.ForeignKey("official_result_snapshots.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_id", sa.String(64), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
            sa.Column("course_code", sa.String(32), nullable=False),
            sa.Column("course_name", sa.String(256), nullable=True),
            sa.Column("credits", sa.Float(), nullable=True),
            sa.Column("grade", sa.String(16), nullable=True),
            sa.Column("grade_point", sa.Float(), nullable=True),
            sa.Column("result_status", sa.String(32), nullable=True),
            sa.Column("raw_data", sa.JSON(), nullable=True),
            sa.UniqueConstraint("snapshot_id", "course_code", name="uq_official_course_result_snap_code"),
        )
        op.create_index("ix_official_course_result_code", "official_course_result_rows", ["course_code"])


def downgrade() -> None:
    op.drop_table("official_course_result_rows")
    op.drop_table("official_result_snapshots")

