# backend/config.py
"""
Configuration management using pydantic-settings V2
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ============================================
    # AI Provider Configuration
    # ============================================
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    LLM_MODEL: str = Field(default="llama-3.1-8b-instant", description="LLM model")
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)
    LLM_MAX_TOKENS: int = Field(default=500, ge=1, le=4096)
    
    # ============================================
    # Server Configuration
    # ============================================
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000, ge=1, le=65535)
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/logisecure.log")
    
    # ============================================
    # CORS Configuration
    # ============================================
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8000"
    )
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
    
    # ============================================
    # Database Configuration
    # ============================================
    DATABASE_URL: Optional[str] = Field(default=None)
    POSTGRES_USER: str = Field(default="logisecure")
    POSTGRES_PASSWORD: str = Field(default="secure_password")
    POSTGRES_DB: str = Field(default="logisecure")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    
    @property
    def database_url_property(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # ============================================
    # Feature Flags
    # ============================================
    USE_MOCK_DATA: bool = Field(default=True)
    ENABLE_AMD_ROCM: bool = Field(default=False)
    ENABLE_WEBSOCKET: bool = Field(default=True)
    
    # ============================================
    # AI Processing Settings
    # ============================================
    CONFIDENCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)
    ENABLE_CONTEXT_FILTERING: bool = Field(default=True)
    
    # ============================================
    # Validators
    # ============================================
    @field_validator("GROQ_API_KEY")
    @classmethod
    def validate_api_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError("GROQ_API_KEY must be set and at least 10 characters")
        return v
    
    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        if v < 0 or v > 1:
            raise ValueError("LLM_TEMPERATURE must be between 0 and 1")
        return v
    
    def display(self):
        return {
            "GROQ_API_KEY": f"{self.GROQ_API_KEY[:8]}..." if len(self.GROQ_API_KEY) > 8 else "***",
            "LLM_MODEL": self.LLM_MODEL,
            "LLM_TEMPERATURE": self.LLM_TEMPERATURE,
            "DEBUG": self.DEBUG,
            "CONFIDENCE_THRESHOLD": self.CONFIDENCE_THRESHOLD,
            "USE_MOCK_DATA": self.USE_MOCK_DATA,
        }


# ============================================
# Create singleton instance
# ============================================
settings = Settings()


if __name__ == "__main__":
    print("=" * 60)
    print("📋 LOGISECURE CONFIGURATION")
    print("=" * 60)
    for key, value in settings.display().items():
        print(f"  {key}: {value}")
    print("\n✅ Configuration loaded successfully!")