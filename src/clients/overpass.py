"""Overpass API client for POI search with category mapping."""

import asyncio
import logging
import math
from typing import Any, Optional

import httpx

from src.cache import cache
from src.config import CacheTTL, settings

logger = logging.getLogger(__name__)


class OverpassError(Exception):
    """Base exception for Overpass API errors."""

    pass


class QueryTimeoutError(OverpassError):
    """Query timeout error."""

    pass


class BadQueryError(OverpassError):
    """Invalid query error."""

    pass


# Category to OSM tag mapping
CATEGORY_MAPPING = {
    # Food & Drink
    "restaurant": ["amenity=restaurant"],
    "cafe": ["amenity=cafe"],
    "bar": ["amenity=bar"],
    "fast_food": ["amenity=fast_food"],
    "food": ["amenity=restaurant", "amenity=cafe", "amenity=fast_food"],
    # Healthcare
    "hospital": ["amenity=hospital"],
    "pharmacy": ["amenity=pharmacy"],
    "doctors": ["amenity=doctors"],
    "dentist": ["amenity=dentist"],
    "clinic": ["amenity=clinic"],
    "healthcare": ["amenity=hospital", "amenity=clinic", "amenity=doctors"],
    # Education
    "school": ["amenity=school"],
    "university": ["amenity=university"],
    "college": ["amenity=college"],
    "kindergarten": ["amenity=kindergarten"],
    "education": ["amenity=school", "amenity=university", "amenity=college"],
    # Finance
    "bank": ["amenity=bank"],
    "atm": ["amenity=atm"],
    # Recreation
    "park": ["leisure=park"],
    "playground": ["leisure=playground"],
    "sports_centre": ["leisure=sports_centre"],
    "swimming_pool": ["leisure=swimming_pool"],
    "cinema": ["amenity=cinema"],
    "theatre": ["amenity=theatre"],
    "museum": ["tourism=museum"],
    # Transportation
    "parking": ["amenity=parking"],
    "fuel": ["amenity=fuel"],
    "charging_station": ["amenity=charging_station"],
    "bus_station": ["amenity=bus_station"],
    "taxi": ["amenity=taxi"],
    # Shopping
    "supermarket": ["shop=supermarket"],
    "convenience": ["shop=convenience"],
    "mall": ["shop=mall"],
    "shopping": ["shop=supermarket", "shop=mall", "shop=convenience"],
    # Accommodation
    "hotel": ["tourism=hotel"],
    "hostel": ["tourism=hostel"],
    "motel": ["tourism=motel"],
    "accommodation": ["tourism=hotel", "tourism=hostel", "tourism=motel"],
    # Emergency
    "police": ["amenity=police"],
    "fire_station": ["amenity=fire_station"],
    "emergency": ["amenity=police", "amenity=fire_station", "amenity=hospital"],
    # Religion
    "place_of_worship": ["amenity=place_of_worship"],
    # Other
    "post_office": ["amenity=post_office"],
    "library": ["amenity=library"],
    "toilet": ["amenity=toilets"],
    "drinking_water": ["amenity=drinking_water"],
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in meters
    """
    # Earth radius in meters
    R = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


class OverpassClient:
    """
    Async HTTP client for Overpass API POI search.

    Features:
    - Overpass QL query generation
    - Category to OSM tag mapping
    - Radius-based POI search
    - Distance calculation
    - Response caching (1 hour TTL)
    - Timeout handling
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize Overpass client.

        Args:
            base_url: Overpass API base URL (defaults to config)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or str(settings.overpass_url)).rstrip("/")
        self.timeout = timeout

        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

        logger.info(f"Initialized OverpassClient: base_url={self.base_url}, timeout={timeout}s")

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("OverpassClient closed")

    def _build_overpass_query(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        tags: list[str],
        limit: int,
    ) -> str:
        """
        Build Overpass QL query for POI search.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_meters: Search radius in meters
            tags: List of OSM tags (e.g., ["amenity=restaurant", "amenity=cafe"])
            limit: Maximum results

        Returns:
            Overpass QL query string
        """
        # Build tag filters
        tag_filters = []
        for tag in tags:
            if "=" in tag:
                key, value = tag.split("=", 1)
                tag_filters.append(f'["{key}"="{value}"]')
            else:
                tag_filters.append(f'["{tag}"]')

        tag_filter_str = "".join(tag_filters)

        # Build query for nodes, ways, and relations
        query = f"""
[out:json][timeout:25];
(
  node{tag_filter_str}(around:{radius_meters},{lat},{lon});
  way{tag_filter_str}(around:{radius_meters},{lat},{lon});
  relation{tag_filter_str}(around:{radius_meters},{lat},{lon});
);
out center {limit};
""".strip()

        return query

    def _parse_element(self, element: dict[str, Any], center_lat: float, center_lon: float) -> dict[str, Any]:
        """
        Parse Overpass API element to normalized POI result.

        Args:
            element: Raw element from Overpass response
            center_lat: Search center latitude (for distance calculation)
            center_lon: Search center longitude (for distance calculation)

        Returns:
            Normalized POI data
        """
        # Get coordinates (handle both nodes and way centers)
        if element["type"] == "node":
            lat = element.get("lat", 0.0)
            lon = element.get("lon", 0.0)
        else:
            # For ways/relations, use center coordinates
            center = element.get("center", {})
            lat = center.get("lat", 0.0)
            lon = center.get("lon", 0.0)

        # Extract tags
        tags = element.get("tags", {})

        # Calculate distance from center
        distance = haversine_distance(center_lat, center_lon, lat, lon)

        # Extract common fields
        result = {
            "id": element.get("id"),
            "type": element.get("type"),
            "lat": lat,
            "lon": lon,
            "distance_meters": round(distance, 1),
            "name": tags.get("name"),
            "amenity": tags.get("amenity"),
            "shop": tags.get("shop"),
            "leisure": tags.get("leisure"),
            "tourism": tags.get("tourism"),
            "tags": tags,
        }

        # Add address components if available
        address_fields = ["addr:housenumber", "addr:street", "addr:city", "addr:postcode", "addr:country"]
        address = {}
        for field in address_fields:
            if field in tags:
                key = field.replace("addr:", "")
                address[key] = tags[field]

        if address:
            result["address"] = address

        return result

    async def search_pois(
        self,
        lat: float,
        lon: float,
        category: str,
        radius_meters: int = 1000,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for POIs near a location.

        Args:
            lat: Center latitude (-90 to 90)
            lon: Center longitude (-180 to 180)
            category: POI category (see CATEGORY_MAPPING)
            radius_meters: Search radius in meters (max 5000)
            limit: Maximum results (1-100)

        Returns:
            List of POI results sorted by distance

        Raises:
            BadQueryError: If parameters are invalid
            QueryTimeoutError: If query times out
            OverpassError: On API errors
        """
        # Validate coordinates
        if not -90 <= lat <= 90:
            raise BadQueryError(f"Latitude must be between -90 and 90, got {lat}")

        if not -180 <= lon <= 180:
            raise BadQueryError(f"Longitude must be between -180 and 180, got {lon}")

        # Validate radius
        if radius_meters < 1 or radius_meters > 5000:
            raise BadQueryError(f"Radius must be between 1 and 5000 meters, got {radius_meters}")

        # Validate limit
        if limit < 1 or limit > 100:
            raise BadQueryError(f"Limit must be between 1 and 100, got {limit}")

        # Get OSM tags for category
        category_lower = category.lower()
        if category_lower not in CATEGORY_MAPPING:
            raise BadQueryError(
                f"Unknown category '{category}'. Available: {', '.join(sorted(CATEGORY_MAPPING.keys()))}"
            )

        tags = CATEGORY_MAPPING[category_lower]

        # Check cache first
        cache_key = (lat, lon, category_lower, radius_meters, limit)
        cached = cache.get("poi", *cache_key)
        if cached is not None:
            logger.info(f"Cache hit for POI search: {category} near ({lat}, {lon})")
            return cached

        # Build Overpass query
        query = self._build_overpass_query(lat, lon, radius_meters, tags, limit)

        logger.debug(f"Overpass query: {query[:100]}...")

        try:
            # Execute query
            response = await self.client.post(
                self.base_url,
                data=query,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Handle errors
            if response.status_code == 400:
                raise BadQueryError(f"Invalid Overpass query: {response.text[:200]}")
            elif response.status_code == 429:
                raise OverpassError("Rate limit exceeded")
            elif response.status_code == 504:
                raise QueryTimeoutError("Query timeout - try reducing radius or limit")
            elif response.status_code >= 400:
                raise OverpassError(f"HTTP {response.status_code}: {response.text[:200]}")

            response.raise_for_status()

            # Parse JSON
            data = response.json()
            elements = data.get("elements", [])

            logger.debug(f"Overpass returned {len(elements)} elements")

            # Parse and enrich results
            results = [self._parse_element(elem, lat, lon) for elem in elements]

            # Sort by distance
            results.sort(key=lambda x: x["distance_meters"])

            # Apply limit (Overpass may return more)
            results = results[:limit]

            # Cache results (1 hour TTL)
            cache.set("poi", results, CacheTTL.POI, *cache_key)

            logger.info(f"Found {len(results)} POIs for category '{category}' near ({lat}, {lon})")

            return results

        except httpx.TimeoutException:
            raise QueryTimeoutError(f"Request timeout after {self.timeout}s - try reducing radius")
        except httpx.HTTPError as e:
            raise OverpassError(f"HTTP error: {e}")


# Global client instance
_client: Optional[OverpassClient] = None


async def get_client() -> OverpassClient:
    """
    Get or create global Overpass client instance.

    Returns:
        Shared OverpassClient instance
    """
    global _client
    if _client is None:
        _client = OverpassClient()
    return _client


async def close_client() -> None:
    """Close global Overpass client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


__all__ = [
    "OverpassClient",
    "OverpassError",
    "QueryTimeoutError",
    "BadQueryError",
    "CATEGORY_MAPPING",
    "haversine_distance",
    "get_client",
    "close_client",
]
