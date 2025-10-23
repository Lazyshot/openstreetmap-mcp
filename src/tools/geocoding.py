"""MCP tools for geocoding and reverse geocoding."""

import logging
from typing import Any

from src.clients.nominatim import BadRequestError, NominatimClient, NominatimError

logger = logging.getLogger(__name__)


def format_geocode_result(result: dict[str, Any], index: int = 1) -> str:
    """
    Format a single geocoding result as markdown.

    Args:
        result: Geocoding result dictionary
        index: Result number for display

    Returns:
        Markdown formatted result
    """
    output = []

    if index > 0:
        output.append(f"### Result {index}")

    # Display name
    display_name = result.get("display_name", "Unknown")
    output.append(f"**📍 {display_name}**")
    output.append("")

    # Coordinates
    lat = result.get("lat", 0)
    lon = result.get("lon", 0)
    output.append(f"**Coordinates:** {lat}, {lon}")

    # Type and class
    result_type = result.get("type")
    result_class = result.get("class")
    if result_type or result_class:
        output.append(f"**Type:** {result_class or 'N/A'} / {result_type or 'N/A'}")

    # Importance
    importance = result.get("importance")
    if importance:
        output.append(f"**Importance:** {importance:.3f}")

    # Address breakdown
    address = result.get("address")
    if address:
        output.append("")
        output.append("**Address Details:**")
        for key, value in address.items():
            formatted_key = key.replace("_", " ").title()
            output.append(f"- {formatted_key}: {value}")

    # Bounding box
    bbox = result.get("boundingbox")
    if bbox and len(bbox) == 4:
        output.append("")
        output.append(f"**Bounding Box:** [{bbox[0]}, {bbox[2]}] to [{bbox[1]}, {bbox[3]}]")

    return "\n".join(output)


def format_reverse_geocode_result(result: dict[str, Any]) -> str:
    """
    Format a reverse geocoding result as markdown.

    Args:
        result: Reverse geocoding result dictionary

    Returns:
        Markdown formatted result
    """
    output = []

    # Display name
    display_name = result.get("display_name", "Unknown")
    output.append(f"## 📍 {display_name}")
    output.append("")

    # Coordinates
    lat = result.get("lat", 0)
    lon = result.get("lon", 0)
    output.append(f"**Coordinates:** {lat}, {lon}")

    # Type
    result_type = result.get("type")
    result_class = result.get("class")
    if result_type or result_class:
        output.append(f"**Type:** {result_class or 'N/A'} / {result_type or 'N/A'}")

    # Address breakdown
    address = result.get("address")
    if address:
        output.append("")
        output.append("**Address Components:**")

        # Common fields in order of specificity
        field_order = [
            ("house_number", "House Number"),
            ("road", "Street"),
            ("neighbourhood", "Neighbourhood"),
            ("suburb", "Suburb"),
            ("city", "City"),
            ("county", "County"),
            ("state", "State"),
            ("postcode", "Postal Code"),
            ("country", "Country"),
            ("country_code", "Country Code"),
        ]

        for key, label in field_order:
            if key in address:
                output.append(f"- {label}: {address[key]}")

        # Include any other fields not in the standard list
        standard_keys = {k for k, _ in field_order}
        for key, value in address.items():
            if key not in standard_keys:
                formatted_key = key.replace("_", " ").title()
                output.append(f"- {formatted_key}: {value}")

    return "\n".join(output)


async def geocode_tool(address: str, limit: int = 1) -> str:
    """
    Convert an address to geographic coordinates.

    Args:
        address: The address to geocode (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
        limit: Maximum number of results to return (1-10, default: 1)

    Returns:
        Markdown formatted geocoding results with coordinates and location information

    Raises:
        ValueError: If address is empty or limit is invalid
    """
    # Validate inputs
    if not address or not address.strip():
        raise ValueError("❌ Address cannot be empty")

    if limit < 1 or limit > 10:
        raise ValueError("❌ Limit must be between 1 and 10")

    try:
        # Create client and geocode
        client = NominatimClient()
        results = await client.geocode(address.strip(), limit=limit, addressdetails=True)
        await client.close()

        # Handle no results
        if not results:
            return f"## ❌ No Results Found\n\nNo locations found for address: **{address}**\n\nTry:\n- Checking the spelling\n- Using a more general address\n- Including city, state, or country"

        # Format results
        output = []
        output.append(f"# 📍 Geocoding Results for '{address}'")
        output.append("")
        output.append(f"Found {len(results)} result(s):")
        output.append("")

        for i, result in enumerate(results, 1):
            if i > 1:
                output.append("")
                output.append("---")
                output.append("")
            output.append(format_geocode_result(result, i if len(results) > 1 else 0))

        return "\n".join(output)

    except BadRequestError as e:
        logger.error(f"Geocoding validation error: {e}")
        return f"## ❌ Invalid Request\n\n{str(e)}\n\nPlease check your input and try again."

    except NominatimError as e:
        logger.error(f"Geocoding API error: {e}")
        return f"## ❌ Geocoding Error\n\n{str(e)}\n\nThe geocoding service encountered an error. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected geocoding error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


async def reverse_geocode_tool(lat: float, lon: float) -> str:
    """
    Convert geographic coordinates to an address.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Markdown formatted address and location information

    Raises:
        ValueError: If coordinates are invalid
    """
    # Validate coordinates
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ValueError("❌ Latitude and longitude must be numbers")

    if not -90 <= lat <= 90:
        raise ValueError(f"❌ Latitude must be between -90 and 90 (got {lat})")

    if not -180 <= lon <= 180:
        raise ValueError(f"❌ Longitude must be between -180 and 180 (got {lon})")

    try:
        # Create client and reverse geocode
        client = NominatimClient()
        result = await client.reverse_geocode(lat, lon, zoom=18)
        await client.close()

        # Handle no result
        if not result:
            return f"## ❌ No Location Found\n\nNo address found for coordinates: **{lat}, {lon}**\n\nThis location may be:\n- In the ocean or a remote area\n- Outside mapped regions\n- In a restricted area\n\nTry coordinates closer to populated areas."

        # Format result
        output = []
        output.append(f"# 🗺️ Reverse Geocoding Results")
        output.append("")
        output.append(f"**Query Coordinates:** {lat}, {lon}")
        output.append("")
        output.append(format_reverse_geocode_result(result))

        return "\n".join(output)

    except BadRequestError as e:
        logger.error(f"Reverse geocoding validation error: {e}")
        return f"## ❌ Invalid Coordinates\n\n{str(e)}\n\nPlease provide valid coordinates:\n- Latitude: -90 to 90\n- Longitude: -180 to 180"

    except NominatimError as e:
        logger.error(f"Reverse geocoding API error: {e}")
        return f"## ❌ Reverse Geocoding Error\n\n{str(e)}\n\nThe reverse geocoding service encountered an error. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected reverse geocoding error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


__all__ = ["geocode_tool", "reverse_geocode_tool"]
