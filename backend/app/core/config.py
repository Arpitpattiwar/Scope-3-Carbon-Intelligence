from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://scope3:scope3pass@localhost:5432/scope3db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Phase 2: AI estimation toggle (set to True when models are ready)
    AI_ESTIMATION_ENABLED: bool = False
    AI_MODEL_PATH: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
