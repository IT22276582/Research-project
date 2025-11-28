# Adaptive Scheduler - Contextual Bandit for Productivity

An adaptive study timer that uses contextual bandit algorithms to dynamically select optimal work intervals (20/30/45/60 min) and break durations (3/5/8/12 min) based on real-time cognitive state estimation.

## Features

- **Adaptive Scheduling**: Dynamically selects work intervals (20/30/45/60 min) and break durations (3/5/8/12 min)
- **Cognitive Load Estimation**: Uses keystroke dynamics and micro-EMA to estimate cognitive state
- **Contextual Bandits**: Implements LinUCB, Thompson Sampling algorithms
- **Privacy-Preserving**: Only stores keystroke timing metadata, no text content
- **Comprehensive Metrics**: 8 productivity metrics (PG, RPH, AHL, EOI, BUC, CTU, SPF, SVR)
- **Safety Constraints**: Enforces maximum work duration, break frequency, and cognitive load thresholds

## Project Structure

```
.
├── src/
│   ├── context_logger/      # Module 1: Keystroke and session logging
│   ├── feature_extractor/   # Module 2: Feature extraction from keystrokes
│   ├── bandit_engine/       # Module 3: Contextual bandit algorithms
│   ├── reward_handler/      # Module 4: Reward computation
│   ├── api/                 # Module 5: Flask REST API endpoints
│   ├── database/            # Database models and schema
│   └── metrics/             # Module 8: Metric computation
├── tests/                   # Unit and integration tests
├── config/                  # Configuration files
├── requirements.txt
├── run_server.py
├── init_database.py
└── example_usage.py
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
python init_database.py
```

4. (Optional) Generate test data:
```bash
python generate_test_data.py
```

## Quick Start

### Starting the API Server

```bash
python run_server.py
```

The API will be available at `http://127.0.0.1:5000`

### Example Usage

```bash
python example_usage.py
```

## API Endpoints

### Core Endpoints

- `POST /api/start-session` - Start a new study session
- `GET /api/get-recommendation` - Get work/break recommendation
- `POST /api/end-interval` - End interval and compute reward
- `POST /api/submit-feedback` - Submit micro-EMA feedback
- `POST /api/end-session` - End study session
- `GET /api/metrics` - Get computed metrics (PG, RPH, AHL, etc.)
- `GET /api/health` - Health check

See `IMPLEMENTATION_GUIDE.md` for detailed API documentation.

## Metrics

The system computes 8 productivity-specific metrics:

1. **PG (Personalization Gain)**: Improvement over Pomodoro baseline
2. **RPH (Regret-per-Hour)**: Normalized regret by study time
3. **AHL (Adaptation Half-Life)**: Time to recover after context shift
4. **EOI (Exploration Overhead Index)**: Cost of exploration
5. **AUC-BUC**: Area under break utility curve
6. **CTU (Counterfactual Targeting Uplift)**: Causal effect estimation
7. **SPF (Stability-Productivity Frontier)**: Reward stability variance
8. **SVR (Safety-Violation Rate)**: Frequency of safety overrides

## Configuration

Edit `config/config.py` to customize:

- Work/Break intervals
- Bandit hyperparameters
- Reward weights
- Safety constraints

## Testing

Run tests:
```bash
pytest tests/
```

## Development

See `IMPLEMENTATION_GUIDE.md` for detailed development instructions and `IMPLEMENTATION_SUMMARY.md` for what's implemented.

## References

See `test.md` for the complete research proposal with detailed metric definitions and implementation specifications.

## License

Research project - See proposal document for details.
