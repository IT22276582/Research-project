"""Main feature extractor that computes context vectors from keystroke data"""
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.database.models import KeystrokeEvent, ContextVector, SessionLocal
from src.feature_extractor.iki_calculator import compute_iki, compute_iki_statistics
from config.config import FEATURE_WINDOW, SMOOTHING_WINDOW


@dataclass
class ContextFeatures:
    """Context feature vector"""
    mean_iki: float
    std_iki: float
    typing_speed: float  # chars/min (estimated from keystrokes)
    correction_ratio: float  # backspaces / total_keys
    pause_count: int  # pauses >1 second
    session_duration: float  # minutes
    time_of_day: int  # 0=morning, 1=afternoon, 2=evening
    cognitive_load: float  # Estimated [0, 1]
    
    def to_vector(self) -> np.ndarray:
        """Convert to numpy array for bandit input"""
        return np.array([
            self.mean_iki,
            self.std_iki,
            self.typing_speed,
            self.correction_ratio,
            self.pause_count,
            self.session_duration,
            self.time_of_day,
            self.cognitive_load
        ])


class FeatureExtractor:
    """Extracts context features from keystroke events"""
    
    def __init__(self, session_id: str):
        """
        Initialize feature extractor
        
        Args:
            session_id: Current session identifier
        """
        self.session_id = session_id
        self.db_session = SessionLocal()
        self.feature_history: List[ContextFeatures] = []
    
    def extract_features(self, window_seconds: int = FEATURE_WINDOW) -> ContextFeatures:
        """
        Extract features from recent keystroke events
        
        Args:
            window_seconds: Time window in seconds to analyze (default: 60 seconds)
        
        Returns:
            ContextFeatures object
        """
        # Get keystroke events from last window
        cutoff_time = datetime.utcnow().timestamp() - window_seconds
        
        events = self.db_session.query(KeystrokeEvent).filter(
            KeystrokeEvent.session_id == self.session_id,
            KeystrokeEvent.timestamp >= cutoff_time
        ).order_by(KeystrokeEvent.timestamp).all()
        
        if not events:
            # Return default features if no events
            return self._default_features()
        
        # Prepare event list for IKI calculation
        event_list = [(e.timestamp, e.event_type) for e in events]
        
        # Compute IKI
        iki_list = compute_iki(event_list)
        iki_stats = compute_iki_statistics(iki_list)
        
        # Compute typing speed (estimate: keys per minute)
        total_keys = len([e for e in events if e.event_type == 'down'])
        time_span = events[-1].timestamp - events[0].timestamp if len(events) > 1 else window_seconds
        typing_speed = (total_keys / time_span * 60) if time_span > 0 else 0.0
        
        # Compute correction ratio (backspace key code varies by OS, use common codes)
        # Common backspace codes: 8 (Windows/Linux), 51 (some systems)
        backspace_codes = {8, 51}
        backspace_count = len([e for e in events if e.key_code in backspace_codes and e.event_type == 'down'])
        correction_ratio = backspace_count / total_keys if total_keys > 0 else 0.0
        
        # Compute pause count (gaps >1 second)
        pause_count = 0
        for i in range(1, len(events)):
            gap = events[i].timestamp - events[i-1].timestamp
            if gap > 1.0:
                pause_count += 1
        
        # Get session duration
        session = self.db_session.query(KeystrokeEvent).filter_by(
            session_id=self.session_id
        ).first()
        session_start = events[0].timestamp if events else datetime.utcnow().timestamp()
        session_duration = (datetime.utcnow().timestamp() - session_start) / 60.0  # minutes
        
        # Time of day (0=morning 6-12, 1=afternoon 12-18, 2=evening 18-6)
        hour = datetime.utcnow().hour
        if 6 <= hour < 12:
            time_of_day = 0
        elif 12 <= hour < 18:
            time_of_day = 1
        else:
            time_of_day = 2
        
        # Estimate cognitive load (simplified: based on typing speed and correction ratio)
        # Higher speed + lower corrections = lower load (better performance)
        # Normalize typing speed (assume 0-200 chars/min range)
        normalized_speed = min(typing_speed / 200.0, 1.0)
        cognitive_load = 1.0 - (normalized_speed * 0.7 + (1.0 - correction_ratio) * 0.3)
        cognitive_load = max(0.0, min(1.0, cognitive_load))  # Clamp to [0, 1]
        
        features = ContextFeatures(
            mean_iki=iki_stats['mean_iki'],
            std_iki=iki_stats['std_iki'],
            typing_speed=typing_speed,
            correction_ratio=correction_ratio,
            pause_count=pause_count,
            session_duration=session_duration,
            time_of_day=time_of_day,
            cognitive_load=cognitive_load
        )
        
        # Add to history for smoothing
        self.feature_history.append(features)
        
        # Apply smoothing if enough history
        if len(self.feature_history) >= SMOOTHING_WINDOW:
            features = self._smooth_features()
        
        return features
    
    def _default_features(self) -> ContextFeatures:
        """Return default feature values when no data available"""
        return ContextFeatures(
            mean_iki=0.2,
            std_iki=0.1,
            typing_speed=0.0,
            correction_ratio=0.0,
            pause_count=0,
            session_duration=0.0,
            time_of_day=1,  # Default to afternoon
            cognitive_load=0.5
        )
    
    def _smooth_features(self) -> ContextFeatures:
        """Apply moving average smoothing to recent features"""
        if len(self.feature_history) < SMOOTHING_WINDOW:
            return self.feature_history[-1]
        
        recent = self.feature_history[-SMOOTHING_WINDOW:]
        
        # Average each feature
        return ContextFeatures(
            mean_iki=np.mean([f.mean_iki for f in recent]),
            std_iki=np.mean([f.std_iki for f in recent]),
            typing_speed=np.mean([f.typing_speed for f in recent]),
            correction_ratio=np.mean([f.correction_ratio for f in recent]),
            pause_count=int(np.mean([f.pause_count for f in recent])),
            session_duration=np.mean([f.session_duration for f in recent]),
            time_of_day=recent[-1].time_of_day,  # Don't smooth categorical
            cognitive_load=np.mean([f.cognitive_load for f in recent])
        )
    
    def save_features_to_db(self, features: ContextFeatures):
        """Save extracted features to database"""
        db_context = ContextVector(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            mean_iki=features.mean_iki,
            std_iki=features.std_iki,
            typing_speed=features.typing_speed,
            correction_ratio=features.correction_ratio,
            pause_count=features.pause_count,
            session_duration=features.session_duration,
            time_of_day=features.time_of_day,
            cognitive_load=features.cognitive_load
        )
        self.db_session.add(db_context)
        self.db_session.commit()
    
    def normalize_features(self, features: ContextFeatures, user_stats: Optional[Dict] = None) -> ContextFeatures:
        """
        Normalize features using user-specific statistics (z-score normalization)
        
        Args:
            features: Raw features
            user_stats: Dictionary with 'mean' and 'std' for each feature
        
        Returns:
            Normalized features
        """
        if not user_stats:
            # No normalization if no user stats available
            return features
        
        # Normalize numeric features (not categorical like time_of_day)
        normalized = ContextFeatures(
            mean_iki=self._normalize_value(features.mean_iki, user_stats.get('mean_iki', {})),
            std_iki=self._normalize_value(features.std_iki, user_stats.get('std_iki', {})),
            typing_speed=self._normalize_value(features.typing_speed, user_stats.get('typing_speed', {})),
            correction_ratio=self._normalize_value(features.correction_ratio, user_stats.get('correction_ratio', {})),
            pause_count=int(self._normalize_value(features.pause_count, user_stats.get('pause_count', {}))),
            session_duration=self._normalize_value(features.session_duration, user_stats.get('session_duration', {})),
            time_of_day=features.time_of_day,  # Don't normalize categorical
            cognitive_load=features.cognitive_load  # Already normalized [0, 1]
        )
        
        return normalized
    
    def _normalize_value(self, value: float, stats: Dict) -> float:
        """Z-score normalization"""
        mean = stats.get('mean', 0.0)
        std = stats.get('std', 1.0)
        if std < 1e-6:
            return 0.0
        return (value - mean) / std
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db_session'):
            self.db_session.close()

