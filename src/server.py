"""MCP server setup and configuration."""

from datetime import datetime, timezone
from typing import Any

from fastmcp import FastMCP

from .config import settings
from .logging_config import get_logger
from .tools.geocoding import geocode_tool, reverse_geocode_tool
from .tools.routing import calculate_route_tool, compare_routes_tool
from .tools.search import find_schools_nearby_tool, search_nearby_tool

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("openstreetmap-mcp")


# ============================================================================
# Geocoding Tools
# ============================================================================


@mcp.tool()
async def geocode(address: str, limit: int = 1) -> str:
    """
    Convert an address to geographic coordinates.

    Args:
        address: The address to geocode (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
        limit: Maximum number of results to return (1-10, default: 1)

    Returns:
        Markdown formatted geocoding results with coordinates and location information
    """
    return await geocode_tool(address, limit)


@mcp.tool()
async def reverse_geocode(lat: float, lon: float) -> str:
    """
    Convert geographic coordinates to an address.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Markdown formatted address and location information
    """
    return await reverse_geocode_tool(lat, lon)


# ============================================================================
# Search Tools
# ============================================================================


@mcp.tool()
async def search_nearby(
    location: str,
    category: str,
    radius_meters: int = 1000,
    limit: int = 10
) -> str:
    """
    Search for places near a location.

    Args:
        location: Location in "lat,lon" format (e.g., "40.7128,-74.0060")
        category: Type of place to search for (e.g., "restaurant", "hospital", "park")
        radius_meters: Search radius in meters (100-5000, default: 1000)
        limit: Maximum results (1-100, default: 10)

    Returns:
        Markdown formatted search results with nearby places
    """
    return await search_nearby_tool(location, category, radius_meters, limit)


@mcp.tool()
async def find_schools_nearby(
    location: str,
    school_type: str = "all",
    radius_meters: int = 2000,
    limit: int = 10
) -> str:
    """
    Find schools near a location with type filtering.

    Args:
        location: Location in "lat,lon" format (e.g., "40.7128,-74.0060")
        school_type: Type of school - "primary", "secondary", "university", "kindergarten", or "all" (default: "all")
        radius_meters: Search radius in meters (100-5000, default: 2000)
        limit: Maximum results (1-100, default: 10)

    Returns:
        Markdown formatted school search results
    """
    return await find_schools_nearby_tool(location, school_type, radius_meters, limit)


# ============================================================================
# Routing Tools
# ============================================================================


@mcp.tool()
async def calculate_route(
    origin: str,
    destination: str,
    mode: str = "driving",
    include_steps: bool = True
) -> str:
    """
    Calculate route between two locations.

    Args:
        origin: Origin location in "lat,lon" format (e.g., "40.7128,-74.0060")
        destination: Destination location in "lat,lon" format
        mode: Transportation mode - "driving", "cycling", "walking", or "transit" (default: "driving")
        include_steps: Include turn-by-turn directions (default: True)

    Returns:
        Markdown formatted route with distance, duration, and optional turn-by-turn directions
    """
    return await calculate_route_tool(origin, destination, mode, include_steps)


@mcp.tool()
async def compare_routes(
    origin: str,
    destination: str,
    include_transit: bool = True
) -> str:
    """
    Compare all transportation modes between two locations.

    Args:
        origin: Origin location in "lat,lon" format (e.g., "40.7128,-74.0060")
        destination: Destination location in "lat,lon" format
        include_transit: Include public transit comparison (default: True)

    Returns:
        Markdown formatted comparison table showing all transportation modes
    """
    return await compare_routes_tool(origin, destination, include_transit)


# Export mcp for use in main.py
__all__ = ["mcp"]
