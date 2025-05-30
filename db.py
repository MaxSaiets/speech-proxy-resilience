"""
Database logic for transcription history.
- SQLAlchemy ORM, SQLite by default.
- TranscriptionHistory model, session management.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///history.db')
SessionLocal = sessionmaker(bind=engine)

class TranscriptionHistory(Base):
    __tablename__ = 'transcription_history'
    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    provider = Column(String)
    status = Column(String)
    text = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    webhook_url = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

Base.metadata.create_all(bind=engine) 