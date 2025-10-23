"""Configuration management using pydantic-settings."""

from enum import Enum
from typing import Annotated

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Valid log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheTTL:
    """Cache Time-To-Live constants in seconds."""

    GEOCODE = 86400  # 24 hours - addresses don't change frequently
    POI = 3600  # 1 hour - POI data is relatively stable
    ROUTE = 300  # 5 minutes - routes can vary with traffic
    TRANSIT = 300  # 5 minutes - transit schedules need freshness


class RateLimits:
    """Rate limiting configuration for external APIs."""

    # Nominatim requires maximum 1 request per second
    NOMINATIM_REQUESTS_PER_SECOND = 1.0


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by environment variables.
    URL validation ensures endpoints are valid HTTP/HTTPS URLs.
    """

    # API Endpoints
    nominatim_url: HttpUrl = Field(
        default="https://nominatim.openstreetmap.org",
        description="Nominatim geocoding API endpoint",
    )
    overpass_url: HttpUrl = Field(
        default="https://overpass-api.de/api/interpreter",
        description="Overpass API endpoint for POI queries",
    )
    osrm_url: HttpUrl = Field(
        default="https://router.project-osrm.org",
        description="OSRM routing API endpoint",
    )
    transitland_url: HttpUrl = Field(
        default="https://transit.land/api/v2",
        description="Transit.land API endpoint for public transit routing",
    )

    # Server Configuration
    port: Annotated[int, Field(ge=1, le=65535)] = Field(
        default=8000,
        description="Server port number (1-65535)",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Required by OSM services
    user_agent: str = Field(
        default="openstreetmap-mcp/0.1.0",
        description="User-Agent header for OSM API requests",
        min_length=1,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Ensure user_agent is not empty."""
        if not v or not v.strip():
            raise ValueError("user_agent must not be empty")
        return v.strip()

    def validate_config(self) -> None:
        """
        Validate configuration on startup.

        Raises:
            ValueError: If configuration is invalid
        """
        # Convert HttpUrl to string for logging
        urls = {
            "nominatim": str(self.nominatim_url),
            "overpass": str(self.overpass_url),
            "osrm": str(self.osrm_url),
            "transitland": str(self.transitland_url),
        }

        # Basic validation already handled by Pydantic
        # This method can be extended for more complex validation
        for name, url in urls.items():
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"{name}_url must be a valid HTTP/HTTPS URL")


# Global settings instance
settings = Settings()

# Validate configuration on import
try:
    settings.validate_config()
except Exception as e:
    raise RuntimeError(f"Configuration validation failed: {e}") from e


__all__ = ["settings", "Settings", "CacheTTL", "RateLimits", "LogLevel"]
