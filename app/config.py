from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "YouTube Comment Assistant"
    app_env: str = "development"

    database_url: str

    auto_publish: bool = False
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    frontend_url: str = "http://127.0.0.1:5174"
    session_secret: str
    token_encryption_key: str
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )
    
@lru_cache
def get_settings() -> "Settings":
    return Settings()
