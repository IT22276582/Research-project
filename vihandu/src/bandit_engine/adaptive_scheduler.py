"""Main adaptive scheduler that coordinates bandit and safety constraints"""
import numpy as np
from typing import Tuple, Optional
from src.bandit_engine.base_bandit import BaseBandit
from src.bandit_engine.linucb import LinUCB
from src.bandit_engine.thompson_sampling import ThompsonSampling
from src.bandit_engine.safety_constraints import SafetyConstraints, UserState
from src.feature_extractor.feature_extractor import ContextFeatures


class AdaptiveScheduler:
    """Main adaptive scheduler using contextual bandit"""
    
    def __init__(self, algorithm: str = "LinUCB", feature_dim: int = 8):
        """
        Initialize adaptive scheduler
        
        Args:
            algorithm: Bandit algorithm ('LinUCB' or 'ThompsonSampling')
            feature_dim: Dimension of context feature vector
        """
        self.algorithm_name = algorithm
        self.feature_dim = feature_dim
        
        # Initialize bandit algorithm
        if algorithm == "LinUCB":
            self.bandit: BaseBandit = LinUCB(feature_dim=feature_dim)
        elif algorithm == "ThompsonSampling":
            self.bandit: BaseBandit = ThompsonSampling(feature_dim=feature_dim)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        self.safety = SafetyConstraints()
        self.user_state = UserState()
    
    def get_recommendation(self, context_features: ContextFeatures) -> Tuple[Tuple[int, int], dict]:
        """
        Get work/break recommendation based on context
        
        Args:
            context_features: Extracted context features
        
        Returns:
            Tuple of ((work_interval, break_duration), metadata)
            Metadata includes: was_overridden, override_reason, confidence, etc.
        """
        # Convert context to vector
        context_vector = context_features.to_vector()
        
        # Update user state from context
        self.user_state.cognitive_load = context_features.cognitive_load
        
        # Get bandit recommendation
        bandit_action = self.bandit.select_action(context_vector)
        
        # Apply safety constraints
        final_action, was_overridden, override_reason = self.safety.apply_constraints(
            bandit_action, self.user_state
        )
        
        # Compute confidence (expected reward)
        if hasattr(self.bandit, 'get_expected_reward'):
            confidence = self.bandit.get_expected_reward(final_action, context_vector)
        else:
            confidence = 0.5  # Default confidence
        
        metadata = {
            'bandit_action': bandit_action,
            'final_action': final_action,
            'was_overridden': was_overridden,
            'override_reason': override_reason,
            'confidence': float(confidence),
            'algorithm': self.algorithm_name,
            'cognitive_load': float(context_features.cognitive_load)
        }
        
        return final_action, metadata
    
    def update(self, action: Tuple[int, int], context_features: ContextFeatures, reward: float):
        """
        Update bandit with observed reward
        
        Args:
            action: Action that was taken
            context_features: Context features at time of action
            reward: Observed reward
        """
        context_vector = context_features.to_vector()
        self.bandit.update(action, context_vector, reward)
    
    def update_user_state(self, continuous_work_time: float = None,
                         time_since_last_break: float = None,
                         sustained_high_productivity: float = None):
        """Update user state for safety constraints"""
        if continuous_work_time is not None:
            self.user_state.continuous_work_time = continuous_work_time
        if time_since_last_break is not None:
            self.user_state.time_since_last_break = time_since_last_break
        if sustained_high_productivity is not None:
            self.user_state.sustained_high_productivity = sustained_high_productivity

