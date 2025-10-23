"""In-memory TTL cache for API responses with thread safety and namespacing."""

import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""

    value: Any
    expiry_time: datetime
    creation_time: datetime


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class TTLCache:
    """
    Thread-safe in-memory cache with TTL expiration and namespace support.

    Features:
    - Thread-safe operations using RLock
    - Namespace prefixes for different data types
    - Automatic cleanup of expired entries
    - Statistics tracking (hits, misses, evictions)
    - Memory limits with LRU eviction
    - Background cleanup timer
    """

    def __init__(
        self,
        max_size: int = 10000,
        cleanup_interval: int = 60,
    ):
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum number of entries (default: 10000)
            cleanup_interval: Seconds between cleanup runs (default: 60)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval

        # Statistics
        self._stats = CacheStats(max_size=max_size)

        # Start background cleanup timer
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()

        logger.info(
            f"Initialized TTLCache with max_size={max_size}, "
            f"cleanup_interval={cleanup_interval}s"
        )

    def _start_cleanup_timer(self) -> None:
        """Start background cleanup timer."""
        self._cleanup_timer = threading.Timer(
            self._cleanup_interval, self._cleanup_expired
        )
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _cleanup_expired(self) -> None:
        """Remove expired entries and restart timer."""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if entry.expiry_time <= now
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.evictions += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        # Restart timer
        self._start_cleanup_timer()

    def _evict_lru(self) -> None:
        """Evict least recently used entry to make room."""
        if not self._cache:
            return

        # Find oldest entry by creation time
        oldest_key = min(self._cache.items(), key=lambda x: x[1].creation_time)[0]
        del self._cache[oldest_key]
        self._stats.evictions += 1
        logger.debug(f"Evicted LRU entry: {oldest_key[:16]}...")

    def _make_key(self, namespace: str, *args, **kwargs) -> str:
        """
        Create a namespaced cache key from arguments.

        Args:
            namespace: Namespace prefix (e.g., 'geocode', 'poi', 'route', 'transit')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            SHA256 hash of namespace and normalized arguments
        """
        key_data = json.dumps(
            {"namespace": namespace, "args": args, "kwargs": kwargs},
            sort_keys=True,
        )
        hash_value = hashlib.sha256(key_data.encode()).hexdigest()
        return f"{namespace}:{hash_value}"

    def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """
        Get a value from cache if it exists and hasn't expired.

        Args:
            namespace: Namespace prefix
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation

        Returns:
            Cached value if found and valid, None otherwise
        """
        key = self._make_key(namespace, *args, **kwargs)

        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                now = datetime.now()

                if entry.expiry_time > now:
                    self._stats.hits += 1
                    logger.debug(f"Cache hit: {key[:32]}...")
                    return entry.value

                # Expired, remove it
                del self._cache[key]
                self._stats.evictions += 1

            self._stats.misses += 1
            logger.debug(f"Cache miss: {key[:32]}...")
            return None

    def set(
        self, namespace: str, value: Any, ttl_seconds: int, *args, **kwargs
    ) -> None:
        """
        Store a value in cache with a TTL.

        Args:
            namespace: Namespace prefix
            value: Value to cache
            ttl_seconds: Time to live in seconds
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
        """
        key = self._make_key(namespace, *args, **kwargs)

        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                self._evict_lru()

            now = datetime.now()
            entry = CacheEntry(
                value=value,
                expiry_time=now + timedelta(seconds=ttl_seconds),
                creation_time=now,
            )
            self._cache[key] = entry
            self._stats.current_size = len(self._cache)

            logger.debug(
                f"Cache set: {key[:32]}... (TTL: {ttl_seconds}s, size: {len(self._cache)})"
            )

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.current_size = 0
            logger.info(f"Cleared all cache entries ({count} items)")

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all entries in a specific namespace.

        Args:
            namespace: Namespace prefix to clear

        Returns:
            Number of entries cleared
        """
        with self._lock:
            prefix = f"{namespace}:"
            keys_to_delete = [key for key in self._cache if key.startswith(prefix)]

            for key in keys_to_delete:
                del self._cache[key]

            self._stats.current_size = len(self._cache)
            count = len(keys_to_delete)

            if count > 0:
                logger.info(f"Cleared {count} entries from namespace '{namespace}'")

            return count

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats object with current statistics
        """
        with self._lock:
            self._stats.current_size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                current_size=self._stats.current_size,
                max_size=self._stats.max_size,
            )

    def shutdown(self) -> None:
        """Shutdown cache and cleanup timer."""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        self.clear()
        logger.info("Cache shutdown complete")


# Global cache instance
cache = TTLCache()


__all__ = ["cache", "TTLCache", "CacheStats"]
