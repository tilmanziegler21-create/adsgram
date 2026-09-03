"""Add knowledge_base JSONB column.

Revision ID: 0002_knowledge_base
Revises: 0001_initial
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_knowledge_base"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("knowledge_base", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "knowledge_base")
