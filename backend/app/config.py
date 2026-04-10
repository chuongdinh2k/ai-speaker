from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    openai_api_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    audio_storage_path: str = "/app/audio"
    rag_top_k: int = 5
    rag_recent_window: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
