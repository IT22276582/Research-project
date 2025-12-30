"""Session tracking storage for cognitive load sessions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite


def _dt(dt_val: datetime) -> str:
    return dt_val.isoformat()


def _parse_dt(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


class SessionStorage:
    """Separate storage for session tracking data."""
    
    def __init__(self, path: Path) -> None:
        self.path = path
        self.db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize the session database."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.path.as_posix())
        await self.db.execute("PRAGMA journal_mode=WAL;")
        await self._create_tables()
        await self.db.commit()

    async def _create_tables(self) -> None:
        """Create session tracking tables."""
        db = self._require_db()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_uuid TEXT UNIQUE NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                session_length_seconds REAL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                cognitive_load_at_start REAL,
                cognitive_load_at_end REAL,
                average_cognitive_load REAL,
                peak_cognitive_load REAL,
                cognitive_load_variance REAL,
                success_score REAL,
                productivity_rating INTEGER,
                difficulty_rating INTEGER,
                satisfaction_rating INTEGER,
                notes TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                cognitive_load REAL,
                metadata_json TEXT,
                FOREIGN KEY (session_id) REFERENCES session_summaries(session_id)
            );

            CREATE TABLE IF NOT EXISTS session_milestones (
                milestone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                description TEXT,
                cognitive_load REAL,
                FOREIGN KEY (session_id) REFERENCES session_summaries(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_session_summaries_start_time 
                ON session_summaries(start_time);
            CREATE INDEX IF NOT EXISTS idx_session_summaries_session_uuid 
                ON session_summaries(session_uuid);
            CREATE INDEX IF NOT EXISTS idx_session_events_session_id 
                ON session_events(session_id);
            CREATE INDEX IF NOT EXISTS idx_session_events_timestamp 
                ON session_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_session_milestones_session_id 
                ON session_milestones(session_id);
            """
        )

    def _require_db(self) -> aiosqlite.Connection:
        if self.db is None:
            raise RuntimeError("SessionStorage not initialized")
        return self.db

    async def create_session(
        self,
        session_uuid: str,
        start_time: datetime,
        cognitive_load_at_start: float,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Create a new session record."""
        db = self._require_db()
        now = datetime.now(timezone.utc)
        
        cursor = await db.execute(
            """
            INSERT INTO session_summaries 
            (session_uuid, start_time, start_date, cognitive_load_at_start, 
             notes, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_uuid,
                _dt(start_time),
                start_time.date().isoformat(),
                cognitive_load_at_start,
                notes,
                json.dumps(tags or []),
                _dt(now),
                _dt(now)
            )
        )
        await db.commit()
        rowid = cursor.lastrowid
        if rowid is None:
            raise RuntimeError("Failed to insert session record")
        return rowid

    async def end_session(
        self,
        session_id: int,
        end_time: datetime,
        cognitive_load_at_end: float,
        success_score: Optional[float] = None,
        productivity_rating: Optional[int] = None,
        difficulty_rating: Optional[int] = None,
        satisfaction_rating: Optional[int] = None,
        notes: Optional[str] = None
    ) -> None:
        """End a session and calculate derived metrics."""
        db = self._require_db()
        
        # Get session start time and load data
        cursor = await db.execute(
            "SELECT start_time, cognitive_load_at_start FROM session_summaries WHERE session_id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        start_time_str, start_load = row
        start_time = _parse_dt(start_time_str)
        
        # Calculate session length
        session_length = (end_time - start_time).total_seconds()
        
        # Get all cognitive load events for this session
        cursor = await db.execute(
            "SELECT cognitive_load FROM session_events WHERE session_id = ? AND cognitive_load IS NOT NULL",
            (session_id,)
        )
        load_rows = await cursor.fetchall()
        
        if load_rows:
            loads = [row[0] for row in load_rows]
            average_load = sum(loads) / len(loads)
            peak_load = max(loads)
            variance_load = sum((x - average_load) ** 2 for x in loads) / len(loads)
        else:
            # Use start and end loads if no events
            loads = [start_load, cognitive_load_at_end]
            average_load = sum(loads) / len(loads)
            peak_load = max(loads)
            variance_load = sum((x - average_load) ** 2 for x in loads) / len(loads)
        
        await db.execute(
            """
            UPDATE session_summaries 
            SET end_time = ?, end_date = ?, session_length_seconds = ?,
                cognitive_load_at_end = ?, average_cognitive_load = ?,
                peak_cognitive_load = ?, cognitive_load_variance = ?,
                success_score = ?, productivity_rating = ?, difficulty_rating = ?,
                satisfaction_rating = ?, notes = COALESCE(?, notes), updated_at = ?
            WHERE session_id = ?
            """,
            (
                _dt(end_time),
                end_time.date().isoformat(),
                session_length,
                cognitive_load_at_end,
                average_load,
                peak_load,
                variance_load,
                success_score,
                productivity_rating,
                difficulty_rating,
                satisfaction_rating,
                notes,
                _dt(datetime.now(timezone.utc)),
                session_id
            )
        )
        await db.commit()

    async def add_session_event(
        self,
        session_id: int,
        timestamp: datetime,
        event_type: str,
        cognitive_load: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a session."""
        db = self._require_db()
        await db.execute(
            """
            INSERT INTO session_events 
            (session_id, timestamp, event_type, cognitive_load, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                _dt(timestamp),
                event_type,
                cognitive_load,
                json.dumps(metadata) if metadata else None
            )
        )
        await db.commit()

    async def add_milestone(
        self,
        session_id: int,
        timestamp: datetime,
        milestone_type: str,
        description: Optional[str] = None,
        cognitive_load: Optional[float] = None
    ) -> None:
        """Add a milestone to a session."""
        db = self._require_db()
        await db.execute(
            """
            INSERT INTO session_milestones 
            (session_id, timestamp, milestone_type, description, cognitive_load)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                _dt(timestamp),
                milestone_type,
                description,
                cognitive_load
            )
        )
        await db.commit()

    async def get_session_by_uuid(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """Get session details by UUID."""
        db = self._require_db()
        cursor = await db.execute(
            "SELECT * FROM session_summaries WHERE session_uuid = ?",
            (session_uuid,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        session_dict = dict(zip(columns, row))
        
        # Parse JSON fields
        if session_dict['tags']:
            session_dict['tags'] = json.loads(session_dict['tags'])
        else:
            session_dict['tags'] = []
        
        return session_dict

    async def get_session_events(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all events for a session."""
        db = self._require_db()
        cursor = await db.execute(
            "SELECT * FROM session_events WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        events = []
        for row in rows:
            event_dict = dict(zip(columns, row))
            if event_dict['metadata_json']:
                event_dict['metadata'] = json.loads(event_dict['metadata_json'])
            else:
                event_dict['metadata'] = {}
            events.append(event_dict)
        
        return events

    async def get_session_milestones(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all milestones for a session."""
        db = self._require_db()
        cursor = await db.execute(
            "SELECT * FROM session_milestones WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        return [dict(zip(columns, row)) for row in rows]

    async def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """List sessions with optional date filtering."""
        db = self._require_db()
        
        query = "SELECT * FROM session_summaries"
        params = []
        
        if start_date or end_date:
            query += " WHERE"
            conditions = []
            
            if start_date:
                conditions.append(" start_time >= ?")
                params.append(_dt(start_date))
            
            if end_date:
                conditions.append(" end_time <= ?")
                params.append(_dt(end_date))
            
            query += " AND".join(conditions)
        
        query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        sessions = []
        for row in rows:
            session_dict = dict(zip(columns, row))
            if session_dict['tags']:
                session_dict['tags'] = json.loads(session_dict['tags'])
            else:
                session_dict['tags'] = []
            sessions.append(session_dict)
        
        return sessions

    async def update_session_notes(
        self,
        session_id: int,
        notes: str,
        tags: Optional[List[str]] = None
    ) -> None:
        """Update session notes and/or tags."""
        db = self._require_db()
        update_fields = ["notes = ?", "updated_at = ?"]
        params = [notes, _dt(datetime.utcnow())]
        
        if tags is not None:
            update_fields.append("tags = ?")
            params.append(json.dumps(tags))
        
        params.append(str(session_id))
        
        await db.execute(
            f"UPDATE session_summaries SET {', '.join(update_fields)} WHERE session_id = ?",
            params
        )
        await db.commit()

    async def delete_session(self, session_id: int) -> None:
        """Delete a session and all related data."""
        db = self._require_db()
        await db.execute("DELETE FROM session_events WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM session_milestones WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
        await db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self.db:
            await self.db.close()
            self.db = None
