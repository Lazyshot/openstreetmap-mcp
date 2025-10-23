"""Transit.land API client for public transit information with graceful degradation."""

import asyncio
import logging
from typing import Any, Optional

import httpx

from src.cache import cache
from src.clients.overpass import OverpassClient, haversine_distance
from src.config import CacheTTL, settings

logger = logging.getLogger(__name__)


class TransitError(Exception):
    """Base exception for transit API errors."""

    pass


class NoTransitDataError(TransitError):
    """No transit data available for location."""

    pass


class TransitLandClient:
    """
    Async HTTP client for Transit.land API with Overpass fallback.

    Features:
    - Nearby stop discovery
    - Basic route information
    - Graceful degradation to Overpass when no transit data
    - Response caching (5 minute TTL)
    - Timeout handling (45s)

    Note: Transit.land coverage varies by city. This client provides
    best-effort transit information and falls back gracefully.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 45.0,
    ):
        """
        Initialize Transit.land client.

        Args:
            base_url: Transit.land API base URL (defaults to config)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or str(settings.transitland_url)).rstrip("/")
        self.timeout = timeout

        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

        logger.info(f"Initialized TransitLandClient: base_url={self.base_url}, timeout={timeout}s")

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("TransitLandClient closed")

    async def find_nearby_stops(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Find transit stops near a location using Transit.land API.

        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters (default: 500)

        Returns:
            List of nearby stops with details

        Raises:
            NoTransitDataError: If no transit data available
            TransitError: On API errors
        """
        # Check cache first
        cache_key = (lat, lon, radius_meters)
        cached = cache.get("transit_stops", *cache_key)
        if cached is not None:
            logger.info(f"Cache hit for transit stops near ({lat}, {lon})")
            return cached

        # Build API request
        url = f"{self.base_url}/stops"
        params = {
            "lat": lat,
            "lon": lon,
            "radius": radius_meters,
            "limit": 20,
        }

        try:
            logger.debug(f"Transit.land request: {url} with params {params}")

            response = await self.client.get(url, params=params)

            # Handle errors
            if response.status_code == 403:
                # Transit.land may require authentication - fall back to Overpass
                logger.info("Transit.land access restricted, will use Overpass fallback")
                raise NoTransitDataError("Transit.land requires authentication")
            elif response.status_code == 404:
                raise NoTransitDataError("No transit data available for this location")
            elif response.status_code >= 400:
                raise TransitError(f"HTTP {response.status_code}: {response.text[:200]}")

            response.raise_for_status()

            # Parse JSON
            data = response.json()
            stops = data.get("stops", [])

            if not stops:
                raise NoTransitDataError("No transit stops found in this area")

            # Parse and enrich stops
            results = []
            for stop in stops:
                # Calculate distance from query point
                stop_lat = stop.get("geometry", {}).get("coordinates", [0, 0])[1]
                stop_lon = stop.get("geometry", {}).get("coordinates", [0, 0])[0]
                distance = haversine_distance(lat, lon, stop_lat, stop_lon)

                result = {
                    "name": stop.get("stop_name", "Unknown Stop"),
                    "lat": stop_lat,
                    "lon": stop_lon,
                    "distance_meters": round(distance, 1),
                    "id": stop.get("onestop_id", ""),
                    "routes": stop.get("routes_serving_stop", []),
                }

                results.append(result)

            # Sort by distance
            results.sort(key=lambda x: x["distance_meters"])

            # Cache results (5 minute TTL)
            cache.set("transit_stops", results, CacheTTL.TRANSIT, *cache_key)

            logger.info(f"Found {len(results)} transit stops near ({lat}, {lon})")

            return results

        except httpx.TimeoutException:
            raise TransitError(f"Request timeout after {self.timeout}s")
        except httpx.HTTPError as e:
            raise TransitError(f"HTTP error: {e}")

    async def find_nearby_stops_fallback(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Fallback to Overpass API for transit stop data.

        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters

        Returns:
            List of transit stops from OpenStreetMap
        """
        logger.info("Using Overpass fallback for transit stops")

        try:
            overpass = OverpassClient()

            # Search for bus stops, tram stops, and train stations
            results = []

            # Try bus stops
            try:
                bus_stops = await overpass.search_pois(
                    lat, lon, "bus_station", radius_meters, limit=10
                )
                for stop in bus_stops:
                    results.append({
                        "name": stop.get("name", "Bus Stop"),
                        "lat": stop.get("lat"),
                        "lon": stop.get("lon"),
                        "distance_meters": stop.get("distance_meters"),
                        "type": "bus",
                        "source": "openstreetmap",
                    })
            except Exception as e:
                logger.debug(f"No bus stops found: {e}")

            await overpass.close()

            if not results:
                raise NoTransitDataError(
                    "No transit data available from Transit.land or OpenStreetMap"
                )

            results.sort(key=lambda x: x["distance_meters"])
            return results

        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            raise NoTransitDataError("Transit data not available for this area")

    async def get_transit_options(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> dict[str, Any]:
        """
        Get transit options between two points.

        Note: This is a simplified implementation that provides nearby
        transit stops. Full route planning would require complex
        schedule integration which is beyond the scope.

        Args:
            origin_lat: Origin latitude
            origin_lon: Origin longitude
            dest_lat: Destination latitude
            dest_lon: Destination longitude

        Returns:
            Dict with origin stops, destination stops, and recommendations
        """
        # Check cache
        cache_key = (origin_lat, origin_lon, dest_lat, dest_lon)
        cached = cache.get("transit_route", *cache_key)
        if cached is not None:
            logger.info("Cache hit for transit route")
            return cached

        try:
            # Find nearby stops at origin
            try:
                origin_stops = await self.find_nearby_stops(origin_lat, origin_lon, 500)
            except NoTransitDataError:
                logger.info("No Transit.land data at origin, trying fallback")
                origin_stops = await self.find_nearby_stops_fallback(origin_lat, origin_lon, 500)

            # Find nearby stops at destination
            try:
                dest_stops = await self.find_nearby_stops(dest_lat, dest_lon, 500)
            except NoTransitDataError:
                logger.info("No Transit.land data at destination, trying fallback")
                dest_stops = await self.find_nearby_stops_fallback(dest_lat, dest_lon, 500)

            # Calculate total transit distance
            total_distance = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)

            result = {
                "origin_stops": origin_stops[:5],  # Top 5 nearest
                "destination_stops": dest_stops[:5],
                "total_distance_meters": round(total_distance, 1),
                "note": "Transit route planning requires real-time schedule data. "
                        "Showing nearby stops for reference.",
            }

            # Cache result (5 minute TTL)
            cache.set("transit_route", result, CacheTTL.TRANSIT, *cache_key)

            return result

        except NoTransitDataError:
            raise
        except Exception as e:
            logger.error(f"Transit query failed: {e}")
            raise TransitError(f"Failed to get transit options: {e}")


# Global client instance
_client: Optional[TransitLandClient] = None


async def get_client() -> TransitLandClient:
    """
    Get or create global Transit.land client instance.

    Returns:
        Shared TransitLandClient instance
    """
    global _client
    if _client is None:
        _client = TransitLandClient()
    return _client


async def close_client() -> None:
    """Close global Transit.land client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


__all__ = [
    "TransitLandClient",
    "TransitError",
    "NoTransitDataError",
    "get_client",
    "close_client",
]
