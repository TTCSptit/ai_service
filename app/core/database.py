from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from app.core.config import settings
from sqlalchemy.sql import func
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True,index=True)
    user_id = Column(String,index=True)
    session_id = Column(String,index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime,default=datetime.now)
class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False) 
    long_term_memory = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
class SessionSummary(Base):
    __tablename__ = "session_summaries"
    session_id = Column(String,primary_key=True,index=True)
    summary_text = Column(Text,nullable=False)
    updated_at = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
def init_db():
    Base.metadata.create_all(bind=engine)