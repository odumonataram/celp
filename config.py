"""
config.py
Application configuration for the CND Multilingual Translation & Learning Platform.

Why a class-based config: it lets us cleanly swap settings between development,
testing, and production without scattering os.environ.get() calls through the
codebase. Subclasses override only what differs.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # SECRET_KEY signs session cookies and CSRF tokens. In production this
    # MUST be set via an environment variable -- never commit a real secret.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-in-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'celp.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-WTF CSRF protection is on by default once Flask-WTF is initialised;
    # this just makes the expiry explicit instead of relying on a hidden default.
    WTF_CSRF_TIME_LIMIT = 3600

    # Where generated/uploaded audio and images are served from.
    AUDIO_UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "audio")
    IMAGE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "img")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload cap

    # Supported indigenous languages for the CND course. Kept here (not just in
    # the DB) so seed scripts and forms can reference a single source of truth.
    SUPPORTED_LANGUAGES = [
        {"code": "en", "name": "English"},
        {"code": "ijw", "name": "Ijaw"},
        {"code": "nem", "name": "Nembe"},
        {"code": "epi", "name": "Epie"},
        {"code": "ogb", "name": "Ogbia"},
    ]

    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    # In production, fail loudly if no real secret key was supplied.
    SECRET_KEY = os.environ.get("SECRET_KEY")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
