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
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"
    
    # Internal routing
    EXISTING_DJANGO_WEBHOOK_URL: str = "http://127.0.0.1:8000/whatsapp/webhook/"
    
    # Database (Unified with Django IPO Utility db.sqlite3)
    DATABASE_URL: str = f"mysql+aiomysql://hostingerdb:Hostingerdb%401234@46.202.162.106:3306/IPOutility"
    
    
    # Server ports
    HOST: str = "0.0.0.0"
    PORT: int = 8005

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
