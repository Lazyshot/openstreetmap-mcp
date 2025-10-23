# OpenStreetMap MCP Server - Project Plan

## Overview

An MCP (Model Context Protocol) server that provides AI agents with geospatial awareness capabilities using OpenStreetMap and related open-source services.

**Deployment Model:** HTTP/SSE transport on Kubernetes cluster
**Design Principle:** Stateless, horizontally scalable, no user-specific features

## Architecture

### Tech Stack

- **Framework:** FastMCP with HTTP/SSE transport
- **Language:** Python 3.11+
- **Package Manager:** uv
- **Caching:** In-memory with TTL
- **Output Format:** Markdown (optimized for LLM consumption)
- **Units:** Metric only

### External Services (Public APIs)

| Service | Purpose | Rate Limits |
|---------|---------|-------------|
| Nominatim | Geocoding & reverse geocoding | 1 req/sec, requires User-Agent |
| Overpass API | POI/amenity search | Varies by instance, ~180s timeout |
| OSRM | Car/bike/foot routing | No strict limits, public demo |
| Transit.land | Public transit routing | Free tier available |

## Tool Specifications

### 1. `geocode`

Convert address to coordinates.

**Parameters:**
- `address` (string, required): Address to geocode
- `limit` (int, optional, default=1): Number of results to return

**Output Format (Markdown):**
```markdown
📍 Location: [Display Name]
- Coordinates: lat, lon
- Type: city/street/building/etc
- Bounding Box: [if relevant]
```

### 2. `reverse_geocode`

Convert coordinates to address.

**Parameters:**
- `lat` (float, required): Latitude
- `lon` (float, required): Longitude

**Output Format (Markdown):**
```markdown
📍 Address: [Formatted Address]
- Country: ...
- City: ...
- Postcode: ...
```

### 3. `search_nearby`

Find POIs/amenities near a location.

**Parameters:**
- `location` (string, required): Address or "lat,lon"
- `category` (string, required): Type of place (restaurant, hospital, atm, etc.)
- `radius_meters` (int, optional, default=1000): Search radius
- `limit` (int, optional, default=10): Maximum results

**Output Format (Markdown):**
```markdown
Found X [category] within Ym of [location]:

1. **[Name]** (123m away)
   - Address: ...
   - Type: restaurant/cafe/etc
   - Coordinates: lat, lon

2. **[Name]** (456m away)
   ...
```

### 4. `calculate_route`

Calculate route between two locations.

**Parameters:**
- `origin` (string, required): Starting location
- `destination` (string, required): Ending location
- `mode` (string, required): Transportation mode (car/bike/foot/transit)

**Output Format (Markdown):**
```markdown
🚗 Route from [A] to [B] via [mode]

**Summary:**
- Distance: X.X km
- Duration: X min (estimated)
- Mode: car/bike/foot/transit

**Directions:**
1. Head north on Street Name (500m)
2. Turn right onto Another St (1.2km)
...

[For transit: include stops, transfers, line numbers]
```

### 5. `compare_routes`

Compare all transportation modes between two locations.

**Parameters:**
- `origin` (string, required): Starting location
- `destination` (string, required): Ending location

**Output Format (Markdown):**
```markdown
📊 Travel Options from [A] to [B]

| Mode    | Distance | Duration | Notes               |
|---------|----------|----------|---------------------|
| 🚗 Car   | 5.2 km   | 8 min    | Fastest             |
| 🚌 Transit| 6.1 km   | 25 min   | 2 transfers         |
| 🚴 Bike  | 5.4 km   | 18 min   | Moderate difficulty |
| 🚶 Walk  | 5.1 km   | 62 min   | Direct route        |

💡 Recommendation: [Mode] (reason)
```

### 6. `find_schools_nearby`

Find educational institutions near a location.

**Parameters:**
- `location` (string, required): Address or "lat,lon"
- `school_type` (string, optional): Filter by type (primary, secondary, university, kindergarten)
- `radius_meters` (int, optional, default=2000): Search radius
- `limit` (int, optional, default=10): Maximum results

**Output Format (Markdown):**
```markdown
🏫 Educational Institutions near [location]

Found X schools within Ym:

1. **[School Name]** (450m away)
   - Type: Primary School
   - Address: ...
   - Grades: 1-6 (if available)
   - Coordinates: lat, lon

2. **[School Name]** (820m away)
   - Type: Secondary School
   - Address: ...
   - Coordinates: lat, lon
```

### 7. `explore_area`

Get comprehensive overview of an area including amenities, services, and transportation.

**Parameters:**
- `location` (string, required): Address or "lat,lon"
- `radius_meters` (int, optional, default=1000): Search radius

**Output Format (Markdown):**
```markdown
🗺️ Area Overview: [Location Name]

## Transportation
- 🚌 Transit: X bus stops, Y train stations
- 🚴 Bike: Z bike share stations, bike lanes present
- 🚗 Parking: N parking facilities

## Amenities & Services
- 🏪 Shopping: X supermarkets, Y convenience stores
- 🍽️ Dining: X restaurants, Y cafes
- 🏥 Healthcare: X hospitals, Y pharmacies
- 🏫 Education: X schools, Y libraries

## Recreation
- 🌳 Parks: X parks, Y playgrounds
- 💪 Fitness: X gyms, Y sports facilities

## Key Statistics
- Walkability: High/Medium/Low (based on amenity density)
- Transit Access: Excellent/Good/Limited
```

### 8. `analyze_neighborhood`

Analyze neighborhood livability for real estate and relocation decisions.

**Parameters:**
- `location` (string, required): Address or "lat,lon"
- `priorities` (list[string], optional): Factors to prioritize (e.g., ["schools", "transit", "safety", "shopping"])
- `radius_meters` (int, optional, default=1000): Analysis radius

**Output Format (Markdown):**
```markdown
📊 Neighborhood Analysis: [Location Name]

## Overall Livability Score
⭐⭐⭐⭐ (4/5) - Good neighborhood for families

## Key Factors

### 🚌 Transit Access: Excellent
- 3 bus stops within 500m
- Metro station 600m away
- Average wait time: 8 minutes

### 🏫 Education: Very Good
- 2 primary schools within 1km
- 1 secondary school within 1.5km
- 1 public library nearby

### 🏪 Amenities: Good
- 4 supermarkets within walking distance
- 12 restaurants and cafes
- 2 pharmacies

### 🌳 Green Spaces: Moderate
- 2 parks within 1km
- Limited playgrounds

## Strengths
- Excellent public transportation connectivity
- Good school options for families
- Diverse dining and shopping options

## Considerations
- Limited green spaces for outdoor activities
- High amenity density may indicate busy area

## Best For
- Young professionals using public transit
- Small families prioritizing schools and amenities
```

## Project Structure

```
openstreetmap-mcp/
├── main.py                    # FastMCP server entry point
├── pyproject.toml             # uv dependencies
├── uv.lock                    # Locked dependencies
├── Dockerfile                 # Container image
├── README.md                  # User documentation
├── docs/
│   └── project-plan.md        # This file
├── src/
│   ├── __init__.py
│   ├── server.py              # MCP server setup
│   ├── config.py              # Environment configuration
│   ├── cache.py               # In-memory TTL cache
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── geocoding.py       # geocode, reverse_geocode
│   │   ├── search.py          # search_nearby, find_schools_nearby
│   │   ├── routing.py         # calculate_route, compare_routes
│   │   └── analysis.py        # explore_area, analyze_neighborhood
│   └── clients/
│       ├── __init__.py
│       ├── nominatim.py       # Geocoding API client
│       ├── overpass.py        # POI search API client
│       ├── osrm.py            # Routing API client
│       └── transit.py         # Transit routing API client
└── tests/                     # Future: test suite
```

## Dependencies

### Core Dependencies (pyproject.toml)

```toml
[project]
name = "openstreetmap-mcp"
version = "0.1.0"
description = "MCP server for geospatial awareness using OpenStreetMap"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=0.1.0",
    "httpx>=0.27.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.3.0",
]
```

### Key Library Choices

- **fastmcp**: MCP protocol implementation
- **httpx**: Async HTTP client for API calls
- **uvicorn**: ASGI server for HTTP/SSE transport
- **pydantic**: Configuration validation
- **python-dotenv**: Environment variable loading

## Configuration

### Environment Variables

```bash
# API Endpoints
NOMINATIM_URL=https://nominatim.openstreetmap.org
OVERPASS_URL=https://overpass-api.de/api/interpreter
OSRM_URL=https://router.project-osrm.org
TRANSITLAND_URL=https://transit.land/api/v2

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Cache TTL (seconds)
CACHE_TTL_GEOCODE=86400        # 24 hours (addresses rarely change)
CACHE_TTL_POI=3600             # 1 hour (POIs change occasionally)
CACHE_TTL_ROUTE=300            # 5 minutes (traffic varies)
CACHE_TTL_TRANSIT=300          # 5 minutes (schedules vary)

# Rate Limiting
RATE_LIMIT_NOMINATIM=1.0       # requests per second
REQUEST_TIMEOUT=30             # seconds

# Required by OSM services
USER_AGENT=openstreetmap-mcp/0.1.0
```

### Configuration Rationale

- **Long cache for geocoding**: Addresses/coordinates don't change
- **Short cache for routes**: Traffic and transit schedules vary
- **Nominatim rate limit**: Respect OSM usage policy (1 req/sec)
- **User-Agent**: Required by Nominatim, good practice for all OSM services

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"

# Run server
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Set up FastMCP server with HTTP/SSE transport
- [ ] Implement in-memory cache with TTL
- [ ] Configuration management (env vars)
- [ ] Basic error handling and logging
- [ ] Health endpoint for K8s probes
- [ ] Basic Dockerfile

**Deliverable:** Server starts, responds to health checks, can be containerized

### Phase 2: Geocoding
- [ ] Nominatim client with rate limiting
- [ ] `geocode` tool implementation
- [ ] `reverse_geocode` tool implementation
- [ ] Markdown output formatting
- [ ] Input validation (coordinates, addresses)

**Deliverable:** Can convert addresses ↔ coordinates

### Phase 3: POI Search
- [ ] Overpass API client
- [ ] `search_nearby` tool implementation
- [ ] Category/amenity tag mapping (restaurant, hospital, etc.)
- [ ] Distance calculation and sorting
- [ ] Handle large result sets

**Deliverable:** Can find nearby amenities/POIs

### Phase 4: Basic Routing
- [ ] OSRM client implementation
- [ ] `calculate_route` tool (car/bike/foot modes)
- [ ] Turn-by-turn direction parsing and formatting
- [ ] Route geometry handling
- [ ] Distance/duration formatting

**Deliverable:** Can calculate routes for car/bike/foot

### Phase 5: Transit Routing
- [ ] Transit.land or alternative client
- [ ] Add transit mode to `calculate_route`
- [ ] Transit-specific output (stops, transfers, line numbers)
- [ ] Graceful degradation when transit data unavailable
- [ ] Handle multi-leg journeys

**Deliverable:** Can calculate public transit routes where data available

### Phase 6: Comparison & Polish
- [ ] `compare_routes` tool implementation
- [ ] Optimize markdown tables for LLM parsing
- [ ] Recommendation logic (fastest, cheapest, etc.)
- [ ] Comprehensive error messages

**Deliverable:** All routing tools functional

### Phase 7: Area Analysis Tools
- [ ] `find_schools_nearby` tool implementation
- [ ] School type filtering and classification
- [ ] `explore_area` tool implementation
- [ ] Aggregate multiple Overpass queries efficiently
- [ ] `analyze_neighborhood` tool implementation
- [ ] Livability scoring algorithm
- [ ] Priority-based analysis logic

**Deliverable:** All analysis tools functional

### Phase 8: Final Polish & Documentation
- [ ] User documentation (README)
- [ ] API documentation
- [ ] Example queries for each tool
- [ ] Dockerfile optimization
- [ ] Performance optimization

**Deliverable:** Production-ready MCP server

## Key Implementation Details

### In-Memory Cache Design

```python
# Simple TTL cache structure
cache = {
    'geocode:sha256(address)': {
        'data': {...},
        'expires': timestamp
    },
    'route:sha256(origin+dest+mode)': {
        'data': {...},
        'expires': timestamp
    }
}
```

**Cache Key Strategy:**
- Hash inputs to create cache keys
- Namespace by operation type (geocode, route, etc.)
- Periodic cleanup of expired entries
- Thread-safe access (if needed)

### Rate Limiting (Nominatim)

**Token Bucket Approach:**
```python
last_nominatim_request = 0
min_interval = 1.0  # seconds

async def nominatim_request():
    now = time.time()
    elapsed = now - last_nominatim_request
    if elapsed < min_interval:
        await asyncio.sleep(min_interval - elapsed)
    # make request
    last_nominatim_request = time.time()
```

### Error Handling Strategy

| Error Type | Strategy | User Message |
|------------|----------|--------------|
| Network timeout | Retry 3x with exponential backoff | "Service temporarily unavailable, please try again" |
| API rate limit | Wait and retry once | "Request queued due to rate limiting" |
| Invalid input | Validate early, no retry | "Invalid coordinates: must be -90 to 90 for latitude" |
| Service down | Fail fast | "Geocoding service unavailable" |
| No results found | Return empty gracefully | "No results found for [query]" |

### Markdown Output Guidelines

**Optimize for LLM consumption:**
- ✅ Use consistent structure (headers, bullets, tables)
- ✅ Clear hierarchy (H2 for sections, H3 for subsections)
- ✅ Tables for comparisons (easy to parse)
- ✅ Emojis for visual scanning (🚗 🚴 🚶 🚌 📍 📊)
- ✅ Concise but complete information
- ❌ Avoid prose paragraphs
- ❌ Avoid unnecessary formatting (bold/italic overuse)
- ❌ Avoid ambiguous abbreviations

**Example - Good:**
```markdown
**Summary:**
- Distance: 5.2 km
- Duration: 18 min
```

**Example - Poor:**
```markdown
The route is approximately five point two kilometers and will take
you about eighteen minutes to complete under normal conditions.
```

## Public Transit Routing Considerations

### Challenge
Public transit routing requires:
- GTFS (General Transit Feed Specification) data
- Schedule information
- Real-time updates (ideally)
- Complex multi-modal routing

### Solution Options

**Option 1: Transit.land API (Recommended)**
- Free tier available
- RESTful API
- Coverage: Major cities globally
- Limitations: Not real-time, coverage varies

**Option 2: Graceful Degradation**
- Use Overpass to find nearby transit stops
- Provide basic info (stop locations, route numbers)
- Inform user: "Real-time transit routing unavailable for this area"

**Option 3: Hybrid**
- Use Transit.land where available
- Fall back to basic transit stop info from Overpass
- Clear messaging about data availability

**Implementation:** Start with Option 1, implement Option 2 as fallback

### Transit Output Format

```markdown
🚌 Transit Route from [A] to [B]

**Summary:**
- Distance: 6.1 km
- Duration: 25 min (estimated)
- Transfers: 2
- Cost: ~2.50 EUR (estimated)

**Itinerary:**
1. Walk to Main St Station (200m, 3 min)
2. Take Line 5 towards Central Station (4 stops, 12 min)
3. Transfer to Line 12 at Central Station
4. Take Line 12 towards West End (2 stops, 7 min)
5. Walk to destination (150m, 3 min)

⚠️ Note: Based on scheduled times, check real-time updates
```

## Deployment Considerations

### Kubernetes Features to Leverage
- **Horizontal Pod Autoscaling**: Scale based on CPU/memory
- **Health Probes**: Liveness and readiness checks
- **ConfigMaps**: Externalize API URLs, cache TTLs
- **Secrets**: Store any API keys (if added later)
- **Resource Limits**: Prevent memory leaks from cache growth

### Monitoring & Observability
- Health endpoint: `/health` (for K8s probes)
- Metrics endpoint: `/metrics` (future: Prometheus)
- Structured logging (JSON format for log aggregation)
- Request tracing (correlation IDs)

### Scaling Characteristics
- **Stateless**: Each pod independent
- **Cache**: In-memory per pod (some duplication acceptable)
- **Rate limiting**: Per-pod (distributed = lower individual rates)
- **CPU-bound**: Mostly I/O wait (network requests)
- **Memory**: Bounded by cache size (configurable max entries)

## Future Enhancements (Post-MVP)

### Potential Features
- [ ] Redis-backed shared cache (for multi-pod efficiency)
- [ ] Self-hosted OSM services (Nominatim, OSRM, Overpass)
- [ ] Elevation data for routes
- [ ] Historical traffic patterns
- [ ] Isochrone calculations (areas reachable in X minutes)
- [ ] Route optimization (multiple stops)
- [ ] Export routes to GPX/KML format
- [ ] Prometheus metrics
- [ ] Distributed rate limiting (Redis)

### Integration Opportunities
- Weather data along routes
- Points of interest along routes
- Alternative route suggestions
- Carbon footprint estimates
- Accessibility information

## Success Criteria

### MVP (Minimum Viable Product)
- ✅ All 8 tools implemented and functional
  - Geocoding (geocode, reverse_geocode)
  - Search (search_nearby, find_schools_nearby)
  - Routing (calculate_route, compare_routes)
  - Analysis (explore_area, analyze_neighborhood)
- ✅ Geocoding works globally
- ✅ POI search works for common categories
- ✅ Routing works for car/bike/foot modes
- ✅ Transit routing works for major cities (with graceful degradation)
- ✅ Area analysis provides actionable insights
- ✅ Consistent markdown output across all tools
- ✅ Containerized and deployable to K8s
- ✅ Health checks functional
- ✅ Basic error handling

### Production Ready
- ✅ Comprehensive error handling
- ✅ Cache hit rate > 40% (reduces API load)
- ✅ Response time < 5s for 95th percentile
- ✅ Documentation complete
- ✅ Rate limiting respected (no API bans)
- ✅ Graceful degradation when services unavailable

## References

### API Documentation
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [OSRM API](http://project-osrm.org/docs/v5.24.0/api/)
- [Transit.land API](https://www.transit.land/documentation)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

### OSM Tagging Reference
- [Map Features](https://wiki.openstreetmap.org/wiki/Map_features) - Categories and tags
- [Amenity Tags](https://wiki.openstreetmap.org/wiki/Key:amenity)
- [Shop Tags](https://wiki.openstreetmap.org/wiki/Key:shop)

### MCP Protocol
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)

### Inspiration & Prior Art
- [jagan-shanmugam/open-streetmap-mcp](https://github.com/jagan-shanmugam/open-streetmap-mcp) - Excellent OSM MCP server implementation that inspired the area analysis tools (`explore_area`, `analyze_neighborhood`, `find_schools_nearby`)
