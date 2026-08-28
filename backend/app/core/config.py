import os
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "JEE Doubt Resolution & Companion Studio"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_TTL_SECONDS: int = 86400  # 24 hours

    # Qdrant Vector Store (Cloud & Local)
    QDRANT_URL: Optional[str] = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "jee_knowledge_base"

    # Groq & Gemini API Configurations
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    
    # Active Model Configurations
    GROQ_ROUTER_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_CRITIC_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MATH_MODEL: str = "gemini-3.6-flash"

    # JEE Guardrail Settings
    STRICT_SYLLABUS_ENFORCEMENT: bool = True
    MAX_HINT_TIER: int = 3
    PROHIBIT_DIRECT_ANSWERS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
