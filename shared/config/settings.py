"""Base application settings using pydantic-settings."""
from __future__ import annotations

from pydantic import Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]


class BaseAppSettings(BaseSettings):
    """Base settings shared by all services.

    Values are loaded from environment variables (case-insensitive).
    Supports loading from .env file if present.
    """
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/iprs",
        description="PostgreSQL connection string",
    )

    # Service metadata
    service_name: str = Field(default="iprs-service")
    service_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    # Worker configuration
    worker_id: str = Field(
        default="worker-1",
        description="Worker instance identifier for distributed processing",
    )
    worker_lease_seconds: int = Field(
        default=60,
        description="Task lease duration in seconds",
    )

    # Run orchestration
    run_task_hash_mod: int = Field(
        default=1,
        description="Number of hash buckets for task sharding",
    )
    run_task_max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts for failed tasks",
    )

    # Data paths
    positions_snapshot_path: str = Field(
        default="demo/inputs/positions.json",
        description="Default path to positions snapshot file",
    )

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"
