"""FastMCP server entry point for OpenStreetMap MCP."""

import signal
import sys

from src.config import settings, TransportType
from src.logging_config import setup_logging, get_logger
from src.server import mcp

# Setup structured logging
setup_logging(settings.log_level)
logger = get_logger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, closing server...")
    sys.exit(0)


def main():
    """Run the FastMCP server."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(
        "Starting OpenStreetMap MCP server",
        extra={
            "transport": settings.transport.value,
            "host": settings.host if settings.transport == TransportType.HTTP else "N/A",
            "port": settings.port if settings.transport == TransportType.HTTP else "N/A",
            "path": settings.mcp_path if settings.transport == TransportType.HTTP else "N/A",
            "nominatim_url": settings.nominatim_url,
            "log_level": settings.log_level,
        },
    )

    # Run the FastMCP server with configured transport
    if settings.transport == TransportType.HTTP:
        logger.info(
            f"Starting HTTP streamable transport on {settings.host}:{settings.port}{settings.mcp_path}"
        )
        mcp.run(
            transport="http",
            host=settings.host,
            port=settings.port,
            path=settings.mcp_path,
        )
    else:
        logger.info("Starting stdio transport")
        mcp.run(
            transport="stdio",
        )


if __name__ == "__main__":
    main()
