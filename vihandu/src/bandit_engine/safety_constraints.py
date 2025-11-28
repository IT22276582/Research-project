"""Safety constraints for bandit actions"""
from typing import Tuple, Optional
from dataclasses import dataclass
from config.config import (
    MAX_WORK_DURATION, MIN_BREAK_FREQUENCY, 
    HIGH_COGNITIVE_LOAD_THRESHOLD, DEEP_WORK_DETECTION_THRESHOLD
)


@dataclass
class UserState:
    """Current user state for safety checks"""
    continuous_work_time: float = 0.0  # minutes
    time_since_last_break: float = 0.0  # minutes
    cognitive_load: float = 0.5  # [0, 1]
    sustained_high_productivity: float = 0.0  # minutes


class SafetyConstraints:
    """Applies safety constraints to bandit recommendations"""
    
    @staticmethod
    def apply_constraints(bandit_action: Tuple[int, int], user_state: UserState) -> Tuple[Tuple[int, int], bool, Optional[str]]:
        """
        Apply safety constraints to bandit action
        
        Args:
            bandit_action: Recommended action (work_interval, break_duration)
            user_state: Current user state
        
        Returns:
            Tuple of (final_action, was_overridden, override_reason)
        """
        work_interval, break_duration = bandit_action
        override_reason = None
        
        # Constraint 1: Maximum work duration
        if user_state.continuous_work_time > MAX_WORK_DURATION:
            work_interval = 20  # Force short work
            break_duration = 12  # Force long break
            override_reason = f"Max work duration exceeded ({user_state.continuous_work_time:.1f} min > {MAX_WORK_DURATION} min)"
            return (work_interval, break_duration), True, override_reason
        
        # Constraint 2: Minimum break frequency
        if user_state.time_since_last_break > MIN_BREAK_FREQUENCY:
            work_interval = 20  # Force break soon
            break_duration = 8
            override_reason = f"Min break frequency violated ({user_state.time_since_last_break:.1f} min > {MIN_BREAK_FREQUENCY} min)"
            return (work_interval, break_duration), True, override_reason
        
        # Constraint 3: High cognitive load
        if user_state.cognitive_load > HIGH_COGNITIVE_LOAD_THRESHOLD:
            work_interval = 20  # Force short work
            break_duration = 12  # Force long break
            override_reason = f"High cognitive load detected ({user_state.cognitive_load:.2f} > {HIGH_COGNITIVE_LOAD_THRESHOLD})"
            return (work_interval, break_duration), True, override_reason
        
        # Constraint 4: Deep work protection (don't interrupt)
        if user_state.sustained_high_productivity > DEEP_WORK_DETECTION_THRESHOLD:
            # Allow bandit action but log that we're in deep work
            override_reason = f"Deep work detected ({user_state.sustained_high_productivity:.1f} min), allowing bandit recommendation"
            return bandit_action, False, override_reason
        
        # No override needed
        return bandit_action, False, None

