"""Configuration for session tracking system."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class SessionTrackingConfig(BaseModel):
    """Configuration for session tracking."""
    
    # Database settings
    storage_path: Path = Field(default=Path("data/sessions.db"))
    
    # Auto session settings
    auto_start_sessions: bool = True
    auto_end_sessions_after_inactivity: bool = True
    inactivity_threshold_seconds: int = 300  # 5 minutes
    
    # Session defaults
    default_tags: List[str] = Field(default_factory=list)
    require_success_rating: bool = False
    require_productivity_rating: bool = False
    require_difficulty_rating: bool = False
    require_satisfaction_rating: bool = False
    
    # Milestone settings
    auto_log_milestones: bool = True
    milestone_types: List[str] = Field(
        default_factory=lambda: [
            "break_start", "break_end", "task_complete", 
            "interruption", "focus_change", "ema_prompt"
        ]
    )
    
    # Cognitive load tracking
    log_cognitive_load_updates: bool = True
    cognitive_load_update_interval: int = 30  # seconds
    
    # Data retention
    enable_retention_pruning: bool = True
    retention_days: int = 90
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class SessionConfig(BaseModel):
    """Session-specific configuration."""
    
    # Session metadata
    project_name: Optional[str] = None
    task_type: Optional[str] = None
    work_context: Optional[str] = None
    
    # Rating scales
    productivity_scale: List[str] = Field(
        default_factory=lambda: [
            "Very Low", "Low", "Medium", "High", "Very High"
        ]
    )
    difficulty_scale: List[str] = Field(
        default_factory=lambda: [
            "Very Easy", "Easy", "Medium", "Hard", "Very Hard"
        ]
    )
    satisfaction_scale: List[str] = Field(
        default_factory=lambda: [
            "Very Dissatisfied", "Dissatisfied", "Neutral", 
            "Satisfied", "Very Satisfied"
        ]
    )
