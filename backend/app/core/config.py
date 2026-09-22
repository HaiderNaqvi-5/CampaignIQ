from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_ENV: str = "development"
    APP_NAME: str = "CampaignIQ"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/campaigniq_db"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/campaigniq_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Auth
    JWT_SECRET: str = "campaigniq_development_secret_key_change_in_production_32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 1440

    # CampaignIQ authentication and integrations (credentials supplied per environment)
    GOOGLE_CLIENT_ID: str = ""
    OTP_EXPIRY_MINUTES: int = 10
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_FROM_ADDRESS: str = ""
    OTP_SMTP_HOST: str = ""
    OTP_SMTP_PORT: int = 587
    OTP_SMTP_USERNAME: str = ""
    OTP_SMTP_PASSWORD: str = ""
    CAMPAIGN_EMAIL_FROM_ADDRESS: str = ""
    CAMPAIGN_SMTP_HOST: str = ""
    CAMPAIGN_SMTP_PORT: int = 587
    CAMPAIGN_SMTP_USERNAME: str = ""
    CAMPAIGN_SMTP_PASSWORD: str = ""
    HUBSPOT_CLIENT_ID: str = ""
    HUBSPOT_CLIENT_SECRET: str = ""
    HUBSPOT_REDIRECT_URI: str = "http://localhost:8000/api/hubspot/callback"
    HUBSPOT_SCOPES: str = "crm.objects.contacts.read crm.objects.contacts.write crm.lists.read"
    HUBSPOT_API_VERSION: str = "2026-09"
    TOKEN_ENCRYPTION_KEY: str = ""

    # AI & Embeddings
# AI & Embeddings
# Supported embedding providers: openai, gemini
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_API_KEY: str = "mock-key"
    EMBEDDING_DIMENSION: int = 1536

# Supported LLM providers: openai, groq
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-20b"

# Kept for OpenAI/backward compatibility
    LLM_API_KEY: str = "mock-key"

# Groq failover key pool
    GROQ_API_KEY_1: str = ""
    GROQ_API_KEY_2: str = ""
    GROQ_API_KEY_3: str = ""

# Number of attempts allowed per Groq key
    LLM_RETRIES_PER_KEY: int = 2
    # Crawler Operational Limits (PRD Section 11)
    MAX_PAGES_PER_BOT: int = 50
    MAX_CRAWL_DEPTH: int = 4
    HTTP_TIMEOUT_SECONDS: int = 15
    BROWSER_NAV_TIMEOUT_SECONDS: int = 30
    MAX_RESPONSE_BYTES: int = 5_000_000
    MAX_REDIRECTS: int = 5
    CRAWL_CONCURRENCY_PER_BOT: int = 5
    HTTP_RETRIES: int = 2
    PLAYWRIGHT_RETRIES: int = 1
    EMBEDDING_RETRIES: int = 3

    # RAG Retrieval Limits
    DEFAULT_TOP_K: int = 8
    MAX_TOP_K: int = 10
    MIN_SIMILARITY_THRESHOLD: float = 0.50
    TARGET_CHUNK_TOKENS: int = 600
    MAX_CHUNK_TOKENS: int = 1000
    CHUNK_OVERLAP_TOKENS: int = 100
    MAX_USER_MESSAGE_CHARS: int = 4000

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
