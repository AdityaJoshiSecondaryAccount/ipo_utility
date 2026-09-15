import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = "1287337667797572"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "1001693916214003"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "ADwealth_WA_Webhook_2026"
    WHATSAPP_APP_SECRET: str = "arham123321"
    WHATSAPP_API_VERSION: str = "v21.0"
    
    # Internal routing
    EXISTING_DJANGO_WEBHOOK_URL: str = "http://127.0.0.1:8000/whatsapp/webhook/"
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/inbox.db"
    
    # Server ports
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
