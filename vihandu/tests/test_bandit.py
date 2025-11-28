"""Tests for bandit algorithms"""
import numpy as np
import pytest
from src.bandit_engine.linucb import LinUCB
from src.bandit_engine.thompson_sampling import ThompsonSampling


def test_linucb_basic():
    """Test basic LinUCB functionality"""
    bandit = LinUCB(alpha=1.0, lambda_reg=0.1, feature_dim=8)
    context = np.random.randn(8)
    
    # Select action
    action = bandit.select_action(context)
    assert action[0] in [20, 30, 45, 60]
    assert action[1] in [3, 5, 8, 12]
    
    # Update with reward
    reward = 0.8
    bandit.update(action, context, reward)
    
    # Select again (should be consistent)
    action2 = bandit.select_action(context)
    assert isinstance(action2, tuple)
    assert len(action2) == 2


def test_thompson_sampling_basic():
    """Test basic Thompson Sampling functionality"""
    bandit = ThompsonSampling(prior_variance=1.0, feature_dim=8)
    context = np.random.randn(8)
    
    # Select action
    action = bandit.select_action(context)
    assert action[0] in [20, 30, 45, 60]
    assert action[1] in [3, 5, 8, 12]
    
    # Update with reward
    reward = 0.8
    bandit.update(action, context, reward)
    
    # Select again
    action2 = bandit.select_action(context)
    assert isinstance(action2, tuple)


def test_safety_constraints():
    """Test safety constraints"""
    from src.bandit_engine.safety_constraints import SafetyConstraints, UserState
    
    safety = SafetyConstraints()
    bandit_action = (45, 5)
    
    # Test max work duration
    user_state = UserState(continuous_work_time=95.0)
    final_action, overridden, reason = safety.apply_constraints(bandit_action, user_state)
    assert overridden == True
    assert final_action[0] == 20  # Forced short work
    
    # Test high cognitive load
    user_state = UserState(cognitive_load=0.85)
    final_action, overridden, reason = safety.apply_constraints(bandit_action, user_state)
    assert overridden == True
    
    # Test normal case
    user_state = UserState(continuous_work_time=30.0, cognitive_load=0.5)
    final_action, overridden, reason = safety.apply_constraints(bandit_action, user_state)
    assert overridden == False
    assert final_action == bandit_action

