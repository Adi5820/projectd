from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection string")
    MONGODB_DB_NAME: str = Field(default="agentic_ads", description="MongoDB database name")

    # AI API Keys
    GOOGLE_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_API_KEY: str = Field(default="", description="Gemini API key alias")
    TOGETHER_API_KEY: str = Field(default="", description="Together AI API key")
    STABILITY_API_KEY: str = Field(default="", description="Stability AI API key (optional)")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash", description="Gemini model identifier")
    FLUX_MODEL: str = Field(default="black-forest-labs/FLUX.1-schnell", description="FLUX model identifier")

    # Server Configuration
    APP_HOST: str = Field(default="0.0.0.0", description="FastAPI host")
    APP_PORT: int = Field(default=8000, description="FastAPI port")

    # Media and Storage
    BASE_DIR: Path = Field(default=Path(__file__).resolve().parent.parent, description="Root project workspace directory")
    MEDIA_STORAGE_PATH: str = Field(default="./media", description="Local media storage directory")
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_db", description="ChromaDB persistence directory")

    # Security & Limits
    SECRET_KEY: str = Field(
        default="agentic-ads-secret-key-change-in-production-2026",
        description="Application secret key for auth and tokens",
    )
    MAX_GENERATIONS_PER_HOUR: int = Field(default=20, description="Rate limit for AI asset generations per hour")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Maximum file upload size in MB")
    MAX_VIDEO_DURATION_SECONDS: int = Field(default=60, description="Maximum ad video duration in seconds")
    DEFAULT_VIDEO_FPS: int = Field(default=24, description="Default video framerate")

    # Voice Narration
    EDGE_TTS_VOICE: str = Field(default="en-US-AriaNeural", description="Default Edge-TTS neural voice")

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    # Lowercase aliases for convenience
    @property
    def mongodb_url(self) -> str:
        return self.MONGODB_URL

    @property
    def mongodb_db_name(self) -> str:
        return self.MONGODB_DB_NAME

    @property
    def google_api_key(self) -> str:
        return self.GOOGLE_API_KEY

    @property
    def together_api_key(self) -> str:
        return self.TOGETHER_API_KEY

    @property
    def stability_api_key(self) -> str:
        return self.STABILITY_API_KEY

    @property
    def app_host(self) -> str:
        return self.APP_HOST

    @property
    def app_port(self) -> int:
        return self.APP_PORT

    @property
    def media_storage_path(self) -> str:
        return self.MEDIA_STORAGE_PATH

    @property
    def chroma_persist_dir(self) -> str:
        return self.CHROMA_PERSIST_DIR

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def max_generations_per_hour(self) -> int:
        return self.MAX_GENERATIONS_PER_HOUR

    @property
    def max_upload_size_mb(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB

    @property
    def max_video_duration_seconds(self) -> int:
        return self.MAX_VIDEO_DURATION_SECONDS

    @property
    def edge_tts_voice(self) -> str:
        return self.EDGE_TTS_VOICE

    @property
    def CHROMA_PERSIST_DIRECTORY(self) -> str:
        return self.CHROMA_PERSIST_DIR

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()
