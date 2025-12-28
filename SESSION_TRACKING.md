# Session Tracking System Documentation

## Overview

The session tracking system provides comprehensive cognitive load session management with detailed analytics, separate from the main cognitive load estimation system. It tracks session timing, cognitive load patterns, success metrics, and user ratings.

## Features

### **Session Management**
- Start/end sessions with cognitive load tracking
- Automatic session length calculation
- Session metadata (notes, tags, project info)
- Session status monitoring

### **Cognitive Load Tracking**
- Real-time cognitive load logging
- Load statistics (average, peak, variance)
- Load progression over time
- Load-based milestone tracking

### **Success Metrics**
- Success score (0-1 scale)
- Productivity rating (1-5 scale)
- Difficulty rating (1-5 scale)  
- Satisfaction rating (1-5 scale)
- Custom rating scales

### **Milestone Tracking**
- Session milestones (breaks, tasks, interruptions)
- Cognitive load at milestone points
- Milestone descriptions and context
- Custom milestone types

### **Data Storage**
- Separate SQLite database (`data/sessions.db`)
- No conflicts with existing system
- Configurable data retention
- Export capabilities

## Database Schema

### **session_summaries Table**
```sql
CREATE TABLE session_summaries (
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
```

### **session_events Table**
```sql
CREATE TABLE session_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    cognitive_load REAL,
    metadata_json TEXT,
    FOREIGN KEY (session_id) REFERENCES session_summaries(session_id)
);
```

### **session_milestones Table**
```sql
CREATE TABLE session_milestones (
    milestone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    milestone_type TEXT NOT NULL,
    description TEXT,
    cognitive_load REAL,
    FOREIGN KEY (session_id) REFERENCES session_summaries(session_id)
);
```

## API Endpoints

### **Session Management**
- `POST /sessions/start` - Start a new session
- `POST /sessions/end` - End current session
- `GET /sessions/current` - Get current session info
- `GET /sessions/status` - Get session status
- `GET /sessions/{uuid}` - Get session summary
- `GET /sessions` - List sessions
- `PUT /sessions/{uuid}` - Update session notes/tags
- `DELETE /sessions/{uuid}` - Delete session

### **Session Activity**
- `POST /sessions/log-cognitive-load` - Log cognitive load update
- `POST /sessions/milestones` - Add milestone

## Configuration

### **Session Tracking Config** (`config/policy_with_sessions.toml`)
```toml
[session_tracking]
storage_path = "data/sessions.db"
auto_start_sessions = true
auto_end_sessions_after_inactivity = true
inactivity_threshold_seconds = 300
default_tags = ["work", "cognitive-load"]
log_cognitive_load_updates = true
cognitive_load_update_interval = 30
enable_retention_pruning = true
retention_days = 90

[session_config]
project_name = null
task_type = null
work_context = null
productivity_scale = ["Very Low", "Low", "Medium", "High", "Very High"]
difficulty_scale = ["Very Easy", "Easy", "Medium", "Hard", "Very Hard"]
satisfaction_scale = ["Very Dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very Satisfied"]
```

## Usage Examples

### **Starting a Session**
```bash
# Using API
curl -X POST http://localhost:8000/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "cognitive_load": 2.5,
    "notes": "Working on project documentation",
    "tags": ["documentation", "writing"]
  }'

# Using CLI
session-cli start --load 2.5 --notes "Working on project documentation" --tags documentation writing
```

### **Ending a Session**
```bash
# Using API
curl -X POST http://localhost:8000/sessions/end \
  -H "Content-Type: application/json" \
  -d '{
    "cognitive_load": 3.8,
    "success_score": 0.8,
    "productivity_rating": 4,
    "difficulty_rating": 3,
    "satisfaction_rating": 4,
    "notes": "Completed documentation section"
  }'

# Using CLI
session-cli end --load 3.8 --success 0.8 --productivity 4 --difficulty 3 --satisfaction 4 --notes "Completed documentation section"
```

### **Logging Cognitive Load**
```bash
# Using API
curl -X POST http://localhost:8000/sessions/log-cognitive-load \
  -H "Content-Type: application/json" \
  -d '{
    "cognitive_load": 3.2,
    "event_type": "task_progress",
    "metadata": {"task": "writing", "progress": 50}
  }'
```

### **Adding Milestones**
```bash
# Using API
curl -X POST http://localhost:8000/sessions/milestones \
  -H "Content-Type: application/json" \
  -d '{
    "milestone_type": "break_start",
    "description": "Coffee break",
    "cognitive_load": 2.1
  }'
```

### **Listing Sessions**
```bash
# Using API
curl "http://localhost:8000/sessions?limit=10&start_date=2023-12-01&end_date=2023-12-31"

# Using CLI
session-cli list --limit 10 --start-date 2023-12-01 --end-date 2023-12-31
```

### **Session Details**
```bash
# Using API
curl http://localhost:8000/sessions/{session-uuid}

# Using CLI
session-cli show {session-uuid}
```

## Integration with Main System

### **Configuration Integration**
The session tracking is integrated into the main configuration system:

```python
from cog_py_est.config import AppConfig

config = AppConfig.load("config/policy_with_sessions.toml")
# Access session settings
session_config = config.session_tracking
session_metadata = config.session_config
```

### **Service Integration**
Session tracking is initialized alongside the main service:

```python
# In app.py
session_manager = create_session_manager(config_path)
await session_manager.initialize()
```

### **No Conflicts Design**
- Separate database file (`data/sessions.db` vs `data/state.db`)
- Independent storage layer
- Separate API endpoints (`/sessions/*`)
- Isolated configuration sections
- No impact on existing cognitive load estimation

## CLI Tool Usage

### **Installation**
```bash
# After installing the package
session-cli --help
```

### **Commands**
```bash
# Start session
session-cli start --load 2.5 --notes "Morning coding session"

# End session
session-cli end --load 3.2 --success 0.7 --productivity 4

# List sessions
session-cli list --limit 5

# Show session details
session-cli show {session-uuid}

# Current session
session-cli current

# Delete session
session-cli delete {session-uuid} --confirm
```

## Data Analysis

### **Session Analytics**
The system automatically calculates:
- Session duration
- Cognitive load statistics (mean, peak, variance)
- Load progression patterns
- Success correlations

### **Export Capabilities**
Sessions can be exported for analysis:
- JSON format
- Date range filtering
- Complete session history
- Event and milestone data

## Privacy and Security

### **Local-Only Storage**
- All data stored locally in SQLite
- No network transmission of session data
- User-controlled data retention

### **Data Minimization**
- Only essential session data collected
- Configurable retention periods
- Secure deletion capabilities

### **User Control**
- Manual session start/end control
- Optional rating collection
- Data deletion on demand

## Best Practices

### **Session Management**
1. Start sessions when beginning focused work
2. End sessions when work is complete
3. Add meaningful notes and tags
4. Rate sessions honestly for better analytics

### **Cognitive Load Logging**
1. Log load at significant events
2. Use consistent event types
3. Include relevant metadata
4. Track load changes over time

### **Milestone Tracking**
1. Log breaks and interruptions
2. Mark task completions
3. Note focus changes
4. Track high/low load periods

### **Data Management**
1. Regular session reviews
2. Export data for long-term analysis
3. Clean up old sessions
4. Backup important sessions

## Troubleshooting

### **Common Issues**
1. **Database locked**: Ensure only one session manager instance
2. **Missing sessions**: Check correct database path
3. **Invalid UUID**: Verify session exists before operations
4. **Configuration errors**: Validate TOML syntax

### **Debug Commands**
```bash
# Check session status
curl http://localhost:8000/sessions/status

# List recent sessions
session-cli list --limit 3

# Verify database
sqlite3 data/sessions.db ".tables"
```

This session tracking system provides comprehensive cognitive load session management while maintaining complete separation from the existing cognitive load estimation system.
