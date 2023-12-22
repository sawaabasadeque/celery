from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Backtest(Base):
    __tablename__ = 'backtests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, nullable=False)
    submitted_at = Column(DateTime, server_default=func.now())
    bigquery_table = Column(String, nullable=False)