"""Session tracking and metadata collection"""
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Chronotype(Enum):
    """User chronotype"""
    MORNING = "morning"
    EVENING = "evening"
    NEUTRAL = "neutral"


class TaskType(Enum):
    """Task type"""
    WRITING = "writing"
    CODING = "coding"
    READING = "reading"
    OTHER = "other"


@dataclass
class SessionMetadata:
    """Session metadata structure"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    chronotype: Chronotype = Chronotype.NEUTRAL
    task_type: TaskType = TaskType.OTHER
    
    @property
    def duration_minutes(self) -> float:
        """Get session duration in minutes"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 60.0
        else:
            delta = datetime.utcnow() - self.start_time
            return delta.total_seconds() / 60.0


class SessionTracker:
    """Tracks study sessions"""
    
    def __init__(self, user_id: str, chronotype: Chronotype = Chronotype.NEUTRAL, 
                 task_type: TaskType = TaskType.OTHER):
        """
        Initialize session tracker
        
        Args:
            user_id: User identifier
            chronotype: User's chronotype
            task_type: Type of task being performed
        """
        self.user_id = user_id
        self.chronotype = chronotype
        self.task_type = task_type
        self.current_session: Optional[SessionMetadata] = None
    
    def start_session(self) -> SessionMetadata:
        """Start a new study session"""
        if self.current_session and not self.current_session.end_time:
            # End previous session if still active
            self.end_session()
        
        session_id = str(uuid.uuid4())
        self.current_session = SessionMetadata(
            session_id=session_id,
            user_id=self.user_id,
            start_time=datetime.utcnow(),
            chronotype=self.chronotype,
            task_type=self.task_type
        )
        return self.current_session
    
    def end_session(self) -> Optional[SessionMetadata]:
        """End the current session"""
        if self.current_session and not self.current_session.end_time:
            self.current_session.end_time = datetime.utcnow()
            session = self.current_session
            self.current_session = None
            return session
        return None
    
    def get_current_session(self) -> Optional[SessionMetadata]:
        """Get current active session"""
        return self.current_session
    
    def update_task_type(self, task_type: TaskType):
        """Update task type for current session"""
        if self.current_session:
            self.current_session.task_type = task_type

