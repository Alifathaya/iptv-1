"""Configuration from environment variables."""
import os

API_KEY: str = os.getenv("API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
OPENAI_TIMEOUT_SECONDS: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS",
        "https://alifathaya.github.io,capacitor://localhost,https://localhost,http://localhost:8765",
    ).split(",") if o.strip()
]
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
