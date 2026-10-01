"""Konfigurasi backend — semua dari environment, tanpa secret di kode."""
import os

APP_NAME = "FotoRestore API"
API_PREFIX = "/api/v1"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "fotorestore")

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/tmp/prestore-p1/photorestore/storage")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MIN_DIMENSION = int(os.getenv("MIN_DIMENSION", "32"))
MAX_DIMENSION = int(os.getenv("MAX_DIMENSION", "4096"))

KEEP_EXIF = os.getenv("KEEP_EXIF", "false").lower() == "true"
TEMP_RETENTION_HOURS = int(os.getenv("TEMP_RETENTION_HOURS", "24"))
RESULT_RETENTION_DAYS = int(os.getenv("RESULT_RETENTION_DAYS", "30"))

JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "600"))
