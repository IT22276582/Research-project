"""Tests for reward computation"""
import pytest
from src.reward_handler.reward_calculator import RewardCalculator, DelayedRewardTracker


def test_reward_computation():
    """Test reward computation"""
    calculator = RewardCalculator(w1=0.6, w2=0.4)
    
    user_data = {
        'chars_typed': 500,
        'keystrokes': [],
        'cognitive_load_pre_break': 0.7,
        'cognitive_load_post_break': 0.4,
        'user_reported_improved_focus': True,
        'deep_work_interrupted': False
    }
    
    reward = calculator.compute_reward(30, 5, user_data)
    
    assert reward.r_progress >= 0.0
    assert reward.r_relief >= 0.0
    assert -1.0 <= reward.immediate_reward <= 1.0


def test_delayed_reward_tracker():
    """Test delayed reward tracking"""
    tracker = DelayedRewardTracker(delay_seconds=1)  # Short delay for testing
    calculator = RewardCalculator()
    
    epoch_id = "test_epoch_1"
    immediate_reward = 0.7
    context_data = {
        'cognitive_load_pre_break': 0.7,
        'cognitive_load_post_break': 0.4
    }
    
    tracker.add_immediate_reward(epoch_id, immediate_reward, context_data)
    
    # Wait and check
    import time
    time.sleep(1.5)
    
    ready_rewards = tracker.check_delayed_rewards(calculator)
    assert epoch_id in ready_rewards
    assert ready_rewards[epoch_id] > 0

