"""
Configuration settings for Spectre-CLI.
Handles environment variables, defaults, and runtime overrides.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class SpectreConfig:
    # Model & Inference (Gemma-2 via Ollama)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma2:9b")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    offline_mode: bool = os.getenv("SPECTRE_OFFLINE", "false").lower() in ("1", "true", "yes")

    # Memory Layer (MongoDB Atlas Vector Search)
    mongodb_uri: Optional[str] = os.getenv("MONGODB_URI", "")
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "spectre_vault")
    mongodb_collection_name: str = os.getenv("MONGODB_COLLECTION_NAME", "resurrected_artifacts")
    mongodb_index_name: str = os.getenv("MONGODB_INDEX_NAME", "vector_index")

    # Observability (Sentry Agent Tracing)
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN", "")
    sentry_environment: str = os.getenv("SENTRY_ENVIRONMENT", "seance-production")
    sentry_traces_sample_rate: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))

    # Speech Synthesizer (ElevenLabs TTS)
    elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
    elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

    # Mastra Orchestration Bridge
    mastra_server_url: str = os.getenv("MASTRA_SERVER_URL", "http://localhost:4111")

    # Local Cache / Persistence
    cache_dir: Path = Path(".spectre_cache")

    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)


config = SpectreConfig()
