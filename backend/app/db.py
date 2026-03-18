import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/chat.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    retrievals = relationship("Retrieval", back_populates="message", cascade="all, delete-orphan")


class Retrieval(Base):
    __tablename__ = "retrievals"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    document_id = Column(String(128), nullable=True)
    chunk_text = Column(Text, nullable=False)
    score = Column(Float, nullable=True)

    message = relationship("Message", back_populates="retrievals")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_or_create_default_session(db: Session) -> ChatSession:
    session = db.query(ChatSession).order_by(ChatSession.id.asc()).first()
    if session:
        return session
    session = ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
