# OpenStreetMap MCP Server

## Project Overview

This is an MCP (Model Context Protocol) server that provides AI agents with geospatial awareness capabilities using OpenStreetMap and related open-source services.

**Key Features:**
- Geocoding and reverse geocoding
- POI/amenity search near locations
- Multi-modal route calculation (car, bike, foot, public transit)
- Travel mode comparison
- Optimized for LLM consumption (Markdown output)

## Architecture Quick Reference

- **Framework:** FastMCP with configurable transport (stdio or HTTP streamable)
- **Language:** Python 3.13+
- **Package Manager:** uv
- **Deployment:** Stateless design (horizontally scalable)
- **Transport:** STDIO for local CLI usage, HTTP for remote/web deployments
- **Caching:** In-memory TTL cache with thread safety
- **External APIs:** Nominatim, Overpass, OSRM, Transit.land (all public, no auth)
- **Output:** Markdown formatted for LLM parsing
- **Units:** Metric only

## Detailed Documentation

For complete project plan, architecture details, tool specifications, and implementation phases, see:

📋 **[docs/project-plan.md](docs/project-plan.md)**

This document contains:
- Full tool specifications with input/output formats
- Project structure and file organization
- Dependencies and configuration
- Implementation phases and roadmap
- API integration details

## Project Structure

```
openstreetmap-mcp/
├── main.py                    # FastMCP server entry point
├── pyproject.toml             # Project dependencies (uv)
├── uv.lock                    # Locked dependencies
├── .env.example               # Example environment configuration
├── README.md                  # User documentation (TODO)
├── CLAUDE.md                  # This file
├── docs/
│   ├── project-plan.md        # Detailed project plan
│   └── task-breakdown.md      # Implementation tracking
├── src/
│   ├── __init__.py
│   ├── server.py              # MCP server setup and tool registration
│   ├── config.py              # Environment configuration (Pydantic)
│   ├── cache.py               # In-memory TTL cache with threading
│   ├── logging_config.py      # Structured logging setup
│   ├── tools/                 # MCP tool implementations
│   │   ├── __init__.py
│   │   ├── geocoding.py       # geocode, reverse_geocode
│   │   ├── search.py          # search_nearby, find_schools_nearby
│   │   └── routing.py         # calculate_route, compare_routes
│   └── clients/               # External API clients
│       ├── __init__.py
│       ├── nominatim.py       # Geocoding API client
│       ├── overpass.py        # POI search API client
│       ├── osrm.py            # Routing API client (car/bike/foot)
│       └── transit.py         # Transit routing API client
└── .gitignore                 # Git ignore rules
```

## Implementation Status

**Current Phase:** Core functionality complete (6/8 tools implemented)

### Implemented ✓
- [x] Phase 1: Core Infrastructure
  - FastMCP server with stdio transport
  - In-memory TTL cache with namespacing and thread safety
  - Pydantic-based configuration management
  - Structured logging with context
  - Rate limiting for Nominatim (1 req/sec)

- [x] Phase 2: Geocoding
  - `geocode` - Convert address to coordinates
  - `reverse_geocode` - Convert coordinates to address
  - Nominatim client with rate limiting
  - Markdown output formatting

- [x] Phase 3: POI Search
  - `search_nearby` - Find POIs/amenities near location
  - `find_schools_nearby` - Find schools with type filtering
  - Overpass API client
  - Category tag mapping
  - Distance calculation and sorting

- [x] Phase 4: Basic Routing
  - `calculate_route` - Routes for car/bike/foot modes
  - OSRM client implementation
  - Turn-by-turn directions
  - Distance/duration formatting

- [x] Phase 5: Transit Routing
  - Transit mode in `calculate_route`
  - Transit.land API client
  - Multi-leg journey support
  - Graceful degradation when no data available

- [x] Phase 6: Comparison & Polish
  - `compare_routes` - Compare all transportation modes
  - Markdown table optimization
  - Recommendation logic

### Pending Implementation ⏳
- [ ] Phase 7: Area Analysis Tools
  - `explore_area` - Comprehensive neighborhood overview
  - `analyze_neighborhood` - Livability analysis

- [ ] Phase 8: Final Polish & Documentation
  - README.md with usage examples
  - Dockerfile for containerization
  - API documentation
  - Example queries
  - Performance optimization

## Development Conventions

### Code Style
- Use async/await for all I/O operations
- Type hints required for all functions
- Pydantic for configuration and validation
- Structured logging with context
- Thread-safe cache operations

### Error Handling
- Validate input early (coordinates, addresses)
- Retry network errors with exponential backoff
- Respect API rate limits (Nominatim: 1 req/sec strict)
- Return user-friendly error messages in markdown
- Custom exceptions per client (NominatimError, OverpassError, etc.)

### Caching Strategy
Cache TTL values defined in `src/config.py:CacheTTL`:

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Geocoding | 24 hours | Addresses/coordinates rarely change |
| POI search | 1 hour | POI data relatively stable |
| Routes | 5 minutes | Traffic and conditions vary |
| Transit | 5 minutes | Schedules need freshness |

Cache features (implemented in `src/cache.py`):
- Thread-safe operations using RLock
- Namespace prefixes (geocode, poi, route, transit)
- Automatic cleanup of expired entries
- LRU eviction when at capacity
- Statistics tracking (hits, misses, evictions)

### Output Format
Markdown optimized for LLM consumption:
- Use tables for comparisons
- Use emojis for visual scanning (📍 🚗 🚴 🚶 🚌 📊 🏫)
- Structured sections with clear headers
- Concise bullet points
- Avoid prose paragraphs

## MCP Tools Available

### Geocoding (2 tools)
1. **`geocode(address: str, limit: int = 1)`** - Convert address to coordinates
2. **`reverse_geocode(lat: float, lon: float)`** - Convert coordinates to address

### Search (2 tools)
3. **`search_nearby(location: str, category: str, radius_meters: int = 1000, limit: int = 10)`** - Find POIs/amenities near location
4. **`find_schools_nearby(location: str, school_type: str = "all", radius_meters: int = 2000, limit: int = 10)`** - Find schools with type filtering

### Routing (2 tools)
5. **`calculate_route(origin: str, destination: str, mode: str = "driving", include_steps: bool = True)`** - Calculate route between two points
6. **`compare_routes(origin: str, destination: str, include_transit: bool = True)`** - Compare all transportation modes

### Not Yet Implemented (2 tools)
7. **`explore_area`** - Comprehensive neighborhood overview (planned)
8. **`analyze_neighborhood`** - Livability analysis for real estate decisions (planned)

See [docs/project-plan.md](docs/project-plan.md#tool-specifications) for detailed specifications.

## Environment Configuration

Key environment variables (see `.env.example` for complete list):

```bash
# API Endpoints (public instances)
NOMINATIM_URL=https://nominatim.openstreetmap.org
OVERPASS_URL=https://overpass-api.de/api/interpreter
OSRM_URL=https://router.project-osrm.org
TRANSITLAND_URL=https://transit.land/api/v2

# Server Configuration
# Transport: stdio (for local CLI) or http (for remote/web deployments)
TRANSPORT=stdio
HOST=127.0.0.1    # HTTP transport only
PORT=8000         # HTTP transport only
MCP_PATH=/mcp     # HTTP transport only
LOG_LEVEL=INFO

# Required by OSM services
USER_AGENT=openstreetmap-mcp/0.1.0
```

Configuration is managed by `src/config.py` using pydantic-settings:
- Type-safe URL validation
- Environment variable loading from `.env`
- Validation on startup
- Default values for all settings

## Quick Start (Local Development)

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode - default)
uv run python main.py

# Run MCP server (HTTP mode for remote access)
TRANSPORT=http uv run python main.py
# Or set TRANSPORT=http in .env file

# Or install and use with Claude Desktop
# Add to Claude Desktop MCP configuration (see below)
```

### MCP Configuration

#### STDIO Transport (Local Claude Desktop)

Add to Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "openstreetmap": {
      "command": "uv",
      "args": ["--directory", "/path/to/openstreetmap-mcp", "run", "python", "main.py"],
      "env": {
        "USER_AGENT": "openstreetmap-mcp/0.1.0-claude-desktop"
      }
    }
  }
}
```

#### HTTP Streamable Transport (Remote Deployment)

For remote deployments, web services, or multi-client scenarios:

1. **Set environment variables:**
```bash
export TRANSPORT=http
export HOST=0.0.0.0  # or specific IP
export PORT=8000
export MCP_PATH=/mcp
```

2. **Run the server:**
```bash
uv run python main.py
```

3. **Connect MCP clients to:** `http://your-server:8000/mcp`

**Benefits of HTTP Transport:**
- Remote access from multiple clients
- Web-based deployments (Cloud Run, Railway, Fly.io, etc.)
- Horizontal scaling with load balancers
- No local process management required
- Streamable bidirectional communication

**Security Note:** When deploying HTTP transport publicly, consider:
- Using HTTPS/TLS termination (e.g., via reverse proxy)
- Authentication/authorization middleware
- Rate limiting per client
- Network firewalls and security groups

## Important Notes

### API Rate Limiting
- **Nominatim requires 1 req/sec maximum** - token bucket implementation in `src/clients/nominatim.py`
- All OSM services require User-Agent header (configured in settings)
- Cache aggressively to minimize API calls (hit rate target: >40%)

### Transit Routing
- Uses Transit.land API (free tier)
- Coverage varies by city (major cities globally)
- Graceful degradation when data unavailable
- Not real-time (scheduled data only)
- Falls back to informative error messages

### Location Input Formats
- **Geocoding tools** accept street addresses (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
- **Search and routing tools** require "lat,lon" format (e.g., "37.4224764,-122.0842499")
- Use geocoding tools first to convert addresses to coordinates

### Threading and Async
- MCP server runs async (FastMCP handles event loop)
- Cache operations are thread-safe (using RLock)
- All HTTP clients use httpx async
- Rate limiting uses asyncio.sleep

## File Reference (Key Implementation Files)

### Entry Points
- `main.py:1` - Server entry point, signal handling, logging setup
- `src/server.py:1` - MCP server initialization and tool registration

### Core Infrastructure
- `src/config.py:1` - Settings class with validation (Pydantic)
- `src/cache.py:40` - TTLCache class with thread safety
- `src/logging_config.py:1` - Structured logging configuration

### API Clients
- `src/clients/nominatim.py:1` - Geocoding with rate limiting
- `src/clients/overpass.py:1` - POI search with category mapping
- `src/clients/osrm.py:1` - Routing for car/bike/foot
- `src/clients/transit.py:1` - Public transit routing

### MCP Tools
- `src/tools/geocoding.py:1` - geocode, reverse_geocode implementations
- `src/tools/search.py:1` - search_nearby, find_schools_nearby implementations
- `src/tools/routing.py:1` - calculate_route, compare_routes implementations

## Testing the Server

```bash
# Test geocoding
echo '{"method": "tools/call", "params": {"name": "geocode", "arguments": {"address": "Eiffel Tower, Paris"}}}' | uv run python main.py

# Test search
echo '{"method": "tools/call", "params": {"name": "search_nearby", "arguments": {"location": "48.8584,2.2945", "category": "restaurant", "radius_meters": 500}}}' | uv run python main.py

# Test routing
echo '{"method": "tools/call", "params": {"name": "calculate_route", "arguments": {"origin": "48.8584,2.2945", "destination": "48.8606,2.3376", "mode": "walking"}}}' | uv run python main.py
```

## Dependencies

See `pyproject.toml` for complete list. Key dependencies:

```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.12.5",      # MCP protocol implementation
    "httpx>=0.27.0",        # Async HTTP client
    "pydantic>=2.5.0",      # Data validation
    "pydantic-settings>=2.0.0",  # Settings management
    "python-dotenv>=1.0.0", # .env file loading
]
```

## Next Steps for Development

1. **Complete Area Analysis Tools** (Phase 7)
   - Implement `explore_area` in new file `src/tools/analysis.py`
   - Implement `analyze_neighborhood`
   - Register tools in `src/server.py`
   - Add comprehensive POI aggregation

2. **Documentation** (Phase 8)
   - Write comprehensive README.md
   - Add usage examples for each tool
   - Document error handling patterns
   - Add troubleshooting guide

3. **Containerization** (Phase 8)
   - Create Dockerfile based on plan
   - Add health check endpoint
   - Optimize image size
   - Test deployment

4. **Testing**
   - Unit tests for cache logic
   - Integration tests for API clients
   - Mock responses for testing
   - Test rate limiting behavior

## References

### API Documentation
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) - **IMPORTANT: 1 req/sec limit**
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [OSRM API](http://project-osrm.org/docs/v5.24.0/api/)
- [Transit.land API](https://www.transit.land/documentation)

### MCP Protocol
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)

### OSM Resources
- [OpenStreetMap API Usage Policy](https://operations.osmfoundation.org/policies/api/)
- [Map Features](https://wiki.openstreetmap.org/wiki/Map_features) - Categories and tags
- [Amenity Tags](https://wiki.openstreetmap.org/wiki/Key:amenity)
- [Shop Tags](https://wiki.openstreetmap.org/wiki/Key:shop)

### Inspiration
- [jagan-shanmugam/open-streetmap-mcp](https://github.com/jagan-shanmugam/open-streetmap-mcp) - Excellent OSM MCP server that inspired area analysis tools

---

**Version:** 0.1.0
**Status:** Core functionality complete, area analysis pending
**Last Updated:** 2025-10-23
