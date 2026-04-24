"""SQLite database models and engine setup."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    claim_category = Column(String, nullable=False)
    treatment_date = Column(String, nullable=False)
    claimed_amount = Column(Float, nullable=False)
    decision = Column(String, nullable=True)
    approved_amount = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    decision_json = Column(JSON, nullable=True)  # Full ClaimDecision as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
