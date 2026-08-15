"""Configuration from environment variables."""

import os

API_KEY: str = os.getenv("API_KEY", "")
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_PIXELS: int = int(os.getenv("MAX_PIXELS", str(4096 * 4096)))
TILE_SIZE: int = int(os.getenv("TILE_SIZE", "512"))
TILE_PAD: int = int(os.getenv("TILE_PAD", "10"))
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "https://alifathaya.github.io,http://localhost:8765,http://localhost:8080,capacitor://localhost,https://localhost",
    ).split(",")
    if o.strip()
]

MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
