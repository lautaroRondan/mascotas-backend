from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60 * 24  # 1 día
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()