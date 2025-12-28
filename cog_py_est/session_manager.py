"""Session tracking manager for cognitive load sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .session_storage import SessionStorage


class SessionManager:
    """Manages cognitive load sessions with tracking and analytics."""
    
    def __init__(self, storage_path: Path) -> None:
        self.storage = SessionStorage(storage_path)
        self._current_session_id: Optional[int] = None
        self._current_session_uuid: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the session manager."""
        await self.storage.initialize()

    async def start_session(
        self,
        cognitive_load: float,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Start a new session and return its UUID."""
        session_uuid = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        session_id = await self.storage.create_session(
            session_uuid=session_uuid,
            start_time=start_time,
            cognitive_load_at_start=cognitive_load,
            notes=notes,
            tags=tags
        )
        
        self._current_session_id = session_id
        self._current_session_uuid = session_uuid
        
        # Add session start event
        await self.storage.add_session_event(
            session_id=session_id,
            timestamp=start_time,
            event_type="session_start",
            cognitive_load=cognitive_load,
            metadata={"notes": notes, "tags": tags}
        )
        
        return session_uuid

    async def end_session(
        self,
        cognitive_load: float,
        success_score: Optional[float] = None,
        productivity_rating: Optional[int] = None,
        difficulty_rating: Optional[int] = None,
        satisfaction_rating: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[str]:
        """End the current session and return its UUID."""
        if self._current_session_id is None:
            return None
        
        end_time = datetime.now(timezone.utc)
        
        await self.storage.end_session(
            session_id=self._current_session_id,
            end_time=end_time,
            cognitive_load_at_end=cognitive_load,
            success_score=success_score,
            productivity_rating=productivity_rating,
            difficulty_rating=difficulty_rating,
            satisfaction_rating=satisfaction_rating,
            notes=notes
        )
        
        # Add session end event
        await self.storage.add_session_event(
            session_id=self._current_session_id,
            timestamp=end_time,
            event_type="session_end",
            cognitive_load=cognitive_load,
            metadata={
                "success_score": success_score,
                "productivity_rating": productivity_rating,
                "difficulty_rating": difficulty_rating,
                "satisfaction_rating": satisfaction_rating,
                "notes": notes
            }
        )
        
        session_uuid = self._current_session_uuid
        self._current_session_id = None
        self._current_session_uuid = None
        
        return session_uuid

    async def log_cognitive_load(
        self,
        cognitive_load: float,
        event_type: str = "cognitive_load_update",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a cognitive load update for the current session."""
        if self._current_session_id is None:
            return
        
        await self.storage.add_session_event(
            session_id=self._current_session_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            cognitive_load=cognitive_load,
            metadata=metadata
        )

    async def add_milestone(
        self,
        milestone_type: str,
        description: Optional[str] = None,
        cognitive_load: Optional[float] = None
    ) -> None:
        """Add a milestone to the current session."""
        if self._current_session_id is None:
            return
        
        await self.storage.add_milestone(
            session_id=self._current_session_id,
            timestamp=datetime.now(timezone.utc),
            milestone_type=milestone_type,
            description=description,
            cognitive_load=cognitive_load
        )

    async def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current session."""
        if self._current_session_uuid is None:
            return None
        
        return await self.storage.get_session_by_uuid(self._current_session_uuid)

    async def get_session_summary(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """Get a complete session summary including events and milestones."""
        session = await self.storage.get_session_by_uuid(session_uuid)
        if not session:
            return None
        
        events = await self.storage.get_session_events(session['session_id'])
        milestones = await self.storage.get_session_milestones(session['session_id'])
        
        return {
            "session": session,
            "events": events,
            "milestones": milestones
        }

    async def list_sessions(
        self,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """List sessions with optional date filtering."""
        return await self.storage.list_sessions(
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

    async def update_session_notes(
        self,
        session_uuid: str,
        notes: str,
        tags: Optional[List[str]] = None
    ) -> None:
        """Update session notes and/or tags."""
        session = await self.storage.get_session_by_uuid(session_uuid)
        if not session:
            raise ValueError(f"Session {session_uuid} not found")
        
        await self.storage.update_session_notes(
            session_id=session['session_id'],
            notes=notes,
            tags=tags
        )

    async def delete_session(self, session_uuid: str) -> None:
        """Delete a session and all related data."""
        session = await self.storage.get_session_by_uuid(session_uuid)
        if not session:
            raise ValueError(f"Session {session_uuid} not found")
        
        await self.storage.delete_session(session['session_id'])

    @property
    def is_session_active(self) -> bool:
        """Check if a session is currently active."""
        return self._current_session_id is not None

    @property
    def current_session_uuid(self) -> Optional[str]:
        """Get the current session UUID."""
        return self._current_session_uuid

    async def close(self) -> None:
        """Close the session manager."""
        await self.storage.close()
