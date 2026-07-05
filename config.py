from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Define Var and data type
    BACKEND_ENV: str = "development"
    PORT: int = 8000
    
    AISSTREAM_API_KEY: str
    OPENSKY_USERNAME: str
    OPENSKY_PASSWORD: str
    
    USE_AMD_ROCM: bool = True
    LOCAL_MODEL_PATH: str
    FIREWORKS_API_KEY: str
    
    # Pydantic reads the file .env local
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Use caching to avoid reading the hard drive for every AI query
@lru_cache()
def get_settings():
    return Settings()

# Use Example:
# settings = get_settings()
# print(settings.AISSTREAM_API_KEY)

