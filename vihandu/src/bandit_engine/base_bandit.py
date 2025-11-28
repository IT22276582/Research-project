"""Base class for contextual bandit algorithms"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, Optional
from config.config import WORK_INTERVALS, BREAK_DURATIONS


class BaseBandit(ABC):
    """Base class for contextual bandit algorithms"""
    
    def __init__(self):
        """Initialize bandit"""
        # Action space: (work_interval, break_duration)
        self.actions = [(w, b) for w in WORK_INTERVALS for b in BREAK_DURATIONS]
        self.num_actions = len(self.actions)
        self.action_counts = {action: 0 for action in self.actions}
    
    @abstractmethod
    def select_action(self, context: np.ndarray) -> Tuple[int, int]:
        """
        Select action given context
        
        Args:
            context: Context feature vector
        
        Returns:
            Tuple of (work_interval, break_duration) in minutes
        """
        pass
    
    @abstractmethod
    def update(self, action: Tuple[int, int], context: np.ndarray, reward: float):
        """
        Update bandit with observed reward
        
        Args:
            action: Selected action (work_interval, break_duration)
            context: Context feature vector at time of action
            reward: Observed reward
        """
        pass
    
    def get_action_index(self, action: Tuple[int, int]) -> int:
        """Get index of action in action space"""
        return self.actions.index(action)
    
    def get_action_by_index(self, index: int) -> Tuple[int, int]:
        """Get action by index"""
        return self.actions[index]

