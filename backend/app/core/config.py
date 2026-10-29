from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NammaNexus AI API"
    app_version: str = "1.0.0"
    environment: str = "development"

    llm_provider: str = "groq"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"

    # NammaServe AI Intent Cache settings
    intent_cache_enabled: bool = True
    intent_cache_ttl_seconds: int = 3600
    intent_cache_max_size: int = 1000

    database_url: str

    resend_api_key: str | None = None
    resend_from_email: str = "NammaNexus AI <notifications@nammanexus.ai>"

    default_official_email: str = "civic.authority@example.com"
    official_email_mapping: dict[str, str] = {
        "BBMP:Road Infrastructure": "bbmp.road@example.com",
        "BBMP:Solid Waste Management": "bbmp.garbage@example.com",
        "BWSSB:Water Supply Maintenance": "bwssb.water@example.com",
        "BBMP:Storm Water Drains": "bbmp.drains@example.com",
        "BESCOM:Street Lighting": "bescom.light@example.com",
        "BBMP:Tree Management": "bbmp.tree@example.com",
    }

    instagram_access_token: str | None = None
    instagram_account_id: str | None = None
    public_base_url: str = "https://api.nammanexus.ai"

    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    google_places_api_key: str | None = None
    geoapify_api_key: str | None = None
    foursquare_api_key: str | None = None
    default_search_radius_km: float = 5.0
    max_search_radius_km: float = 25.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
