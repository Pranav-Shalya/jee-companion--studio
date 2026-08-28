import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatSession(Base):
    """
    SQLAlchemy model representing a persistent mentor doubt coaching session.
    """
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # One-to-many relationship with chat messages
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.timestamp",
        lazy="selectin",
    )


class ChatMessage(Base):
    """
    SQLAlchemy model representing an individual message in a doubt session.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(
        String,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)  # Raw string or JSON serialized payload
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Many-to-one relationship back to the parent session
    session = relationship("ChatSession", back_populates="messages")
