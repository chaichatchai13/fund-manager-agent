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

    # Domain — mirrors THETAFLOW_DOMAIN in Caddyfile; used to determine secure cookie flag
    thetaflow_domain: str = "localhost"

    # Feature flags
    mock_schwab: bool = False

    # Auth
    # Plain text password OR bcrypt hash (starts with $2b$). Both accepted.
    thetaflow_password: str = ""
    # Used to sign JWTs — generate a strong random value for production:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "dev-secret-change-in-production"

    # App
    log_level: str = "INFO"
    environment: str = "development"

    # Twilio (SMS alerts + two-way agent)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""   # e.g. +15551234567
    alert_phone_number: str = ""   # your phone number to receive alerts

    # Brave Search API (research skill)
    brave_api_key: str = ""

    # SocialData.tools (social intel skill)
    socialdata_api_key: str = ""
    social_summary_language: str = "English"

    # PWA Push (VAPID keys — generate with: npx web-push generate-vapid-keys)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@thetaflow.app"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
