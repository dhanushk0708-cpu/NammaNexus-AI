from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NammaNexus AI API"
    app_version: str = "1.0.0"
    environment: str = "development"

    gemini_api_key: str | None = None
    groq_api_key: str | None = None

    database_url: str

    resend_api_key: str | None = None

    instagram_access_token: str | None = None
    instagram_account_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
