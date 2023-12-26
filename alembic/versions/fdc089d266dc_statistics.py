"""statistics

Revision ID: fdc089d266dc
Revises: 89047692d181
Create Date: 2023-12-25 19:58:38.685425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import uuid
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fdc089d266dc'
down_revision: Union[str, None] = '89047692d181'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('backtest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtests.id'), nullable=False),
        sa.Column('total_return_percentage', sa.Float),
        sa.Column('total_return', sa.Float),
        sa.Column('max_drawdown_percent', sa.Float),
        sa.Column('max_drawdown', sa.Float),
        sa.Column('std_deviation', sa.Float),
        sa.Column('positive_periods', sa.Integer),
        sa.Column('negative_periods', sa.Integer),
        sa.Column('average_daily_return', sa.Float)
    )


def downgrade() -> None:
    op.drop_table('statistics')
