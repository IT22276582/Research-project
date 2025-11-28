# Adaptive Scheduler - Complete User Guide

A comprehensive guide on how to install, run, and use the Adaptive Scheduler system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Running the System](#running-the-system)
4. [Using the API](#using-the-api)
5. [Testing](#testing)
6. [Generating Test Data](#generating-test-data)
7. [Computing Metrics](#computing-metrics)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python init_database.py

# 3. Start the server
python run_server.py

# 4. In another terminal, test it
python example_usage.py
```

The API will be running at `http://127.0.0.1:5000`

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- SQLAlchemy (database ORM)
- NumPy, Pandas (data processing)
- scikit-learn, PyTorch (machine learning)
- pynput (keystroke logging)

### Step 2: Initialize Database

```bash
python init_database.py
```

This creates the SQLite database (`adaptive_scheduler.db`) with all required tables.

### Step 3: (Optional) Generate Test Data

For testing and evaluation:

```bash
python generate_test_data.py
```

This creates synthetic user sessions for testing metrics and algorithms.

---

## Running the System

### Start the API Server

```bash
python run_server.py
```

The server will start on `http://127.0.0.1:5000` by default.

**Output:**
```
Initializing database...
Database initialized!
Starting API server on 127.0.0.1:5000...
 * Running on http://127.0.0.1:5000
```

### Check Server Status

```bash
curl http://127.0.0.1:5000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 0
}
```

### Stop the Server

Press `Ctrl+C` in the terminal running the server.

---

## Using the API

### 1. Start a Study Session

**Endpoint:** `POST /api/start-session`

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/start-session \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "task_type": "writing",
    "chronotype": "morning",
    "algorithm": "LinUCB"
  }'
```

**Response:**
```json
{
  "session_id": "abc-123-def-456",
  "initial_action": {
    "work_interval": 30,
    "break_duration": 5
  },
  "metadata": {
    "algorithm": "LinUCB",
    "confidence": 0.75,
    "cognitive_load": 0.5
  }
}
```

**Parameters:**
- `user_id` (required): Unique user identifier
- `task_type` (optional): "writing", "coding", "reading", "other" (default: "other")
- `chronotype` (optional): "morning", "evening", "neutral" (default: "neutral")
- `algorithm` (optional): "LinUCB" or "ThompsonSampling" (default: "LinUCB")

### 2. Get Recommendation

**Endpoint:** `GET /api/get-recommendation?session_id=<session_id>`

**Request:**
```bash
curl "http://127.0.0.1:5000/api/get-recommendation?session_id=abc-123-def-456"
```

**Response:**
```json
{
  "work_interval": 30,
  "break_duration": 5,
  "explanation": "Recommended by LinUCB based on cognitive load: 0.65",
  "confidence": 0.78,
  "was_overridden": false
}
```

### 3. End Work/Break Interval

**Endpoint:** `POST /api/end-interval`

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/end-interval \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def-456",
    "interval_type": "work",
    "metrics": {
      "chars_typed": 500,
      "cognitive_load_pre_break": 0.7,
      "cognitive_load_post_break": 0.4,
      "improved_focus": true,
      "deep_work_interrupted": false
    }
  }'
```

**Response:**
```json
{
  "next_action": {
    "work_interval": 25,
    "break_duration": 8
  },
  "reward_computed": {
    "immediate_reward": 0.75,
    "r_progress": 0.65,
    "r_relief": 0.30
  },
  "metadata": {
    "algorithm": "LinUCB",
    "was_overridden": false
  }
}
```

**Parameters:**
- `session_id` (required): Session identifier
- `interval_type` (required): "work" or "break"
- `metrics` (optional): Dictionary with:
  - `chars_typed`: Number of characters typed
  - `cognitive_load_pre_break`: Load before break (0-1)
  - `cognitive_load_post_break`: Load after break (0-1)
  - `improved_focus`: Boolean
  - `deep_work_interrupted`: Boolean

### 4. Submit Feedback (Micro-EMA)

**Endpoint:** `POST /api/submit-feedback`

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/submit-feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def-456",
    "fatigue_level": 2,
    "focus_level": 4,
    "satisfaction": 4
  }'
```

**Response:**
```json
{
  "acknowledged": true,
  "policy_updated": true
}
```

**Parameters:**
- `session_id` (required): Session identifier
- `fatigue_level` (required): 1-5 scale
- `focus_level` (required): 1-5 scale
- `satisfaction` (optional): 1-5 scale

### 5. Get Metrics

**Endpoint:** `GET /api/metrics?user_id=<user_id>`

**Request:**
```bash
curl "http://127.0.0.1:5000/api/metrics?user_id=user123"
```

**With time range:**
```bash
curl "http://127.0.0.1:5000/api/metrics?user_id=user123&start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59"
```

**Response:**
```json
{
  "user_id": "user123",
  "metrics": {
    "PG": 0.18,
    "RPH": 0.08,
    "AHL": 4.5,
    "EOI": 0.12,
    "AUC_BUC": 2.3,
    "CTU": 0.15,
    "SPF_variance": 0.10,
    "SVR": 0.03
  },
  "interpretation": {
    "PG": "Excellent personalization (18.0% improvement over baseline)",
    "RPH": "Excellent efficiency (RPH: 0.080)",
    "AHL": "Fast adaptation (4.5 sessions)",
    "EOI": "Moderate exploration cost (12.0%)",
    "SVR": "Low safety override rate (3.0%)"
  }
}
```

### 6. End Session

**Endpoint:** `POST /api/end-session`

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/end-session \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def-456"
  }'
```

**Response:**
```json
{
  "session_ended": true,
  "duration_minutes": 45.5
}
```

---

## Testing

### Run Example Script

```bash
python example_usage.py
```

This demonstrates a complete session flow:
1. Starting a session
2. Getting recommendations
3. Ending intervals
4. Submitting feedback
5. Computing metrics

### Run Unit Tests

```bash
pytest tests/
```

**Test files:**
- `tests/test_bandit.py` - Bandit algorithm tests
- `tests/test_reward.py` - Reward computation tests
- `tests/test_feature_extractor.py` - Feature extraction tests

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Generating Test Data

### Interactive Generation

```bash
python generate_test_data.py
```

You'll be prompted for:
- Number of users (default: 5)
- Sessions per user (default: 3)

### Programmatic Generation

```python
from src.data_generation.synthetic_data import generate_test_data

# Generate data for 10 users, 5 sessions each
user_ids = generate_test_data(num_users=10, sessions_per_user=5)
```

**What it generates:**
- Synthetic user profiles
- Keystroke events
- Context vectors
- Actions and rewards
- Micro-EMA feedback

**Use cases:**
- Testing algorithms
- Validating metrics
- Simulation studies
- Development and debugging

---

## Computing Metrics

### Via API

```bash
curl "http://127.0.0.1:5000/api/metrics?user_id=user123"
```

### Programmatically

```python
from src.metrics.metrics_calculator import MetricsCalculator

# Initialize calculator
calculator = MetricsCalculator(user_id="user123")

# Compute all metrics
metrics = calculator.compute_all_metrics()

# Access individual metrics
print(f"Personalization Gain: {metrics.PG:.3f}")
print(f"Regret-per-Hour: {metrics.RPH:.3f}")
print(f"Adaptation Half-Life: {metrics.AHL:.1f} sessions")
```

### Available Metrics

1. **PG (Personalization Gain)**: Improvement over Pomodoro baseline
2. **RPH (Regret-per-Hour)**: Normalized regret by study time
3. **AHL (Adaptation Half-Life)**: Recovery time after context shifts
4. **EOI (Exploration Overhead Index)**: Cost of exploration
5. **AUC-BUC**: Area under break utility curve
6. **CTU (Counterfactual Targeting Uplift)**: Causal effect estimation
7. **SPF Variance**: Stability-productivity trade-off
8. **SVR (Safety-Violation Rate)**: Safety override frequency

---

## Configuration

Edit `config/config.py` to customize:

### Work/Break Intervals
```python
WORK_INTERVALS = [20, 30, 45, 60]  # minutes
BREAK_DURATIONS = [3, 5, 8, 12]  # minutes
```

### Bandit Hyperparameters
```python
LINUCB_ALPHA = 1.0  # Exploration parameter
LINUCB_LAMBDA = 0.1  # Regularization
THOMPSON_PRIOR_VARIANCE = 1.0
```

### Reward Weights
```python
REWARD_W1 = 0.6  # Task progress weight
REWARD_W2 = 0.4  # Post-break relief weight
```

### Safety Constraints
```python
MAX_WORK_DURATION = 90  # minutes
MIN_BREAK_FREQUENCY = 120  # minutes
HIGH_COGNITIVE_LOAD_THRESHOLD = 0.8
```

### API Settings
```python
API_HOST = "127.0.0.1"
API_PORT = 5000
```

---

## Troubleshooting

### Server Won't Start

**Error:** `Address already in use`

**Solution:**
```bash
# Change port in config/config.py or use environment variable
export API_PORT=5001
python run_server.py
```

### Database Errors

**Error:** `No such table: sessions`

**Solution:**
```bash
python init_database.py
```

### Import Errors

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
# Make sure you're in the project root directory
pip install -r requirements.txt
```

### Keystroke Listener Not Working

**Error:** Permission denied (macOS/Linux)

**Solution:**
- **macOS**: System Preferences → Security & Privacy → Accessibility → Enable terminal/IDE
- **Linux**: May need to run with `sudo` or grant permissions
- **Windows**: Usually works without additional setup

### No Data for Metrics

**Error:** Metrics return `None` or `0`

**Solution:**
1. Generate test data: `python generate_test_data.py`
2. Or use the system with real sessions (it learns online)
3. Check that sessions have actions and rewards

### API Connection Refused

**Error:** `Connection refused`

**Solution:**
1. Make sure server is running: `python run_server.py`
2. Check the port: `http://127.0.0.1:5000`
3. Check firewall settings

---

## Project Structure

```
.
├── src/
│   ├── context_logger/      # Keystroke and session logging
│   ├── feature_extractor/   # Feature extraction
│   ├── bandit_engine/       # Bandit algorithms
│   ├── reward_handler/      # Reward computation
│   ├── api/                 # REST API
│   ├── database/            # Database models
│   ├── metrics/             # Metrics computation
│   └── data_generation/     # Synthetic data generator
├── tests/                   # Unit tests
├── config/                  # Configuration
├── requirements.txt         # Dependencies
├── run_server.py            # Server startup
├── init_database.py         # Database initialization
├── generate_test_data.py    # Test data generator
├── example_usage.py         # Usage example
└── GUIDE.md                 # This file
```

---

## Next Steps

1. **Start using the system**: Run `python run_server.py` and use the API
2. **Generate test data**: `python generate_test_data.py` for testing
3. **Compute metrics**: Use `/api/metrics` endpoint
4. **Customize**: Edit `config/config.py` for your needs
5. **Extend**: Add new bandit algorithms or features

---

## Support

For detailed proposal and research background, see `test.md`.

For code documentation, see inline docstrings in source files.

---

**Happy scheduling! 🎯**

