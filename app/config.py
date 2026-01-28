import os
from dataclasses import dataclass


def _normalize_database_url(url: str) -> str:
    """
    Render (and other providers) sometimes provide postgres:// URLs.
    SQLAlchemy prefers postgresql://.
    Also, many hosted Postgres require SSL; we append sslmode=require if missing.
    """
    if not url:
        return ""

    # Normalize scheme for SQLAlchemy
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Add sslmode=require if not present
    # (Render Postgres commonly requires SSL/TLS.)  :contentReference[oaicite:4]{index=4}
    if "sslmode=" not in url:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}sslmode=require"

    return url


@dataclass
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Default local dev DB (you can override with DATABASE_URL env var)
    SQLALCHEMY_DATABASE_URI: str = _normalize_database_url(
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/franklin_planner")
    )

    # UI preferences
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "America/New_York")
