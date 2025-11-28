"""Main context logger that coordinates keystroke listening and session tracking"""
from typing import List, Optional, Callable
from src.context_logger.keystroke_listener import KeystrokeListener, KeystrokeEvent
from src.context_logger.session_tracker import SessionTracker, SessionMetadata
from src.database.models import Session, KeystrokeEvent as DBKeystrokeEvent, SessionLocal
from datetime import datetime


class ContextLogger:
    """Main context logger that coordinates all logging components"""
    
    def __init__(self, user_id: str, chronotype: str = "neutral", task_type: str = "other"):
        """
        Initialize context logger
        
        Args:
            user_id: User identifier
            chronotype: User chronotype ('morning', 'evening', 'neutral')
            task_type: Task type ('writing', 'coding', 'reading', 'other')
        """
        from src.context_logger.session_tracker import Chronotype, TaskType
        
        self.session_tracker = SessionTracker(
            user_id=user_id,
            chronotype=Chronotype(chronotype),
            task_type=TaskType(task_type)
        )
        self.keystroke_listener: Optional[KeystrokeListener] = None
        self.keystroke_buffer: List[KeystrokeEvent] = []
        self.db_session = SessionLocal()
    
    def start_session(self) -> SessionMetadata:
        """Start a new study session and begin keystroke logging"""
        session_metadata = self.session_tracker.start_session()
        
        # Initialize keystroke listener
        self.keystroke_listener = KeystrokeListener(
            session_id=session_metadata.session_id,
            callback=self._handle_keystroke_event
        )
        self.keystroke_listener.start()
        
        # Save session to database
        db_session = Session(
            session_id=session_metadata.session_id,
            user_id=session_metadata.user_id,
            start_time=session_metadata.start_time,
            chronotype=session_metadata.chronotype.value,
            task_type=session_metadata.task_type.value
        )
        self.db_session.add(db_session)
        self.db_session.commit()
        
        return session_metadata
    
    def end_session(self) -> Optional[SessionMetadata]:
        """End current session and stop keystroke logging"""
        # Stop keystroke listener
        if self.keystroke_listener:
            self.keystroke_listener.stop()
            self.keystroke_listener = None
        
        # Flush keystroke buffer to database
        self._flush_keystroke_buffer()
        
        # End session
        session_metadata = self.session_tracker.end_session()
        
        if session_metadata:
            # Update session in database
            db_session = self.db_session.query(Session).filter_by(
                session_id=session_metadata.session_id
            ).first()
            if db_session:
                db_session.end_time = session_metadata.end_time
                self.db_session.commit()
        
        return session_metadata
    
    def _handle_keystroke_event(self, event: KeystrokeEvent):
        """Handle keystroke event (callback from listener)"""
        self.keystroke_buffer.append(event)
        
        # Flush buffer periodically (every 100 events or every 10 seconds)
        if len(self.keystroke_buffer) >= 100:
            self._flush_keystroke_buffer()
    
    def _flush_keystroke_buffer(self):
        """Flush keystroke buffer to database"""
        if not self.keystroke_buffer:
            return
        
        current_session = self.session_tracker.get_current_session()
        if not current_session:
            return
        
        db_events = []
        for event in self.keystroke_buffer:
            db_event = DBKeystrokeEvent(
                session_id=event.session_id,
                timestamp=event.timestamp,
                key_code=event.key_code,
                event_type=event.event_type.value
            )
            db_events.append(db_event)
        
        self.db_session.bulk_save_objects(db_events)
        self.db_session.commit()
        self.keystroke_buffer.clear()
    
    def get_current_session(self) -> Optional[SessionMetadata]:
        """Get current active session"""
        return self.session_tracker.get_current_session()
    
    def __enter__(self):
        """Context manager entry"""
        self.start_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.end_session()
        self.db_session.close()

