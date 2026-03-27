import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_ENV: str = "development"
    DEBUG: bool = True
    DEFAULT_AGENT_COUNT: int = 10
    CONCURRENT_AGENT_LIMIT: int = 50
    DEFAULT_CLIENT_ID: str = "CLIENT_A"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: str = "0"
    
    @property
    def redis_full_url(self) -> str:
        return f"{self.REDIS_URL}/{self.REDIS_DB}"

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None

    # LLM Settings
    STRATEGIC_LLM_MODEL: str = "gpt-4o-mini"
    AGENT_LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: Optional[str] = None
    
    # Zep Settings
    ZEP_API_KEY: Optional[str] = None
    
    # Security
    API_KEY: Optional[str] = None
    ALLOWED_ORIGINS: str = "*" # Comma-separated list
    
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # Paths
    AURA_HOME: str = os.path.expanduser("~/.aura")
    PERSONAS_FILE: str = os.path.join(os.path.expanduser("~/.aura"), "personas.json")
    CONFIG_PATH: str = os.path.expanduser("~/.aura/aura.cfg")

    model_config = SettingsConfigDict(
        env_file=os.path.expanduser("~/.aura/aura.cfg") if os.path.exists(os.path.expanduser("~/.aura/aura.cfg")) else ".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
