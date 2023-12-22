"""initial_schema

Revision ID: 89047692d181
Revises: 
Create Date: 2023-12-21 09:40:34.834904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import uuid
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '89047692d181'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'backtests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('task_id', sa.String, nullable=False),
        sa.Column('submitted_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('bigquery_table', sa.String, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('backtests')
