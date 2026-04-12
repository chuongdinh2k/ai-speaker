from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    redis_url: str = "redis://localhost:6379"
    openai_api_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    rag_top_k: int = 5
    rag_recent_window: int = 10

    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    s3_region: str
    s3_presigned_url_expiry: int = 3600

settings = Settings()
