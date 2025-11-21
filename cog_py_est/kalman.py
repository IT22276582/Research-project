"""Lightweight Kalman filter with RLS-based observation adaptation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from .config import EstimatorConfig


@dataclass
class Estimate:
    timestamp: datetime
    load: float
    variance: float
    residual: float

    @property
    def ci95(self) -> float:
        return 1.96 * np.sqrt(self.variance)


class RLSAdapter:
    """Recursive least squares for observation weights."""

    def __init__(self, dim: int, forgetting_factor: float) -> None:
        self.weights = np.zeros(dim)
        self.P = np.eye(dim) * 10.0
        self.lambda_ = forgetting_factor

    def update(self, features: np.ndarray, target: float) -> np.ndarray:
        phi = features.reshape(-1, 1)
        gain_num = self.P @ phi
        gain_den = self.lambda_ + (phi.T @ self.P @ phi)[0][0]
        gain = gain_num / gain_den
        error = target - float(self.weights @ features)
        self.weights = self.weights + (gain.flatten() * error)
        self.P = (self.P - gain @ phi.T @ self.P) / self.lambda_
        return self.weights


class KalmanEstimator:
    """Scalar Kalman filter that consumes fused feature scores."""

    def __init__(self, config: EstimatorConfig, feature_dim: int) -> None:
        self.config = config
        self.feature_dim = feature_dim
        self.mean = config.diffuse_mean
        self.covariance = config.diffuse_variance
        self.observation_weights = np.ones(feature_dim) / max(feature_dim, 1)
        self.rls = RLSAdapter(feature_dim, config.rls_forgetting_factor)
        # Cap the latent state to avoid runaway values when a stored state is stale or corrupted.
        self._state_clip = 10.0

    def predict_update(
        self,
        features: np.ndarray,
        timestamp: datetime,
        quality: float,
        label: Optional[float] = None,
    ) -> Estimate:
        if label is not None:
            self.observation_weights = self.rls.update(features, label)

        # Project features into a scalar observation
        measurement = float(self.observation_weights @ features)
        scaled_measurement_noise = self.config.measurement_noise / max(quality, 1e-3)

        # Predict
        predicted_cov = self.covariance + self.config.process_noise

        # Update
        innovation = measurement - self.mean
        innovation_cov = predicted_cov + scaled_measurement_noise
        kalman_gain = predicted_cov / innovation_cov

        self.mean = self.mean + kalman_gain * innovation
        self.covariance = (1 - kalman_gain) * predicted_cov
        # Avoid unbounded growth if the state was restored to an extreme value.
        if abs(self.mean) > self._state_clip:
            self.mean = float(np.clip(self.mean, -self._state_clip, self._state_clip))
            self.covariance = min(self.covariance, self._state_clip)

        return Estimate(
            timestamp=timestamp,
            load=self.mean,
            variance=self.covariance,
            residual=innovation,
        )

    def learn_from_label(
        self, features: np.ndarray, label: float, timestamp: datetime
    ) -> Estimate:
        """Update the observation model and assimilate the EMA label."""
        self.observation_weights = self.rls.update(features, label)
        return self.assimilate_label(label, timestamp)

    def assimilate_label(self, label: float, timestamp: datetime) -> Estimate:
        """Treat the EMA label as a high-confidence measurement of latent load."""
        measurement_noise = self.config.measurement_noise * 0.1
        predicted_cov = self.covariance + self.config.process_noise
        innovation = label - self.mean
        innovation_cov = predicted_cov + measurement_noise
        kalman_gain = predicted_cov / innovation_cov
        self.mean = self.mean + kalman_gain * innovation
        self.covariance = (1 - kalman_gain) * predicted_cov
        return Estimate(
            timestamp=timestamp,
            load=self.mean,
            variance=self.covariance,
            residual=innovation,
        )

    def restore(
        self, estimate: Estimate, weights: np.ndarray, forgetting_factor: float
    ) -> None:
        """Restore saved filter state to support warm-start."""
        self.mean = estimate.load
        self.covariance = estimate.variance
        # Resize if stored weights differ; fall back to diffuse prior.
        if weights.shape[0] != self.feature_dim:
            self.observation_weights = np.ones(self.feature_dim) / max(self.feature_dim, 1)
            self.rls = RLSAdapter(self.feature_dim, self.config.rls_forgetting_factor)
            return
        self.observation_weights = weights
        self.rls = RLSAdapter(self.feature_dim, forgetting_factor)
        self.rls.weights = weights.copy()
