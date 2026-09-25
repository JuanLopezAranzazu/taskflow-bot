from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    BOT_MODE: str = "polling"  # "polling" o "webhook"
    WEBHOOK_BASE_URL: str = ""
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str = "secret"


settings = Settings()
