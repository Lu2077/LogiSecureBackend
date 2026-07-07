from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # 🖥️ SERVER CONFIGURATION
    BACKEND_ENV: str = "development"
    PORT: int = 8000
    
    # 🛰️ API CREDENTIALS (Assigned as empty strings by default to prevent crashes)
    AISSTREAM_API_KEY: str = ""
    OPENSKY_USERNAME: str = ""
    OPENSKY_PASSWORD: str = ""
    
    # 🤖 AI ENGINE & HARDWARE (Flexible configurations for the team)
    USE_AMD_ROCM: bool = False  # Changed to False by default so that standard team laptops do not fail to start up.
    LOCAL_MODEL_PATH: str = "./models/gemma-4-e4b.gguf" # Suggested route aligned with the Google Gemma bonus
    FIREWORKS_API_KEY: str = ""
    
    # Pydantic configuration for reading the local .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignores extraneous variables in the .env file without throwing errors.
    )

# RAM cache to optimize local server performance
@lru_cache()
def get_settings():
    return Settings()

