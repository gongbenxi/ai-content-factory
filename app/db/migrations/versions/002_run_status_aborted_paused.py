"""allow aborted and paused run statuses

Revision ID: 002
Revises: 001
Create Date: 2026-06-08
"""

from alembic import op


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


NEW_STATUSES = "('drafting', 'reviewing', 'needs_human', 'done', 'published', 'failed', 'paused', 'aborted')"
OLD_STATUSES = "('drafting', 'reviewing', 'needs_human', 'done', 'published', 'failed')"


def upgrade() -> None:
    op.execute("ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check")
    op.execute(f"ALTER TABLE runs ADD CONSTRAINT runs_status_check CHECK (status IN {NEW_STATUSES})")


def downgrade() -> None:
    op.execute("UPDATE runs SET status = 'failed' WHERE status IN ('paused', 'aborted')")
    op.execute("ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check")
    op.execute(f"ALTER TABLE runs ADD CONSTRAINT runs_status_check CHECK (status IN {OLD_STATUSES})")
