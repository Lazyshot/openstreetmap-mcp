"""Nominatim geocoding API client with rate limiting and caching."""

import asyncio
import logging
from typing import Any, Optional

import httpx

from src.cache import cache
from src.config import CacheTTL, RateLimits, settings

logger = logging.getLogger(__name__)


class NominatimError(Exception):
    """Base exception for Nominatim API errors."""

    pass


class RateLimitError(NominatimError):
    """Rate limit exceeded error."""

    pass


class BadRequestError(NominatimError):
    """Invalid request parameters error."""

    pass


class ServerError(NominatimError):
    """Nominatim server error."""

    pass


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API requests.

    Ensures requests are limited to a specific rate (e.g., 1 request/second).
    """

    def __init__(self, requests_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests allowed per second
        """
        self.rate = requests_per_second
        self.interval = 1.0 / requests_per_second
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.

        Blocks until enough time has passed since the last request.
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time

            if time_since_last < self.interval:
                wait_time = self.interval - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()


class NominatimClient:
    """
    Async HTTP client for Nominatim geocoding API.

    Features:
    - Rate limiting (1 request/second)
    - Retry logic with exponential backoff
    - Response caching (24 hour TTL)
    - Comprehensive error handling
    - Required User-Agent header
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        """
        Initialize Nominatim client.

        Args:
            base_url: Nominatim API base URL (defaults to config)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = (base_url or str(settings.nominatim_url)).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Rate limiter (1 request/second for Nominatim)
        self.rate_limiter = TokenBucketRateLimiter(
            RateLimits.NOMINATIM_REQUESTS_PER_SECOND
        )

        # HTTP client with User-Agent header
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

        logger.info(
            f"Initialized NominatimClient: base_url={self.base_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("NominatimClient closed")

    async def _make_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Make rate-limited HTTP request with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/search', '/reverse')
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            NominatimError: On API errors
            httpx.HTTPError: On network errors after retries
        """
        # Add format=json to all requests
        params = {**params, "format": "json"}
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await self.rate_limiter.acquire()

                # Make request
                logger.debug(f"Request to {endpoint}: params={params}")
                response = await self.client.get(url, params=params)

                # Handle HTTP errors
                if response.status_code == 400:
                    raise BadRequestError(f"Invalid request parameters: {params}")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code == 503:
                    raise ServerError("Nominatim service unavailable")
                elif response.status_code >= 400:
                    raise NominatimError(
                        f"HTTP {response.status_code}: {response.text}"
                    )

                response.raise_for_status()

                # Parse JSON
                data = response.json()
                logger.debug(f"Response from {endpoint}: {len(data)} results")
                return data

            except (httpx.HTTPError, NominatimError) as e:
                is_last_attempt = attempt == self.max_retries - 1

                if is_last_attempt:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise

                # Exponential backoff: 1s, 2s, 4s
                delay = 2**attempt
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # Should never reach here, but for type safety
        raise NominatimError("Request failed after all retry attempts")

    def _parse_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and normalize Nominatim result.

        Args:
            result: Raw API result

        Returns:
            Normalized result with standardized fields
        """
        return {
            "display_name": result.get("display_name"),
            "lat": float(result.get("lat", 0)),
            "lon": float(result.get("lon", 0)),
            "type": result.get("type"),
            "class": result.get("class"),
            "importance": result.get("importance"),
            "address": result.get("address", {}),
            "boundingbox": result.get("boundingbox"),
            "osm_type": result.get("osm_type"),
            "osm_id": result.get("osm_id"),
        }

    async def geocode(
        self, address: str, limit: int = 1, addressdetails: bool = True
    ) -> list[dict[str, Any]]:
        """
        Geocode an address to coordinates.

        Args:
            address: Address string to geocode
            limit: Maximum number of results (1-50)
            addressdetails: Include detailed address breakdown

        Returns:
            List of geocoding results with coordinates and metadata

        Raises:
            BadRequestError: If address is empty or limit is invalid
            NominatimError: On API errors
        """
        # Validate input
        if not address or not address.strip():
            raise BadRequestError("Address must be a non-empty string")

        if limit < 1 or limit > 50:
            raise BadRequestError("Limit must be between 1 and 50")

        # Check cache first
        cache_key = (address.strip().lower(), limit, addressdetails)
        cached = cache.get("geocode", *cache_key)
        if cached is not None:
            logger.info(f"Cache hit for geocode: {address[:50]}...")
            return cached

        # Make API request
        params = {
            "q": address.strip(),
            "limit": limit,
            "addressdetails": 1 if addressdetails else 0,
        }

        results = await self._make_request("/search", params)

        # Handle empty results
        if not results:
            logger.info(f"No geocoding results found for: {address}")
            return []

        # Parse results
        parsed = [self._parse_result(r) for r in results]

        # Cache results (24 hour TTL)
        cache.set("geocode", parsed, CacheTTL.GEOCODE, *cache_key)
        logger.info(f"Geocoded '{address}' -> {len(parsed)} result(s)")

        return parsed

    async def reverse_geocode(
        self, lat: float, lon: float, zoom: int = 18
    ) -> Optional[dict[str, Any]]:
        """
        Reverse geocode coordinates to an address.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            zoom: Detail level (0-18, higher = more detail)

        Returns:
            Geocoding result with address, or None if not found

        Raises:
            BadRequestError: If coordinates are invalid
            NominatimError: On API errors
        """
        # Validate coordinates
        if not -90 <= lat <= 90:
            raise BadRequestError(f"Latitude must be between -90 and 90, got {lat}")

        if not -180 <= lon <= 180:
            raise BadRequestError(f"Longitude must be between -180 and 180, got {lon}")

        if not 0 <= zoom <= 18:
            raise BadRequestError(f"Zoom must be between 0 and 18, got {zoom}")

        # Check cache first
        cache_key = (round(lat, 6), round(lon, 6), zoom)
        cached = cache.get("geocode", *cache_key)
        if cached is not None:
            logger.info(f"Cache hit for reverse_geocode: {lat}, {lon}")
            return cached

        # Make API request
        params = {
            "lat": lat,
            "lon": lon,
            "zoom": zoom,
            "addressdetails": 1,
        }

        result = await self._make_request("/reverse", params)

        # Handle no results
        if not result or "error" in result:
            logger.info(f"No reverse geocoding result for: {lat}, {lon}")
            return None

        # Parse result
        parsed = self._parse_result(result)

        # Cache result (24 hour TTL)
        cache.set("geocode", parsed, CacheTTL.GEOCODE, *cache_key)
        logger.info(f"Reverse geocoded ({lat}, {lon}) -> {parsed.get('display_name')}")

        return parsed


# Global client instance (will be initialized on first use)
_client: Optional[NominatimClient] = None


async def get_client() -> NominatimClient:
    """
    Get or create global Nominatim client instance.

    Returns:
        Shared NominatimClient instance
    """
    global _client
    if _client is None:
        _client = NominatimClient()
    return _client


async def close_client() -> None:
    """Close global Nominatim client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


__all__ = [
    "NominatimClient",
    "NominatimError",
    "RateLimitError",
    "BadRequestError",
    "ServerError",
    "get_client",
    "close_client",
]
