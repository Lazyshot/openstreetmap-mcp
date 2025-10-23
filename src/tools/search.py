"""MCP tools for POI search."""

import logging
import re
from typing import Any

from src.clients.nominatim import NominatimClient, NominatimError
from src.clients.overpass import CATEGORY_MAPPING, OverpassClient, OverpassError

logger = logging.getLogger(__name__)


def parse_location(location: str) -> tuple[float, float]:
    """
    Parse location string as either address or coordinates.

    Args:
        location: Location string (address or "lat,lon" format)

    Returns:
        (lat, lon) tuple

    Raises:
        ValueError: If location format is invalid
    """
    # Check if it's in "lat,lon" format
    coord_pattern = r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$'
    match = re.match(coord_pattern, location.strip())

    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))

        if not -90 <= lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90 (got {lat})")
        if not -180 <= lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180 (got {lon})")

        return (lat, lon)

    # Otherwise, it's an address - geocode it
    raise ValueError("Location must be in 'lat,lon' format for search. Use geocode tool first to get coordinates from an address.")


async def search_nearby_tool(
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
        Markdown formatted search results

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate inputs
    if not location or not location.strip():
        raise ValueError("❌ Location cannot be empty")

    if not category or not category.strip():
        raise ValueError("❌ Category cannot be empty")

    if radius_meters < 100 or radius_meters > 5000:
        raise ValueError("❌ Radius must be between 100 and 5000 meters")

    if limit < 1 or limit > 100:
        raise ValueError("❌ Limit must be between 1 and 100")

    # Check if category is valid
    if category.lower() not in CATEGORY_MAPPING:
        available = ", ".join(sorted(CATEGORY_MAPPING.keys())[:20])
        return f"""## ❌ Unknown Category

Category '{category}' not found.

**Available categories (sample):**
{available}, ...

**Total categories available:** {len(CATEGORY_MAPPING)}

Use a valid category from the OpenStreetMap database."""

    try:
        # Parse location
        lat, lon = parse_location(location)

        # Search using Overpass
        client = OverpassClient()
        results = await client.search_pois(lat, lon, category, radius_meters, limit)
        await client.close()

        # Handle no results
        if not results:
            return f"""## 📍 No Results Found

No **{category}** places found within {radius_meters}m of ({lat}, {lon}).

Try:
- Increasing the search radius
- Using a different category
- Searching in a more populated area"""

        # Format results
        output = []
        output.append(f"# 🔍 Search Results: {category.title()}")
        output.append("")
        output.append(f"**Location:** {lat}, {lon}")
        output.append(f"**Radius:** {radius_meters}m")
        output.append(f"**Found:** {len(results)} place(s)")
        output.append("")

        for i, poi in enumerate(results, 1):
            output.append(f"## {i}. {poi.get('name', 'Unnamed')}")
            output.append("")
            output.append(f"**📍 Distance:** {poi.get('distance_meters')}m")
            output.append(f"**Coordinates:** {poi.get('lat')}, {poi.get('lon')}")

            # Type information
            amenity = poi.get('amenity') or poi.get('shop') or poi.get('leisure') or poi.get('tourism')
            if amenity:
                output.append(f"**Type:** {amenity}")

            # Address if available
            if poi.get('address'):
                output.append("")
                output.append("**Address:**")
                for key, value in poi.get('address', {}).items():
                    output.append(f"- {key.title()}: {value}")

            output.append("")

        return "\n".join(output)

    except ValueError as e:
        logger.error(f"Search validation error: {e}")
        return f"## ❌ Invalid Input\n\n{str(e)}\n\nPlease check your input and try again."

    except OverpassError as e:
        logger.error(f"Search API error: {e}")
        return f"## ❌ Search Error\n\n{str(e)}\n\nThe search service encountered an error. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected search error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


async def find_schools_nearby_tool(
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
    # Validate school type
    valid_types = ["all", "primary", "secondary", "university", "kindergarten"]
    if school_type.lower() not in valid_types:
        return f"""## ❌ Invalid School Type

School type '{school_type}' not recognized.

**Valid types:**
- primary
- secondary
- university
- kindergarten
- all (searches all types)"""

    # Map school types to categories
    if school_type.lower() == "all":
        category = "education"
    elif school_type.lower() in ["primary", "secondary"]:
        category = "school"
    else:
        category = school_type.lower()

    try:
        # Parse location
        lat, lon = parse_location(location)

        # Search using Overpass
        client = OverpassClient()
        results = await client.search_pois(lat, lon, category, radius_meters, limit * 2)  # Get more to filter
        await client.close()

        # Filter by school type if specified
        if school_type.lower() != "all":
            filtered = []
            for poi in results:
                tags = poi.get('tags', {})
                # Check amenity tag for school type
                if school_type.lower() == "primary":
                    if tags.get('school') == 'primary' or 'primary' in tags.get('name', '').lower():
                        filtered.append(poi)
                elif school_type.lower() == "secondary":
                    if tags.get('school') == 'secondary' or 'secondary' in tags.get('name', '').lower() or 'high school' in tags.get('name', '').lower():
                        filtered.append(poi)
                elif school_type.lower() == "kindergarten":
                    if tags.get('amenity') == 'kindergarten' or 'kindergarten' in tags.get('name', '').lower():
                        filtered.append(poi)
                else:
                    filtered.append(poi)
            results = filtered[:limit]

        # Handle no results
        if not results:
            return f"""## 🏫 No Schools Found

No **{school_type}** schools found within {radius_meters}m of ({lat}, {lon}).

Try:
- Increasing the search radius
- Using "all" to search all school types
- Searching in a different area"""

        # Format results
        output = []
        output.append(f"# 🏫 Schools Near Location")
        output.append("")
        output.append(f"**Location:** {lat}, {lon}")
        output.append(f"**School Type:** {school_type.title()}")
        output.append(f"**Radius:** {radius_meters}m")
        output.append(f"**Found:** {len(results)} school(s)")
        output.append("")

        for i, school in enumerate(results, 1):
            output.append(f"## {i}. {school.get('name', 'Unnamed School')}")
            output.append("")
            output.append(f"**📍 Distance:** {school.get('distance_meters')}m")
            output.append(f"**Coordinates:** {school.get('lat')}, {school.get('lon')}")

            # School type from tags
            tags = school.get('tags', {})
            if tags.get('amenity'):
                output.append(f"**Type:** {tags.get('amenity')}")
            if tags.get('school'):
                output.append(f"**Level:** {tags.get('school')}")

            # Address if available
            if school.get('address'):
                output.append("")
                output.append("**Address:**")
                for key, value in school.get('address', {}).items():
                    output.append(f"- {key.title()}: {value}")

            output.append("")

        return "\n".join(output)

    except ValueError as e:
        logger.error(f"School search validation error: {e}")
        return f"## ❌ Invalid Input\n\n{str(e)}\n\nPlease check your input and try again."

    except OverpassError as e:
        logger.error(f"School search API error: {e}")
        return f"## ❌ Search Error\n\n{str(e)}\n\nThe search service encountered an error. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected school search error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


__all__ = ["search_nearby_tool", "find_schools_nearby_tool"]
