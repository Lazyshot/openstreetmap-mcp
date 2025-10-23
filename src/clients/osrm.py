"""OSRM routing API client for car, bike, and foot routing."""

import asyncio
import logging
from typing import Any, Optional

import httpx

from src.cache import cache
from src.config import CacheTTL, settings

logger = logging.getLogger(__name__)


class OSRMError(Exception):
    """Base exception for OSRM API errors."""

    pass


class NoRouteError(OSRMError):
    """No route found between points."""

    pass


class InvalidCoordinatesError(OSRMError):
    """Invalid coordinates provided."""

    pass


# Mapping of OSRM instruction types to human-readable text
MANEUVER_TYPES = {
    "turn": "Turn",
    "new name": "Continue onto",
    "depart": "Depart",
    "arrive": "Arrive",
    "merge": "Merge",
    "on ramp": "Take the ramp",
    "off ramp": "Take the exit",
    "fork": "At the fork",
    "end of road": "At the end of the road",
    "continue": "Continue",
    "roundabout": "Enter the roundabout",
    "rotary": "Enter the rotary",
    "roundabout turn": "At the roundabout",
    "notification": "Note",
    "exit roundabout": "Exit the roundabout",
    "exit rotary": "Exit the rotary",
}

MODIFIER_MAP = {
    "left": "left",
    "right": "right",
    "sharp left": "sharp left",
    "sharp right": "sharp right",
    "slight left": "slight left",
    "slight right": "slight right",
    "straight": "straight",
    "uturn": "U-turn",
}


class OSRMClient:
    """
    Async HTTP client for OSRM routing API.

    Features:
    - Multi-profile routing (driving, cycling, walking)
    - Turn-by-turn directions
    - Distance and duration calculation
    - GeoJSON geometry
    - Response caching (5 minute TTL)
    - Timeout handling
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize OSRM client.

        Args:
            base_url: OSRM API base URL (defaults to config)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or str(settings.osrm_url)).rstrip("/")
        self.timeout = timeout

        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

        logger.info(f"Initialized OSRMClient: base_url={self.base_url}, timeout={timeout}s")

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("OSRMClient closed")

    def _format_coordinates(self, origin: tuple[float, float], destination: tuple[float, float]) -> str:
        """
        Format coordinates for OSRM API.

        Args:
            origin: (lon, lat) tuple for start point
            destination: (lon, lat) tuple for end point

        Returns:
            Coordinates string in format "lon1,lat1;lon2,lat2"
        """
        return f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"

    def _format_direction(self, step: dict[str, Any], step_num: int) -> str:
        """
        Format a routing step into human-readable direction.

        Args:
            step: OSRM step dictionary
            step_num: Step number for display

        Returns:
            Formatted direction string
        """
        maneuver = step.get("maneuver", {})
        maneuver_type = maneuver.get("type", "")
        modifier = maneuver.get("modifier", "")

        # Get instruction text
        instruction = MANEUVER_TYPES.get(maneuver_type, maneuver_type.title())

        # Add modifier if present
        if modifier and modifier in MODIFIER_MAP:
            if maneuver_type == "turn":
                instruction = f"Turn {MODIFIER_MAP[modifier]}"
            elif maneuver_type in ["on ramp", "off ramp", "fork"]:
                instruction = f"{instruction} {MODIFIER_MAP[modifier]}"

        # Get street name
        name = step.get("name", "")
        if name and name != "-":
            if maneuver_type == "new name":
                instruction = f"{instruction} {name}"
            elif maneuver_type not in ["arrive", "depart"]:
                instruction = f"{instruction} onto {name}"

        # Get distance
        distance = step.get("distance", 0)
        if distance > 0:
            if distance >= 1000:
                distance_str = f"{distance / 1000:.1f} km"
            else:
                distance_str = f"{int(distance)} m"

            instruction = f"{instruction} ({distance_str})"

        return f"{step_num}. {instruction}"

    def _parse_route(self, route_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse OSRM route response.

        Args:
            route_data: Route object from OSRM response

        Returns:
            Parsed route with distance, duration, geometry, and directions
        """
        # Extract basic info
        distance = route_data.get("distance", 0)  # meters
        duration = route_data.get("duration", 0)  # seconds
        geometry = route_data.get("geometry", {})

        # Parse legs and steps
        legs = route_data.get("legs", [])
        all_steps = []
        directions = []

        step_num = 1
        for leg in legs:
            steps = leg.get("steps", [])
            for step in steps:
                all_steps.append(step)

                # Skip last "arrive" step for intermediate legs
                maneuver_type = step.get("maneuver", {}).get("type", "")
                if maneuver_type == "arrive" and leg != legs[-1]:
                    continue

                direction = self._format_direction(step, step_num)
                directions.append(direction)
                step_num += 1

        return {
            "distance_meters": distance,
            "duration_seconds": duration,
            "distance_km": round(distance / 1000, 2),
            "duration_minutes": round(duration / 60, 1),
            "geometry": geometry,
            "steps": all_steps,
            "directions": directions,
        }

    async def route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str = "driving",
    ) -> dict[str, Any]:
        """
        Calculate route between two points.

        Args:
            origin: (lat, lon) tuple for start point
            destination: (lat, lon) tuple for end point
            profile: Routing profile - "driving", "cycling", or "walking"

        Returns:
            Route information with distance, duration, geometry, and directions

        Raises:
            InvalidCoordinatesError: If coordinates are invalid
            NoRouteError: If no route can be found
            OSRMError: On API errors
        """
        # Validate profile
        valid_profiles = ["driving", "cycling", "walking"]
        if profile not in valid_profiles:
            raise OSRMError(
                f"Invalid profile '{profile}'. Must be one of: {', '.join(valid_profiles)}"
            )

        # Validate coordinates
        orig_lat, orig_lon = origin
        dest_lat, dest_lon = destination

        if not (-90 <= orig_lat <= 90 and -180 <= orig_lon <= 180):
            raise InvalidCoordinatesError(
                f"Invalid origin coordinates: ({orig_lat}, {orig_lon})"
            )

        if not (-90 <= dest_lat <= 90 and -180 <= dest_lon <= 180):
            raise InvalidCoordinatesError(
                f"Invalid destination coordinates: ({dest_lat}, {dest_lon})"
            )

        # Check cache first
        cache_key = (orig_lat, orig_lon, dest_lat, dest_lon, profile)
        cached = cache.get("route", *cache_key)
        if cached is not None:
            logger.info(f"Cache hit for route: {profile} from ({orig_lat}, {orig_lon}) to ({dest_lat}, {dest_lon})")
            return cached

        # OSRM uses lon,lat order (not lat,lon!)
        coords = self._format_coordinates(
            (orig_lon, orig_lat),
            (dest_lon, dest_lat)
        )

        # Build URL
        url = f"{self.base_url}/route/v1/{profile}/{coords}"
        params = {
            "overview": "full",
            "steps": "true",
            "geometries": "geojson",
        }

        try:
            logger.debug(f"OSRM request: {url} with params {params}")

            response = await self.client.get(url, params=params)

            # Handle errors
            if response.status_code == 400:
                raise InvalidCoordinatesError("Invalid coordinates or request")
            elif response.status_code >= 400:
                raise OSRMError(f"HTTP {response.status_code}: {response.text[:200]}")

            response.raise_for_status()

            # Parse JSON
            data = response.json()

            # Check OSRM response code
            code = data.get("code")
            if code != "Ok":
                message = data.get("message", "Unknown error")

                if code == "NoRoute":
                    raise NoRouteError(f"No route found between points: {message}")
                elif code == "NoSegment":
                    raise NoRouteError(f"No matching road segment found: {message}")
                elif code == "InvalidValue":
                    raise InvalidCoordinatesError(f"Invalid input: {message}")
                else:
                    raise OSRMError(f"OSRM error ({code}): {message}")

            # Extract routes
            routes = data.get("routes", [])
            if not routes:
                raise NoRouteError("No routes returned by OSRM")

            # Parse first (best) route
            route_data = routes[0]
            parsed_route = self._parse_route(route_data)

            # Add metadata
            parsed_route["profile"] = profile
            parsed_route["origin"] = {"lat": orig_lat, "lon": orig_lon}
            parsed_route["destination"] = {"lat": dest_lat, "lon": dest_lon}

            # Cache result (5 minute TTL)
            cache.set("route", parsed_route, CacheTTL.ROUTE, *cache_key)

            logger.info(
                f"Calculated {profile} route: {parsed_route['distance_km']} km, "
                f"{parsed_route['duration_minutes']} min"
            )

            return parsed_route

        except httpx.TimeoutException:
            raise OSRMError(f"Request timeout after {self.timeout}s")
        except httpx.HTTPError as e:
            raise OSRMError(f"HTTP error: {e}")


# Global client instance
_client: Optional[OSRMClient] = None


async def get_client() -> OSRMClient:
    """
    Get or create global OSRM client instance.

    Returns:
        Shared OSRMClient instance
    """
    global _client
    if _client is None:
        _client = OSRMClient()
    return _client


async def close_client() -> None:
    """Close global OSRM client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


__all__ = [
    "OSRMClient",
    "OSRMError",
    "NoRouteError",
    "InvalidCoordinatesError",
    "get_client",
    "close_client",
]
