from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://nagararaksha:nagararaksha@localhost:5432/nagararaksha"
    anthropic_api_key: str = ""
    upload_dir: str = "./uploads"
    max_photo_width: int = 960
    volunteer_cap: int = 5
    hotspot_min_reports: int = 2
    hotspot_radius_meters: float = 60.0
    cors_origins: list[str] = ["*"]
    staff_password: str = "changeme"
    staff_token_secret: str = "dev-secret-change-me"

    class Config:
        env_file = ".env"


settings = Settings()
