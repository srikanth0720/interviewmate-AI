import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Locate the project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root
load_dotenv(BASE_DIR / ".env", override=True)


@dataclass
class Settings:

    gnani_api_key: str = os.getenv("GNANI_API_KEY", "")

    stt_url: str = os.getenv(
        "GNANI_STT_URL",
        "https://api.vachana.ai/stt/v3"
    )

    tts_url: str = os.getenv(
        "GNANI_TTS_URL",
        "https://api.vachana.ai/api/v1/tts/inference"
    )

    stt_model: str = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")

    tts_model: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")

    tts_voice: str = os.getenv("GNANI_TTS_VOICE", "Nalini")

    evon_api_url: str = os.getenv("EVON_API_URL", "")

    evon_api_key: str = os.getenv("EVON_API_KEY", "")

    evon_model: str = os.getenv("EVON_MODEL", "evon")

    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./interviewmate.db"
    )

    max_audio_seconds: int = int(
        os.getenv("MAX_AUDIO_SECONDS", "30")
    )


settings = Settings()