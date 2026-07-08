from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # 🖥️ SERVER CONFIGURATION
    APP_NAME: str = "LogiSecure AI - Core System"
    APP_VERSION: str = "0.1.0"
    BACKEND_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 🌐 CORS: comma-separated list of allowed origins.
    # "*" is fine for the hackathon demo; lock this down to the real frontend
    # origin (e.g. "http://localhost:5173") before any client deployment.
    CORS_ALLOW_ORIGINS: str = "*"

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

def get_cors_origins() -> list[str]:
    """Parse CORS_ALLOW_ORIGINS ('*' or comma-separated URLs) into the list CORSMiddleware expects."""
    raw = get_settings().CORS_ALLOW_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

