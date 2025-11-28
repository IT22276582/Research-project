"""Database models for Adaptive Scheduler"""
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from pathlib import Path

# Get database URL
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/adaptive_scheduler.db")

Base = declarative_base()


class Session(Base):
    """Study session metadata"""
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    chronotype = Column(String)  # 'morning', 'evening', 'neutral'
    task_type = Column(String)  # 'writing', 'coding', 'reading', 'other'
    
    # Relationships
    keystroke_events = relationship("KeystrokeEvent", back_populates="session")
    context_vectors = relationship("ContextVector", back_populates="session")
    actions = relationship("Action", back_populates="session")
    micro_ema = relationship("MicroEMA", back_populates="session")


class KeystrokeEvent(Base):
    """Keystroke timing events (privacy-preserving: only key codes, not characters)"""
    __tablename__ = "keystroke_events"
    
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    timestamp = Column(Float, nullable=False)  # Unix timestamp
    key_code = Column(Integer, nullable=False)  # Key code (not character)
    event_type = Column(String, nullable=False)  # 'down' or 'up'
    
    # Relationship
    session = relationship("Session", back_populates="keystroke_events")


class ContextVector(Base):
    """Extracted context features"""
    __tablename__ = "context_vectors"
    
    vector_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Features
    mean_iki = Column(Float)
    std_iki = Column(Float)
    typing_speed = Column(Float)  # chars/min
    correction_ratio = Column(Float)  # backspaces / total_keys
    pause_count = Column(Integer)  # pauses >1 second
    session_duration = Column(Float)  # minutes
    time_of_day = Column(Integer)  # 0=morning, 1=afternoon, 2=evening
    cognitive_load = Column(Float)  # Estimated cognitive load [0, 1]
    
    # Relationship
    session = relationship("Session", back_populates="context_vectors")
    actions = relationship("Action", back_populates="context_vector")


class Action(Base):
    """Bandit actions (work/break intervals)"""
    __tablename__ = "actions"
    
    action_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    epoch = Column(Integer, nullable=False)  # Decision epoch number
    work_interval = Column(Integer, nullable=False)  # minutes
    break_duration = Column(Integer, nullable=False)  # minutes
    context_vector_id = Column(Integer, ForeignKey("context_vectors.vector_id"))
    bandit_algorithm = Column(String)  # 'LinUCB', 'ThompsonSampling', 'Neural'
    safety_override = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="actions")
    context_vector = relationship("ContextVector", back_populates="actions")
    reward = relationship("Reward", back_populates="action", uselist=False)


class Reward(Base):
    """Reward values for actions"""
    __tablename__ = "rewards"
    
    reward_id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("actions.action_id"), unique=True)
    immediate_reward = Column(Float)
    delayed_reward = Column(Float, nullable=True)
    final_reward = Column(Float)
    r_progress = Column(Float)  # Task progress component
    r_relief = Column(Float)  # Post-break relief component
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    action = relationship("Action", back_populates="reward")


class MicroEMA(Base):
    """Micro Ecological Momentary Assessment feedback"""
    __tablename__ = "micro_ema"
    
    ema_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    fatigue_level = Column(Integer)  # 1-5 scale
    focus_level = Column(Integer)  # 1-5 scale
    satisfaction = Column(Integer, nullable=True)  # 1-5 scale
    
    # Relationship
    session = relationship("Session", back_populates="micro_ema")


class Metrics(Base):
    """Computed metrics (updated periodically)"""
    __tablename__ = "metrics"
    
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    # Metrics
    PG = Column(Float, nullable=True)  # Personalization Gain
    RPH = Column(Float, nullable=True)  # Regret-per-Hour
    AHL = Column(Float, nullable=True)  # Adaptation Half-Life
    EOI = Column(Float, nullable=True)  # Exploration Overhead Index
    AUC_BUC = Column(Float, nullable=True)  # Area Under Break Utility Curve
    CTU = Column(Float, nullable=True)  # Counterfactual Targeting Uplift
    SPF_variance = Column(Float, nullable=True)  # Stability-Productivity Frontier variance
    SVR = Column(Float, nullable=True)  # Safety-Violation Rate


# Database setup
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

