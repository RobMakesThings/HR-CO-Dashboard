from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    oracle_dsn: str = "localhost:1521/FREEPDB1"
    oracle_co_user: str = "co"
    oracle_co_password: str = "letmein"
    oracle_hr_user: str = "hr"
    oracle_hr_password: str = "letmein"
    oracle_dash_user: str = "dashboard"
    oracle_dash_password: str = "dashboard_pwd"
    jwt_secret: str = "change-me-not"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    default_date_range_days: int = 365

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
