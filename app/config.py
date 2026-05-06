from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "BIMSA-CLASS API"
    APP_ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8001

    DATABASE_URL: str = "postgresql://ddclass:change-me@127.0.0.1:5432/ddclass"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    UPLOADS_DIR: str = ""

    BACKEND_CORS_ORIGINS_RAW: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5174,http://127.0.0.1:5174",
        alias="BACKEND_CORS_ORIGINS",
    )
    TRUSTED_HOSTS_RAW: str = Field(
        default="localhost,127.0.0.1",
        alias="TRUSTED_HOSTS",
    )

    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "ChangeMe123!"
    INIT_ADMIN_REAL_NAME: str = "System Administrator"
    INIT_DEFAULT_DATA: bool = True
    ALLOW_PUBLIC_REGISTRATION: bool = False

    GUNICORN_WORKERS: int = 3
    LOG_LEVEL: str = "info"
    ENABLE_LLM_GRADING_WORKER: bool = True
    LLM_GRADING_WORKER_LEADER: bool = False
    LLM_GRADING_WORKER_POLL_SECONDS: int = 2
    LLM_GRADING_TASK_STALE_SECONDS: int = 600
    DEFAULT_ESTIMATED_IMAGE_TOKENS: int = 850

    # Optional: first-boot LLM preset + vision/text validation + demo course wiring (see app.bootstrap.seed_initial_llm_deployment_bundle).
    INIT_LLM_PRESET_NAME: str = "deployment-primary"
    INIT_LLM_BASE_URL: str = ""
    INIT_LLM_API_KEY: str = ""
    INIT_LLM_MODEL_NAME: str = ""
    INIT_LLM_CONNECT_TIMEOUT_SECONDS: int = 10
    INIT_LLM_READ_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("BACKEND_CORS_ORIGINS_RAW", "TRUSTED_HOSTS_RAW", mode="before")
    @classmethod
    def normalize_csv_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        raise TypeError("Expected a comma-separated string or a list.")

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        return self._split_csv(self.BACKEND_CORS_ORIGINS_RAW)

    @property
    def TRUSTED_HOSTS(self) -> list[str]:
        return self._split_csv(self.TRUSTED_HOSTS_RAW)


settings = Settings()
