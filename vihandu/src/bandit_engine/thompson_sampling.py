"""Thompson Sampling (Bayesian) contextual bandit"""
import numpy as np
from typing import Tuple
from src.bandit_engine.base_bandit import BaseBandit
from config.config import THOMPSON_PRIOR_VARIANCE


class ThompsonSampling(BaseBandit):
    """Thompson Sampling contextual bandit with Bayesian linear regression"""
    
    def __init__(self, prior_variance: float = THOMPSON_PRIOR_VARIANCE, 
                 feature_dim: int = 8, noise_variance: float = 1.0):
        """
        Initialize Thompson Sampling
        
        Args:
            prior_variance: Prior variance for parameters
            feature_dim: Dimension of context feature vector
            noise_variance: Noise variance in reward observations
        """
        super().__init__()
        self.prior_variance = prior_variance
        self.feature_dim = feature_dim
        self.noise_variance = noise_variance
        
        # Per-action posterior parameters
        # Using Bayesian linear regression with conjugate priors
        self.posterior_mean = {}  # μ[a] = posterior mean of theta
        self.posterior_cov = {}   # Σ[a] = posterior covariance of theta
        
        # Initialize priors for each action
        for action in self.actions:
            self.posterior_mean[action] = np.zeros(feature_dim)
            self.posterior_cov[action] = np.eye(feature_dim) * prior_variance
    
    def select_action(self, context: np.ndarray) -> Tuple[int, int]:
        """
        Select action using Thompson Sampling
        
        Args:
            context: Context feature vector
        
        Returns:
            Tuple of (work_interval, break_duration)
        """
        # Ensure context is correct shape
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        
        max_sample = -np.inf
        best_action = self.actions[0]
        
        for action in self.actions:
            # Sample theta from posterior
            try:
                theta_sample = np.random.multivariate_normal(
                    self.posterior_mean[action],
                    self.posterior_cov[action]
                )
            except np.linalg.LinAlgError:
                # If covariance is singular, use mean only
                theta_sample = self.posterior_mean[action]
            
            # Compute expected reward
            expected_reward = np.dot(theta_sample, context)
            
            if expected_reward > max_sample:
                max_sample = expected_reward
                best_action = action
        
        self.action_counts[best_action] += 1
        return best_action
    
    def update(self, action: Tuple[int, int], context: np.ndarray, reward: float):
        """
        Update Thompson Sampling with observed reward (Bayesian update)
        
        Args:
            action: Selected action
            context: Context feature vector
            reward: Observed reward
        """
        # Ensure context is correct shape
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        
        # Bayesian update for linear regression
        # Prior: N(μ_0, Σ_0)
        # Likelihood: y ~ N(x^T θ, σ^2)
        # Posterior: N(μ_n, Σ_n)
        
        μ_old = self.posterior_mean[action]
        Σ_old = self.posterior_cov[action]
        
        # Update covariance: Σ_n = (Σ_0^-1 + (1/σ^2) * x * x^T)^-1
        try:
            Σ_old_inv = np.linalg.inv(Σ_old)
        except np.linalg.LinAlgError:
            Σ_old_inv = np.linalg.pinv(Σ_old)
        
        context_outer = np.outer(context, context)
        Σ_new_inv = Σ_old_inv + (1.0 / self.noise_variance) * context_outer
        
        try:
            Σ_new = np.linalg.inv(Σ_new_inv)
        except np.linalg.LinAlgError:
            Σ_new = np.linalg.pinv(Σ_new_inv)
        
        # Update mean: μ_n = Σ_n * (Σ_0^-1 * μ_0 + (1/σ^2) * x * y)
        μ_new = Σ_new @ (Σ_old_inv @ μ_old + (1.0 / self.noise_variance) * context * reward)
        
        self.posterior_mean[action] = μ_new
        self.posterior_cov[action] = Σ_new
    
    def get_expected_reward(self, action: Tuple[int, int], context: np.ndarray) -> float:
        """Get expected reward (using posterior mean)"""
        if len(context) != self.feature_dim:
            context = np.pad(context, (0, max(0, self.feature_dim - len(context))), 
                           mode='constant')[:self.feature_dim]
        return np.dot(self.posterior_mean[action], context)

