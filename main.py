"""FastMCP server entry point for OpenStreetMap MCP."""

import signal
import sys

from src.config import settings
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
            "port": settings.port,
            "nominatim_url": settings.nominatim_url,
            "log_level": settings.log_level,
        },
    )

    # Run the FastMCP server
    mcp.run(
        transport="stdio",  # MCP protocol uses stdio by default
    )


if __name__ == "__main__":
    main()
