"""Configuration management for the bot."""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8459447990:AAE9yPVgoi6MicC1xa5Lc8SzhVT51k6y-yQ")
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "dtc_job_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "Fayez")
    
    # Database URL
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    
    # Telegram Channels
    SERVICES_CHANNEL_ID: int = int(os.getenv("SERVICES_CHANNEL_ID", "-1003482966379"))
    REQUESTS_CHANNEL_ID: int = int(os.getenv("REQUESTS_CHANNEL_ID", "-1003482966379"))
    
    # Admin Group for Approvals
    ADMIN_GROUP_ID: int = int(os.getenv("ADMIN_GROUP_ID", "-1003482966379"))
    
    # Web Dashboard
    WEB_DASHBOARD_EMAIL: str = os.getenv("WEB_DASHBOARD_EMAIL", "admin@dtcjob.com")
    WEB_DASHBOARD_PASSWORD: str = os.getenv("WEB_DASHBOARD_PASSWORD", "admin123")
    WEB_DASHBOARD_SECRET_KEY: str = os.getenv("WEB_DASHBOARD_SECRET_KEY", "your-secret-key-change-this-in-production")
    WEB_DASHBOARD_PORT: int = int(os.getenv("WEB_DASHBOARD_PORT", "8000"))

    
    # Admin
    ADMIN_USER_IDS: List[int] = [
        int(uid.strip()) for uid in os.getenv("ADMIN_USER_IDS", "5049749756").split(",") if uid.strip()
    ]
    
    # Verification
    VERIFICATION_CODE_EXPIRY_MINUTES: int = int(os.getenv("VERIFICATION_CODE_EXPIRY_MINUTES", "10"))
    
    # Service Limits
    MAX_DESCRIPTION_LENGTH: int = 3000  # Telegram message limit is 4096, leaving room for formatting
    MAX_TITLE_LENGTH: int = 200


config = Config()

