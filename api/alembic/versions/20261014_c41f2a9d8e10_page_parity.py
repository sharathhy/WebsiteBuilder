"""page parity: current-site page inventory and preview parity result

Revision ID: c41f2a9d8e10
Revises: 7863c1e92c7e
Create Date: 2026-10-14 21:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c41f2a9d8e10'
down_revision: str | None = '7863c1e92c7e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade() -> None:
    op.add_column(
        'websites',
        sa.Column('page_inventory', JSON, server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column('websites', sa.Column('page_inventory_stats', JSON, nullable=True))
    op.add_column('generated_sites', sa.Column('page_parity', JSON, nullable=True))


def downgrade() -> None:
    op.drop_column('generated_sites', 'page_parity')
    op.drop_column('websites', 'page_inventory_stats')
    op.drop_column('websites', 'page_inventory')
