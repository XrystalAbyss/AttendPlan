"""Add immutable performance snapshots without modifying attendance data."""
from alembic import op
import sqlalchemy as sa

revision = "f2e1_performance"
down_revision = "3f1b44a7a3db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing app startup can create missing tables before Alembic runs.
    if sa.inspect(op.get_bind()).has_table("performance_snapshots"):
        return
    op.create_table("performance_snapshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("term_key", sa.String(256), nullable=False),
        sa.Column("view", sa.String(16), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("term_key", "view", "checksum", name="uq_performance_term_view_checksum"),
    )


def downgrade() -> None:
    op.drop_table("performance_snapshots")
