"""Configuration settings for Adaptive Scheduler"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/adaptive_scheduler.db")

# Bandit Configuration
WORK_INTERVALS = [20, 30, 45, 60]  # minutes
BREAK_DURATIONS = [3, 5, 8, 12]  # minutes

# Feature Extraction
IKI_MIN = 0.01  # seconds
IKI_MAX = 5.0  # seconds
FEATURE_WINDOW = 60  # seconds (1 minute)
SMOOTHING_WINDOW = 5  # samples

# Bandit Hyperparameters
LINUCB_ALPHA = 1.0
LINUCB_LAMBDA = 0.1
THOMPSON_PRIOR_VARIANCE = 1.0

# Reward Configuration
REWARD_W1 = 0.6  # Task progress weight
REWARD_W2 = 0.4  # Post-break relief weight
IMMEDIATE_REWARD_WEIGHT = 0.7
DELAYED_REWARD_WEIGHT = 0.3
DELAYED_REWARD_DELAY = 600  # seconds (10 minutes)

# Safety Constraints
MAX_WORK_DURATION = 90  # minutes
MIN_BREAK_FREQUENCY = 120  # minutes
HIGH_COGNITIVE_LOAD_THRESHOLD = 0.8
DEEP_WORK_DETECTION_THRESHOLD = 15  # minutes of sustained high productivity

# Micro-EMA
MICRO_EMA_INTERVAL = 20  # minutes (minimum)
MICRO_EMA_PROMPT_PROBABILITY = 0.3  # 30% chance per interval

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "5000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

# Privacy
ENCRYPTION_ENABLED = True
LOG_RETENTION_DAYS = 30

