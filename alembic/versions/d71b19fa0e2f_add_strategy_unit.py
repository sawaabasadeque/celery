"""add_strategy_unit

Revision ID: d71b19fa0e2f
Revises: eeaa7b25f5c6
Create Date: 2024-03-25 19:43:08.066449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd71b19fa0e2f'
down_revision: Union[str, None] = 'eeaa7b25f5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('backtests', 'sell_strike_method', new_column_name='strategy')
    op.add_column('backtests', sa.Column('strategy_unit', sa.Float()))


def downgrade() -> None:
    op.drop_column('backtests', 'strategy_unit')
    op.alter_column('backtests', 'strategy', new_column_name='sell_strike_method')
