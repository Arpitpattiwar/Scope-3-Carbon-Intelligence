from typing import Optional

from pydantic_settings import BaseSettings


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
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    AI_ESTIMATION_ENABLED: bool = False
    AI_MODEL_PATH: Optional[str] = None
    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_SERVICE_HOSTPORT: Optional[str] = None
    ML_SERVICE_TIMEOUT_SECONDS: float = 10.0

    # Set to true to wipe and re-seed on startup. Reset to false after first seed.
    FORCE_RESEED: bool = False

    @property
    def cors_origins(self) -> list[str]:
        configured = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL not in configured:
            configured.append(self.FRONTEND_URL)
        return configured

    @property
    def ml_service_base_url(self) -> str:
        if self.ML_SERVICE_HOSTPORT:
            return f"http://{self.ML_SERVICE_HOSTPORT.strip().rstrip('/')}"
        return self.ML_SERVICE_URL.strip().rstrip("/")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
