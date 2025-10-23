"""MCP tools for routing and route comparison."""

import logging
from typing import Any

from src.clients.nominatim import NominatimClient, NominatimError
from src.clients.osrm import OSRMClient, OSRMError
from src.clients.transit import NoTransitDataError, TransitLandClient, TransitError

logger = logging.getLogger(__name__)


def parse_location(location: str) -> tuple[float, float]:
    """
    Parse location string as coordinates in "lat,lon" format.

    Args:
        location: Location string in "lat,lon" format

    Returns:
        (lat, lon) tuple

    Raises:
        ValueError: If location format is invalid
    """
    import re

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

    raise ValueError("Location must be in 'lat,lon' format (e.g., '40.7128,-74.0060')")


async def calculate_route_tool(
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
    # Validate inputs
    if not origin or not origin.strip():
        raise ValueError("❌ Origin cannot be empty")

    if not destination or not destination.strip():
        raise ValueError("❌ Destination cannot be empty")

    valid_modes = ["driving", "cycling", "walking", "transit"]
    if mode.lower() not in valid_modes:
        return f"""## ❌ Invalid Mode

Mode '{mode}' not recognized.

**Valid modes:**
- driving (car)
- cycling (bike)
- walking (foot)
- transit (public transportation)"""

    try:
        # Parse locations
        origin_lat, origin_lon = parse_location(origin)
        dest_lat, dest_lon = parse_location(destination)

        # Mode-specific icons
        mode_icons = {
            "driving": "🚗",
            "cycling": "🚴",
            "walking": "🚶",
            "transit": "🚌"
        }
        icon = mode_icons.get(mode.lower(), "🗺️")

        # Handle transit separately
        if mode.lower() == "transit":
            transit_client = TransitLandClient()
            try:
                result = await transit_client.get_transit_options(
                    origin_lat, origin_lon,
                    dest_lat, dest_lon
                )
                await transit_client.close()

                # Format transit results
                output = []
                output.append(f"# {icon} Transit Route")
                output.append("")
                output.append(f"**Origin:** {origin_lat}, {origin_lon}")
                output.append(f"**Destination:** {dest_lat}, {dest_lon}")
                output.append(f"**Distance:** {result.get('total_distance_meters', 0):.0f}m")
                output.append("")
                output.append("## 📍 Nearby Stops at Origin")
                output.append("")

                for i, stop in enumerate(result.get('origin_stops', [])[:3], 1):
                    output.append(f"{i}. **{stop.get('name')}** ({stop.get('distance_meters')}m away)")
                    if stop.get('routes'):
                        routes = ", ".join(stop.get('routes', [])[:5])
                        output.append(f"   Routes: {routes}")

                output.append("")
                output.append("## 📍 Nearby Stops at Destination")
                output.append("")

                for i, stop in enumerate(result.get('destination_stops', [])[:3], 1):
                    output.append(f"{i}. **{stop.get('name')}** ({stop.get('distance_meters')}m away)")
                    if stop.get('routes'):
                        routes = ", ".join(stop.get('routes', [])[:5])
                        output.append(f"   Routes: {routes}")

                output.append("")
                output.append("---")
                output.append("")
                output.append("**Note:** " + result.get('note', ''))

                return "\n".join(output)

            except NoTransitDataError as e:
                logger.error(f"Transit data unavailable: {e}")
                return f"""## {icon} No Transit Data Available

{str(e)}

**Suggestions:**
- Try a different location with better transit coverage
- Use driving, cycling, or walking modes instead
- Check if the area has public transportation

**Alternative:** Use `compare_routes` to see all available transportation options."""

        # Use OSRM for driving, cycling, walking
        osrm_client = OSRMClient()
        route = await osrm_client.route(
            origin=(origin_lat, origin_lon),
            destination=(dest_lat, dest_lon),
            profile=mode.lower()
        )
        await osrm_client.close()

        # Format route results
        output = []
        output.append(f"# {icon} Route: {mode.title()}")
        output.append("")
        output.append(f"**Origin:** {origin_lat}, {origin_lon}")
        output.append(f"**Destination:** {dest_lat}, {dest_lon}")
        output.append("")

        # Route summary
        distance_km = route.get('distance_meters', 0) / 1000
        duration_min = route.get('duration_seconds', 0) / 60

        output.append(f"**📏 Distance:** {distance_km:.2f} km")
        output.append(f"**⏱️ Duration:** {duration_min:.0f} minutes")
        output.append("")

        # Turn-by-turn directions
        if include_steps and route.get('directions'):
            output.append("## 🗺️ Turn-by-Turn Directions")
            output.append("")

            for direction in route.get('directions', []):
                output.append(f"**{direction}**")

            output.append("")

        return "\n".join(output)

    except ValueError as e:
        logger.error(f"Route validation error: {e}")
        return f"## ❌ Invalid Input\n\n{str(e)}\n\nPlease check your input and try again."

    except (OSRMError, TransitError) as e:
        logger.error(f"Routing error: {e}")
        return f"## ❌ Routing Error\n\n{str(e)}\n\nThe routing service encountered an error. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected routing error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


async def compare_routes_tool(
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
    # Validate inputs
    if not origin or not origin.strip():
        raise ValueError("❌ Origin cannot be empty")

    if not destination or not destination.strip():
        raise ValueError("❌ Destination cannot be empty")

    try:
        # Parse locations
        origin_lat, origin_lon = parse_location(origin)
        dest_lat, dest_lon = parse_location(destination)

        # Initialize clients
        osrm_client = OSRMClient()
        results = {}

        # Get routes for all OSRM modes
        modes = ["driving", "cycling", "walking"]
        for mode in modes:
            try:
                route = await osrm_client.route(
                    origin=(origin_lat, origin_lon),
                    destination=(dest_lat, dest_lon),
                    profile=mode
                )
                results[mode] = route
            except OSRMError as e:
                logger.warning(f"Failed to get {mode} route: {e}")
                results[mode] = {"error": str(e)}

        await osrm_client.close()

        # Get transit info if requested
        transit_result = None
        if include_transit:
            transit_client = TransitLandClient()
            try:
                transit_result = await transit_client.get_transit_options(
                    origin_lat, origin_lon,
                    dest_lat, dest_lon
                )
            except NoTransitDataError as e:
                logger.info(f"Transit not available: {e}")
                transit_result = {"error": str(e)}
            except TransitError as e:
                logger.warning(f"Transit error: {e}")
                transit_result = {"error": str(e)}
            finally:
                await transit_client.close()

        # Format comparison table
        output = []
        output.append("# 📊 Route Comparison")
        output.append("")
        output.append(f"**Origin:** {origin_lat}, {origin_lon}")
        output.append(f"**Destination:** {dest_lat}, {dest_lon}")
        output.append("")
        output.append("## Transportation Options")
        output.append("")

        # Create comparison table
        output.append("| Mode | Distance | Duration | Notes |")
        output.append("|------|----------|----------|-------|")

        # Driving
        if "error" not in results.get("driving", {}):
            driving = results["driving"]
            dist_km = driving.get('distance_meters', 0) / 1000
            dur_min = driving.get('duration_seconds', 0) / 60
            output.append(f"| 🚗 Driving | {dist_km:.2f} km | {dur_min:.0f} min | Fastest by car |")
        else:
            output.append(f"| 🚗 Driving | - | - | {results['driving']['error']} |")

        # Cycling
        if "error" not in results.get("cycling", {}):
            cycling = results["cycling"]
            dist_km = cycling.get('distance_meters', 0) / 1000
            dur_min = cycling.get('duration_seconds', 0) / 60
            output.append(f"| 🚴 Cycling | {dist_km:.2f} km | {dur_min:.0f} min | Bike-friendly route |")
        else:
            output.append(f"| 🚴 Cycling | - | - | {results['cycling']['error']} |")

        # Walking
        if "error" not in results.get("walking", {}):
            walking = results["walking"]
            dist_km = walking.get('distance_meters', 0) / 1000
            dur_min = walking.get('duration_seconds', 0) / 60
            output.append(f"| 🚶 Walking | {dist_km:.2f} km | {dur_min:.0f} min | Pedestrian route |")
        else:
            output.append(f"| 🚶 Walking | - | - | {results['walking']['error']} |")

        # Transit
        if include_transit and transit_result:
            if "error" not in transit_result:
                dist_km = transit_result.get('total_distance_meters', 0) / 1000
                stops_count = len(transit_result.get('origin_stops', []))
                output.append(f"| 🚌 Transit | {dist_km:.2f} km | Varies | {stops_count} stops nearby |")
            else:
                output.append(f"| 🚌 Transit | - | - | {transit_result['error']} |")

        output.append("")

        # Add recommendations
        output.append("## 💡 Recommendations")
        output.append("")

        # Find fastest mode
        valid_results = {k: v for k, v in results.items() if "error" not in v}
        if valid_results:
            fastest = min(valid_results.items(), key=lambda x: x[1].get('duration_seconds', float('inf')))
            fastest_mode = fastest[0]
            fastest_time = fastest[1].get('duration_seconds', 0) / 60

            output.append(f"- **Fastest:** {fastest_mode.title()} ({fastest_time:.0f} minutes)")

            # Find shortest distance
            shortest = min(valid_results.items(), key=lambda x: x[1].get('distance_meters', float('inf')))
            shortest_mode = shortest[0]
            shortest_dist = shortest[1].get('distance_meters', 0) / 1000

            output.append(f"- **Shortest:** {shortest_mode.title()} ({shortest_dist:.2f} km)")

            # Eco-friendly option
            if "cycling" in valid_results:
                output.append("- **Eco-friendly:** Cycling (zero emissions)")
            elif "walking" in valid_results:
                output.append("- **Eco-friendly:** Walking (zero emissions)")

        output.append("")

        # Transit details if available
        if include_transit and transit_result and "error" not in transit_result:
            output.append("## 🚌 Transit Details")
            output.append("")
            output.append("**Nearby stops at origin:**")
            for stop in transit_result.get('origin_stops', [])[:3]:
                output.append(f"- {stop.get('name')} ({stop.get('distance_meters')}m)")
            output.append("")

        return "\n".join(output)

    except ValueError as e:
        logger.error(f"Route comparison validation error: {e}")
        return f"## ❌ Invalid Input\n\n{str(e)}\n\nPlease check your input and try again."

    except Exception as e:
        logger.error(f"Unexpected comparison error: {e}", exc_info=True)
        return f"## ❌ Unexpected Error\n\nAn unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the issue persists."


__all__ = ["calculate_route_tool", "compare_routes_tool"]
