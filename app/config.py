from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Imgre Multi-Agent Automation"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/imgre_db",
        description="Async PostgreSQL Connection URL"
    )

    # Gemini & Imagen Configuration
    GEMINI_API_KEY: str = Field(
        default="",
        description="API key for Gemini models"
    )
    DEFAULT_GEMINI_MODEL: str = "models/gemini-3.5-flash"
    IMAGEN_MODEL: str = "imagen-3.0-generate-002"
    IMAGE_GEN_RESOLUTION: str = "1024x1024"

    # Scheduler Configuration
    SCHEDULER_CRON_HOUR: int = 9
    SCHEDULER_CRON_MINUTE: int = 0

# Instantiate settings to be imported across the application
settings = Settings()
