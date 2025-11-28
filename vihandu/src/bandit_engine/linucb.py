"""Linear Upper Confidence Bound (LinUCB) bandit algorithm"""
import numpy as np
from typing import Tuple
from src.bandit_engine.base_bandit import BaseBandit
from config.config import LINUCB_ALPHA, LINUCB_LAMBDA


class LinUCB(BaseBandit):
    """Linear Upper Confidence Bound contextual bandit"""
    
    def __init__(self, alpha: float = LINUCB_ALPHA, lambda_reg: float = LINUCB_LAMBDA, 
                 feature_dim: int = 8):
        """
        Initialize LinUCB
        
        Args:
            alpha: Exploration parameter (higher = more exploration)
            lambda_reg: Regularization parameter
            feature_dim: Dimension of context feature vector
        """
        super().__init__()
        self.alpha = alpha
        self.lambda_reg = lambda_reg
        self.feature_dim = feature_dim
        
        # Per-action matrices: A[a] and b[a]
        self.A = {}  # A[a] = lambda_reg * I + sum(x_t * x_t^T)
        self.b = {}  # b[a] = sum(r_t * x_t)
        self.theta = {}  # theta[a] = A[a]^-1 * b[a] (cached)
        
        # Initialize matrices for each action
        for action in self.actions:
            self.A[action] = np.eye(feature_dim) * lambda_reg
            self.b[action] = np.zeros(feature_dim)
            self.theta[action] = np.zeros(feature_dim)
    
    def select_action(self, context: np.ndarray) -> Tuple[int, int]:
        """
        Select action using LinUCB
        
        Args:
            context: Context feature vector (should be feature_dim length)
        
        Returns:
            Tuple of (work_interval, break_duration)
        """
        # Ensure context is correct shape
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        
        max_ucb = -np.inf
        best_action = self.actions[0]  # Default to first action
        
        for action in self.actions:
            # Compute mean reward estimate
            mean = np.dot(self.theta[action], context)
            
            # Compute confidence bound
            try:
                A_inv = np.linalg.inv(self.A[action])
                confidence = self.alpha * np.sqrt(context.T @ A_inv @ context)
            except np.linalg.LinAlgError:
                # If matrix is singular, use pseudo-inverse
                A_inv = np.linalg.pinv(self.A[action])
                confidence = self.alpha * np.sqrt(context.T @ A_inv @ context)
            
            ucb = mean + confidence
            
            if ucb > max_ucb:
                max_ucb = ucb
                best_action = action
        
        self.action_counts[best_action] += 1
        return best_action
    
    def update(self, action: Tuple[int, int], context: np.ndarray, reward: float):
        """
        Update LinUCB with observed reward
        
        Args:
            action: Selected action
            context: Context feature vector
            reward: Observed reward
        """
        # Ensure context is correct shape
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        
        # Update A and b matrices
        context_outer = np.outer(context, context)
        self.A[action] += context_outer
        self.b[action] += reward * context
        
        # Update theta (parameter estimate)
        try:
            self.theta[action] = np.linalg.solve(self.A[action], self.b[action])
        except np.linalg.LinAlgError:
            # If singular, use pseudo-inverse
            self.theta[action] = np.linalg.pinv(self.A[action]) @ self.b[action]
    
    def get_expected_reward(self, action: Tuple[int, int], context: np.ndarray) -> float:
        """Get expected reward for an action given context"""
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        return np.dot(self.theta[action], context)

