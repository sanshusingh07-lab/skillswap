import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Render injects SECRET_KEY via environment; locally falls back to dev key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Render provides DATABASE_URL for PostgreSQL (free tier)
    # Locally falls back to SQLite so no setup is needed
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # Fix Render's legacy postgres:// prefix (SQLAlchemy requires postgresql://)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{BASE_DIR / 'skillswap.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,          # Reconnect on stale connections
        'pool_recycle': 300,            # Recycle connections every 5 minutes
    }

    # File upload storage
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload

    # Request timeouts
    REQUEST_TIMEOUT = 12
