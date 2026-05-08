from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
from app.core.config import settings
from sqlalchemy.sql import func

# Chuyển đổi URL sang asyncpg
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True,index=True)
    user_id = Column(String,index=True)
    session_id = Column(String,index=True)
    role = Column(String)
    content = Column(Text)
    ai_data_json = Column(Text, nullable=True)
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

class UserSkill(Base):
    __tablename__ = "user_skills"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    skill_name = Column(String, nullable=False)
    exp_point = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()