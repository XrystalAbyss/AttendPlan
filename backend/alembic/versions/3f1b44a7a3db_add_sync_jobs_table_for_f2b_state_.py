"""add sync_jobs table for f2b state machine

Revision ID: 3f1b44a7a3db
Revises: 448d5b554af1
Create Date: 2026-10-19 21:12:05.421602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f1b44a7a3db'
down_revision: Union[str, None] = '448d5b554af1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sync_jobs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('academic_term_id', sa.String(length=64), nullable=True),
        sa.Column('source_scope', sa.String(length=64), nullable=False, server_default='CURRENT_SEMESTER_PILOT'),
        sa.Column('state', sa.String(length=32), nullable=False, server_default='IDLE'),
        sa.Column('current_step', sa.String(length=128), nullable=False, server_default='Initialized'),
        sa.Column('start_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completion_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_batches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_batches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_current', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('safe_diagnostic_message', sa.String(length=256), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['academic_term_id'], ['academic_terms.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('sync_jobs', schema=None) as batch_op:
        batch_op.create_index('ix_sync_jobs_state', ['state'], unique=False)
        batch_op.create_index('ix_sync_jobs_created', ['created_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('sync_jobs', schema=None) as batch_op:
        batch_op.drop_index('ix_sync_jobs_created')
        batch_op.drop_index('ix_sync_jobs_state')
    op.drop_table('sync_jobs')

