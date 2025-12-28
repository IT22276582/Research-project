"""Session tracking API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .session_config import SessionConfig, SessionTrackingConfig
from .session_manager import SessionManager


class SessionStartRequest(BaseModel):
    """Request to start a new session."""
    cognitive_load: float = Field(ge=0.0, le=10.0)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    project_name: Optional[str] = None
    task_type: Optional[str] = None
    work_context: Optional[str] = None


class SessionEndRequest(BaseModel):
    """Request to end a session."""
    cognitive_load: float = Field(ge=0.0, le=10.0)
    success_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    productivity_rating: Optional[int] = Field(default=None, ge=1, le=5)
    difficulty_rating: Optional[int] = Field(default=None, ge=1, le=5)
    satisfaction_rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    """Request to update session notes/tags."""
    notes: str
    tags: Optional[List[str]] = None


class CognitiveLogRequest(BaseModel):
    """Request to log cognitive load update."""
    cognitive_load: float = Field(ge=0.0, le=10.0)
    event_type: str = "cognitive_load_update"
    metadata: Optional[Dict[str, Any]] = None


class MilestoneRequest(BaseModel):
    """Request to add a milestone."""
    milestone_type: str
    description: Optional[str] = None
    cognitive_load: Optional[float] = Field(default=None, ge=0.0, le=10.0)


class SessionAPI:
    """API endpoints for session tracking."""
    
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    async def start_session(self, request: SessionStartRequest) -> Dict[str, Any]:
        """Start a new session."""
        session_uuid = await self.session_manager.start_session(
            cognitive_load=request.cognitive_load,
            notes=request.notes,
            tags=request.tags
        )
        
        return {
            "session_uuid": session_uuid,
            "status": "started",
            "message": "Session started successfully"
        }

    async def end_session(self, request: SessionEndRequest) -> Dict[str, Any]:
        """End the current session."""
        session_uuid = await self.session_manager.end_session(
            cognitive_load=request.cognitive_load,
            success_score=request.success_score,
            productivity_rating=request.productivity_rating,
            difficulty_rating=request.difficulty_rating,
            satisfaction_rating=request.satisfaction_rating,
            notes=request.notes
        )
        
        if session_uuid is None:
            raise HTTPException(status_code=404, detail="No active session found")
        
        return {
            "session_uuid": session_uuid,
            "status": "ended",
            "message": "Session ended successfully"
        }

    async def get_current_session(self) -> Dict[str, Any]:
        """Get information about the current session."""
        session_info = await self.session_manager.get_current_session_info()
        
        if session_info is None:
            raise HTTPException(status_code=404, detail="No active session found")
        
        return {
            "session": session_info,
            "is_active": True
        }

    async def get_session_summary(self, session_uuid: str) -> Dict[str, Any]:
        """Get a complete session summary."""
        summary = await self.session_manager.get_session_summary(session_uuid)
        
        if summary is None:
            raise HTTPException(status_code=404, detail=f"Session {session_uuid} not found")
        
        return summary

    async def list_sessions(
        self,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """List sessions with optional date filtering."""
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        sessions = await self.session_manager.list_sessions(
            limit=limit,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }

    async def update_session(
        self,
        session_uuid: str,
        request: SessionUpdateRequest
    ) -> Dict[str, Any]:
        """Update session notes and/or tags."""
        try:
            await self.session_manager.update_session_notes(
                session_uuid=session_uuid,
                notes=request.notes,
                tags=request.tags
            )
            
            return {
                "session_uuid": session_uuid,
                "status": "updated",
                "message": "Session updated successfully"
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def delete_session(self, session_uuid: str) -> Dict[str, Any]:
        """Delete a session and all related data."""
        try:
            await self.session_manager.delete_session(session_uuid)
            
            return {
                "session_uuid": session_uuid,
                "status": "deleted",
                "message": "Session deleted successfully"
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def log_cognitive_load(self, request: CognitiveLogRequest) -> Dict[str, Any]:
        """Log a cognitive load update for the current session."""
        if not self.session_manager.is_session_active:
            raise HTTPException(status_code=404, detail="No active session found")
        
        await self.session_manager.log_cognitive_load(
            cognitive_load=request.cognitive_load,
            event_type=request.event_type,
            metadata=request.metadata
        )
        
        return {
            "status": "logged",
            "message": "Cognitive load logged successfully"
        }

    async def add_milestone(self, request: MilestoneRequest) -> Dict[str, Any]:
        """Add a milestone to the current session."""
        if not self.session_manager.is_session_active:
            raise HTTPException(status_code=404, detail="No active session found")
        
        await self.session_manager.add_milestone(
            milestone_type=request.milestone_type,
            description=request.description,
            cognitive_load=request.cognitive_load
        )
        
        return {
            "status": "added",
            "message": "Milestone added successfully"
        }

    async def get_session_status(self) -> Dict[str, Any]:
        """Get the current session status."""
        return {
            "is_active": self.session_manager.is_session_active,
            "current_session_uuid": self.session_manager.current_session_uuid
        }
