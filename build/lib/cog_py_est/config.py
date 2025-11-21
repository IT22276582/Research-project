"""Configuration models for the Python cognitive load estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]
from pydantic import BaseModel, Field, field_validator


class WindowConfig(BaseModel):
    window_seconds: float = 60.0
    hop_seconds: float = 15.0
    inactivity_gap_seconds: float = 5.0

    @field_validator("window_seconds", "hop_seconds", "inactivity_gap_seconds")
    @classmethod
    def _positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("window settings must be positive")
        return value


class EstimatorConfig(BaseModel):
    process_noise: float = 0.01
    measurement_noise: float = 0.05
    initial_variance: float = 1.0
    rls_forgetting_factor: float = 0.98
    baseline_minutes: int = 5
    diffuse_mean: float = 0.0
    diffuse_variance: float = 4.0
    baseline_target_variance: float = 0.3

    @field_validator("process_noise", "measurement_noise", "initial_variance", "diffuse_variance", "baseline_target_variance")
    @classmethod
    def _non_negative(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("noise and variance terms must be > 0")
        return value

    @field_validator("rls_forgetting_factor")
    @classmethod
    def _forgetting_range(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("forgetting factor must be in (0, 1]")
        return value


class PermissionsConfig(BaseModel):
    allowed_sources: List[str] = Field(
        default_factory=lambda: ["keyboard", "pointer", "system"]
    )
    privacy_pause: bool = False
    context_blocklist: List[str] = Field(default_factory=list)
    idle_block_seconds: int = 900
    consent_log_path: Path = Path("data/consent_log.jsonl")
    state_path: Path = Path("data/permissions_state.json")

    @field_validator("allowed_sources")
    @classmethod
    def _non_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("at least one event source must be allowed")
        return value

    @field_validator("idle_block_seconds")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("idle block seconds must be >= 0")
        return value


class EmaConfig(BaseModel):
    min_seconds_between_prompts: int = 1800
    cooldown_on_dismiss_seconds: int = 900
    trigger_uncertainty_threshold: float = 0.25
    trigger_residual_threshold: float = 0.2

    @field_validator("min_seconds_between_prompts", "cooldown_on_dismiss_seconds")
    @classmethod
    def _positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("EMA timing must be positive")
        return value


class StorageConfig(BaseModel):
    path: Path = Path("data/state.db")
    enable_retention_prune: bool = True
    retention_hours: int = 48

    @field_validator("retention_hours")
    @classmethod
    def _retention_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("retention_hours must be positive")
        return value


class ServiceConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class ExportConfig(BaseModel):
    enabled: bool = True
    output_dir: Path = Path("data/exports")
    require_review: bool = True
    review_token: Optional[str] = None


class SensitivityProfile(BaseModel):
    residual_threshold: float
    uncertainty_threshold: float
    process_noise: float
    measurement_noise: float
    description: Optional[str] = None


class SensitivityConfig(BaseModel):
    current_profile: str = "balanced"
    profiles: Dict[str, SensitivityProfile] = Field(default_factory=dict)

    def apply(self, estimator: EstimatorConfig, ema: EmaConfig) -> None:
        if not self.profiles:
            return
        profile = self.profiles.get(self.current_profile)
        if not profile:
            raise ValueError(f"sensitivity profile '{self.current_profile}' not found")
        ema.trigger_residual_threshold = profile.residual_threshold
        ema.trigger_uncertainty_threshold = profile.uncertainty_threshold
        estimator.process_noise = profile.process_noise
        estimator.measurement_noise = profile.measurement_noise


class AppConfig(BaseModel):
    window: WindowConfig = WindowConfig()
    estimator: EstimatorConfig = EstimatorConfig()
    permissions: PermissionsConfig = PermissionsConfig()
    ema: EmaConfig = EmaConfig()
    storage: StorageConfig = StorageConfig()
    service: ServiceConfig = ServiceConfig()
    sensitivity: Optional[SensitivityConfig] = None
    export: ExportConfig = ExportConfig()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        if path and path.exists():
            data = tomllib.loads(path.read_text())
            config = cls.model_validate(data)
        else:
            config = cls()
        config.apply_sensitivity()
        return config

    def ensure_storage_parent(self) -> None:
        self.storage.path.parent.mkdir(parents=True, exist_ok=True)
        self.export.output_dir.mkdir(parents=True, exist_ok=True)

    def apply_sensitivity(self) -> None:
        if self.sensitivity:
            self.sensitivity.apply(self.estimator, self.ema)
