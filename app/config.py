from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Schwab API
    schwab_app_key: str = ""
    schwab_app_secret: str = ""
    schwab_callback_url: str = "https://127.0.0.1"
    schwab_token_path: str = "./schwab_token.json"

    # Anthropic
    anthropic_api_key: str = ""

    # PostgreSQL individual credentials (used to build DATABASE_URL)
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_pass: str = ""

    # Feature flags
    mock_schwab: bool = False

    # App
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
