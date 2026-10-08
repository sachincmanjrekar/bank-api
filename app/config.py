from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file).

    Defaults are for local development. In Docker/AWS we override them
    with real environment variables instead of changing code.
    """

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Bank API"
    database_url: str = "sqlite:///./bank.db"


settings = Settings()
