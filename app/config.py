from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file).

    Defaults are for local development. In Docker/AWS we override them
    with real environment variables instead of changing code.
    """

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Bank API"
    database_url: str = "sqlite:///./bank.db"
    # True for Aurora DSQL: instead of a password, each new connection gets a
    # short-lived IAM auth token generated from the caller's AWS credentials.
    database_iam_auth: bool = False

    # Used to sign JWT tokens. This default is for local development only;
    # on AWS it is replaced by a long random SECRET_KEY environment variable.
    secret_key: str = "dev-only-secret-key-change-me-in-production-0123456789"
    access_token_expire_minutes: int = 30


settings = Settings()
