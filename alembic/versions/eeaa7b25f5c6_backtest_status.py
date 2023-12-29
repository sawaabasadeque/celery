"""backtest_status

Revision ID: eeaa7b25f5c6
Revises: fdc089d266dc
Create Date: 2023-12-27 10:33:46.602510

"""
from typing import Sequence, Union
from sqlalchemy import Enum

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'eeaa7b25f5c6'
down_revision: Union[str, None] = 'fdc089d266dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make bigquery_table nullable
    op.alter_column('backtests', 'bigquery_table', nullable=True)

    # Create the enum types
    status_enum = sa.Enum('running', 'completed', 'error', name='status_enum', create_type=True)
    sell_strike_method_enum = sa.Enum('percent_under', 'desired_premium', name='sell_strike_method_enum', create_type=True)

    # Create the enum types in the database
    status_enum.create(op.get_bind(), checkfirst=True)
    sell_strike_method_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns
    op.add_column('backtests', sa.Column('start_date', sa.Date))
    op.add_column('backtests', sa.Column('end_date', sa.Date))
    op.add_column('backtests', sa.Column('spread', sa.Integer))
    op.add_column('backtests', sa.Column('initial_portfolio_value', sa.Float))
    op.add_column('backtests', sa.Column('status', sa.Enum(name='status_enum')))
    op.add_column('backtests', sa.Column('sell_strike_method', sa.Enum(name='sell_strike_method_enum')))


def downgrade() -> None:
    op.drop_column('backtests', 'start_date')
    op.drop_column('backtests', 'end_date')
    op.drop_column('backtests', 'status')
    op.drop_column('backtests', 'spread')
    op.drop_column('backtests', 'sell_strike_method')
    op.drop_column('backtests', 'initial_portfolio_value')

    # Drop the enum types
    op.execute('DROP TYPE status_enum')
    op.execute('DROP TYPE sell_strike_method_enum')
