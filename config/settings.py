"""Centralized environment-based application settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime settings shared by the Flask application and local scripts."""

    def __init__(self) -> None:
        self.environment = os.getenv("FLASK_ENV", "development").lower()
        self.debug = self.environment == "development"
        self.secret_key = os.getenv("SESSION_SECRET", "")
        self.firebase_required = os.getenv("FIREBASE_REQUIRED", "false").lower() == "true"
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "5000"))
        self._validate()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def _validate(self) -> None:
        """Fail fast for settings that would make a production deployment unsafe."""
        if self.is_production and not self.secret_key:
            raise RuntimeError("SESSION_SECRET must be set when FLASK_ENV=production")
        if self.firebase_required and not os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_KEY is required when FIREBASE_REQUIRED=true")

    def as_flask_config(self) -> dict[str, object]:
        """Return settings in Flask's configuration format."""
        return {
            "SECRET_KEY": self.secret_key or "local-development-secret",
            "ENV": self.environment,
            "DEBUG": self.debug,
        }


settings = Settings()

# Keep this import useful to deployment tooling without exposing its contents.
ENV_FILE = Path(os.getenv("ENV_FILE", ".env"))
