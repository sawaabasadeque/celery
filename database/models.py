import uuid
from sqlalchemy import Column, DateTime, String, func, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Backtest(Base):
    __tablename__ = 'backtests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, nullable=False)
    submitted_at = Column(DateTime, server_default=func.now())
    bigquery_table = Column(String, nullable=False)

class Statistic(Base):
    __tablename__ = 'statistics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(UUID(as_uuid=True), ForeignKey('backtests.id'), nullable=False)
    total_return_percentage = Column(Float)
    total_return = Column(Float)
    max_drawdown_percent = Column(Float)
    max_drawdown = Column(Float)
    std_deviation = Column(Float)
    positive_periods = Column(Integer)
    negative_periods = Column(Integer)
    average_daily_return = Column(Float)