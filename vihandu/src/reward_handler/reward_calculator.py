"""Reward computation for bandit learning"""
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from config.config import (
    REWARD_W1, REWARD_W2, IMMEDIATE_REWARD_WEIGHT, 
    DELAYED_REWARD_WEIGHT, DELAYED_REWARD_DELAY
)


@dataclass
class RewardComponents:
    """Components of reward computation"""
    r_progress: float  # Task progress component [0, 1]
    r_relief: float  # Post-break relief component [0, 1]
    immediate_reward: float  # Combined immediate reward
    delayed_reward: Optional[float] = None  # Delayed reward (computed later)
    final_reward: Optional[float] = None  # Final weighted reward


class RewardCalculator:
    """Computes rewards for bandit learning"""
    
    def __init__(self, w1: float = REWARD_W1, w2: float = REWARD_W2):
        """
        Initialize reward calculator
        
        Args:
            w1: Weight for task progress component
            w2: Weight for post-break relief component
        """
        self.w1 = w1
        self.w2 = w2
        assert abs(w1 + w2 - 1.0) < 1e-6, "Weights must sum to 1.0"
    
    def compute_reward(self, work_interval: int, break_duration: int,
                      user_data: Dict) -> RewardComponents:
        """
        Compute reward for a work-break cycle
        
        Args:
            work_interval: Work interval duration in minutes
            break_duration: Break duration in minutes
            user_data: Dictionary containing:
                - chars_typed: Number of characters typed
                - keystrokes: List of keystroke events
                - cognitive_load_pre_break: Cognitive load before break
                - cognitive_load_post_break: Cognitive load after break (optional)
                - user_reported_improved_focus: Boolean (optional)
                - deep_work_interrupted: Boolean (optional)
        
        Returns:
            RewardComponents object
        """
        # Component 1: Task Progress
        r_progress = self._compute_progress_reward(work_interval, user_data)
        
        # Component 2: Post-Break Relief
        r_relief = self._compute_relief_reward(break_duration, user_data)
        
        # Composite immediate reward
        immediate_reward = self.w1 * r_progress + self.w2 * r_relief
        
        # Reward shaping
        immediate_reward = self._apply_reward_shaping(immediate_reward, user_data)
        
        # Clip to [-1, 1] range
        immediate_reward = np.clip(immediate_reward, -1.0, 1.0)
        
        return RewardComponents(
            r_progress=r_progress,
            r_relief=r_relief,
            immediate_reward=immediate_reward
        )
    
    def _compute_progress_reward(self, work_interval: int, user_data: Dict) -> float:
        """Compute task progress component"""
        chars_typed = user_data.get('chars_typed', 0)
        keystrokes = user_data.get('keystrokes', [])
        
        # Typing speed (chars per minute)
        chars_per_min = chars_typed / work_interval if work_interval > 0 else 0.0
        
        # Focus duration (time without pauses >2 seconds)
        focus_duration = self._compute_focus_duration(keystrokes, work_interval)
        
        # Normalize (assume 0-200 chars/min range, 0-100% focus)
        normalized_speed = min(chars_per_min / 200.0, 1.0)
        normalized_focus = focus_duration / work_interval if work_interval > 0 else 0.0
        
        # Weighted combination
        r_progress = 0.6 * normalized_speed + 0.4 * normalized_focus
        
        return np.clip(r_progress, 0.0, 1.0)
    
    def _compute_focus_duration(self, keystrokes: list, work_interval: int) -> float:
        """Compute focus duration (time without long pauses)"""
        if not keystrokes or len(keystrokes) < 2:
            return 0.0
        
        focus_time = 0.0
        last_timestamp = keystrokes[0].timestamp if hasattr(keystrokes[0], 'timestamp') else 0.0
        
        for i in range(1, len(keystrokes)):
            current_timestamp = keystrokes[i].timestamp if hasattr(keystrokes[i], 'timestamp') else 0.0
            gap = current_timestamp - last_timestamp
            
            if gap < 2.0:  # No pause >2 seconds
                focus_time += gap
            else:
                # Long pause detected, reset focus
                pass
            
            last_timestamp = current_timestamp
        
        return focus_time / 60.0  # Convert to minutes
    
    def _compute_relief_reward(self, break_duration: int, user_data: Dict) -> float:
        """Compute post-break relief component"""
        load_pre = user_data.get('cognitive_load_pre_break', 0.5)
        load_post = user_data.get('cognitive_load_post_break', None)
        
        if load_post is None:
            # If no post-break measurement, use default based on break duration
            # Longer breaks generally provide more relief
            load_post = load_pre - (break_duration / 12.0) * 0.3
            load_post = max(0.0, load_post)
        
        # Delta load (reduction is positive)
        delta_load = load_pre - load_post
        
        # Normalize to [0, 1]
        r_relief = np.clip(delta_load, 0.0, 1.0)
        
        return r_relief
    
    def _apply_reward_shaping(self, reward: float, user_data: Dict) -> float:
        """Apply reward shaping bonuses/penalties"""
        # Bonus: User reported improved focus
        if user_data.get('user_reported_improved_focus', False):
            reward += 0.2
        
        # Penalty: Deep work interrupted
        if user_data.get('deep_work_interrupted', False):
            reward -= 0.3
        
        return reward
    
    def compute_final_reward(self, immediate_reward: float, 
                           delayed_reward: Optional[float] = None) -> float:
        """
        Compute final reward combining immediate and delayed components
        
        Args:
            immediate_reward: Immediate reward
            delayed_reward: Delayed reward (optional)
        
        Returns:
            Final weighted reward
        """
        if delayed_reward is None:
            return immediate_reward
        
        final_reward = (IMMEDIATE_REWARD_WEIGHT * immediate_reward + 
                       DELAYED_REWARD_WEIGHT * delayed_reward)
        
        return np.clip(final_reward, -1.0, 1.0)


class DelayedRewardTracker:
    """Tracks delayed rewards for actions"""
    
    def __init__(self, delay_seconds: int = DELAYED_REWARD_DELAY):
        """
        Initialize delayed reward tracker
        
        Args:
            delay_seconds: Delay in seconds before computing delayed reward
        """
        self.delay_seconds = delay_seconds
        self.pending_rewards = {}  # {epoch_id: (immediate_reward, timestamp, context_data)}
    
    def add_immediate_reward(self, epoch_id: str, immediate_reward: float, 
                            context_data: Dict):
        """Add immediate reward for later delayed computation"""
        import time
        self.pending_rewards[epoch_id] = (
            immediate_reward,
            time.time(),
            context_data
        )
    
    def check_delayed_rewards(self, reward_calculator: RewardCalculator) -> Dict[str, float]:
        """
        Check for rewards that are ready for delayed computation
        
        Args:
            reward_calculator: RewardCalculator instance
        
        Returns:
            Dictionary of {epoch_id: final_reward}
        """
        import time
        current_time = time.time()
        ready_rewards = {}
        
        for epoch_id, (imm_reward, timestamp, context_data) in list(self.pending_rewards.items()):
            if current_time - timestamp >= self.delay_seconds:
                # Compute delayed reward
                delayed_reward = self._compute_delayed_reward(context_data, reward_calculator)
                
                # Compute final reward
                final_reward = reward_calculator.compute_final_reward(
                    imm_reward, delayed_reward
                )
                
                ready_rewards[epoch_id] = final_reward
                del self.pending_rewards[epoch_id]
        
        return ready_rewards
    
    def _compute_delayed_reward(self, context_data: Dict, 
                               reward_calculator: RewardCalculator) -> float:
        """Compute delayed reward component"""
        # Use post-break cognitive load if available
        load_post = context_data.get('cognitive_load_post_break', None)
        load_pre = context_data.get('cognitive_load_pre_break', 0.5)
        
        if load_post is not None:
            delta_load = load_pre - load_post
            return np.clip(delta_load, 0.0, 1.0)
        
        # Default: assume some recovery occurred
        return 0.3

