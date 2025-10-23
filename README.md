# OpenStreetMap MCP Server

Give your AI assistant geospatial superpowers! This MCP server provides AI agents (like Claude) with comprehensive location-based capabilities using OpenStreetMap and related open-source services.

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## < What Can It Do?

Your AI assistant can now:

- =� **Find any location** - Convert addresses to coordinates and vice versa
- = **Search nearby places** - Find restaurants, hospitals, schools, parks, and more
- =� **Calculate routes** - Get directions for driving, cycling, walking, or public transit
- =� **Compare travel options** - See all transportation modes side-by-side
- <� **Find schools** - Search for educational institutions with filtering by type

All results are formatted in clean, easy-to-read markdown optimized for AI consumption.

## � Quick Start

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [Claude Desktop](https://claude.ai/download) or any MCP-compatible client

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/openstreetmap-mcp.git
   cd openstreetmap-mcp
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment (optional)**
   ```bash
   cp .env.example .env
   # Edit .env if you need custom API endpoints
   ```

### Configure with Claude Desktop

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openstreetmap": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/openstreetmap-mcp",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/openstreetmap-mcp` with the actual path where you cloned the repository.

### Restart Claude Desktop

Restart Claude Desktop to load the MCP server. You should see the OpenStreetMap tools available in Claude's tool palette.

## =� Available Tools

### 1. Geocode - Address to Coordinates

Convert any address to geographic coordinates.

**Example prompts:**
- "What are the coordinates of the Eiffel Tower?"
- "Geocode 1600 Amphitheatre Parkway, Mountain View, CA"

**Returns:**
```markdown
=� Eiffel Tower, 5, Avenue Anatole France, Paris, France
Coordinates: 48.8583701, 2.2944813
Type: tourism / attraction
```

### 2. Reverse Geocode - Coordinates to Address

Convert coordinates back to a human-readable address.

**Example prompts:**
- "What's located at coordinates 40.7128, -74.0060?"
- "Reverse geocode 51.5074, -0.1278"

**Returns:**
```markdown
=� New York City Hall, Manhattan, New York, USA
Country: United States
City: New York
Postcode: 10007
```

### 3. Search Nearby - Find Places

Find points of interest near any location.

**Example prompts:**
- "Find restaurants near 48.8584, 2.2945"
- "Search for hospitals within 2km of the Statue of Liberty"
- "What parks are near Times Square?"

**Supported categories:**
- Dining: restaurant, cafe, bar, pub, fast_food
- Services: hospital, pharmacy, bank, atm, post_office
- Shopping: supermarket, convenience, mall
- Recreation: park, playground, museum, cinema
- Transport: bus_station, subway, parking
- Education: school, university, library
- And many more! See [OSM amenity tags](https://wiki.openstreetmap.org/wiki/Key:amenity)

### 4. Find Schools Nearby

Specialized tool for finding educational institutions.

**Example prompts:**
- "Find primary schools within 1km of 40.7589, -73.9851"
- "Search for universities near Central Park"

**School types:**
- `primary` - Elementary/primary schools
- `secondary` - Middle/high schools
- `university` - Colleges and universities
- `kindergarten` - Preschools
- `all` - All educational institutions

### 5. Calculate Route

Get directions between two locations with multiple transport modes.

**Example prompts:**
- "How do I drive from 48.8584,2.2945 to 48.8606,2.3376?"
- "Give me walking directions from the Louvre to Notre-Dame"
- "What's the cycling route from Brooklyn Bridge to Central Park?"

**Transport modes:**
- `driving` - Car directions with traffic-aware routing
- `cycling` - Bike routes on bike-friendly paths
- `walking` - Pedestrian routes
- `transit` - Public transportation (major cities only)

**Returns:**
```markdown
=� Walking Route: Eiffel Tower to Louvre Museum

Summary:
- Distance: 3.2 km
- Duration: 39 minutes
- Mode: Walking

Turn-by-turn directions:
1. Head northeast on Avenue Anatole France (450m)
2. Turn right onto Pont de la Concorde (280m)
3. Continue straight onto Quai des Tuileries (1.1km)
...
```

### 6. Compare Routes

Compare all transportation options side-by-side to find the best way to travel.

**Example prompts:**
- "Compare all ways to get from 40.7128,-74.0060 to 40.7589,-73.9851"
- "What are my travel options from Times Square to Central Park?"

**Returns:**
```markdown
=� Travel Options from Times Square to Central Park

| Mode     | Distance | Duration | Notes              |
|----------|----------|----------|--------------------|
| =� Car    | 3.2 km   | 12 min   | Fastest in traffic |
| =� Transit | 3.8 km   | 18 min   | 1 subway line      |
| =� Bike   | 3.4 km   | 14 min   | Bike lane available|
| =� Walk   | 3.1 km   | 38 min   | Scenic route       |

=� Recommendation: Transit (fastest with no parking hassle)
```

## =� Example Conversations

Here are some real-world examples of how to use the tools:

### Planning a Trip
```
You: I'm visiting Paris. Find restaurants near the Eiffel Tower.

Claude: [uses geocode tool for "Eiffel Tower, Paris"]
        [uses search_nearby tool with category "restaurant"]

        I found 15 restaurants within 1km of the Eiffel Tower:

        1. Le Jules Verne (250m away)
           Fine dining, Michelin-starred
        2. Caf� de l'Homme (180m away)
           French cuisine with Eiffel Tower views
        ...
```

### Finding Your Way
```
You: How do I get from Notre-Dame to the Arc de Triomphe?

Claude: [uses geocode for both locations]
        [uses compare_routes tool]

        Here are your travel options:
        - Metro (fastest): 22 minutes, 1 transfer
        - Walking: 1 hour 15 minutes, scenic along the Seine
        - Taxi: 15 minutes in current traffic
        - Bike: 30 minutes via riverbank path
```

### Location Research
```
You: I'm looking at apartments near 40.7589,-73.9851.
     What schools are nearby?

Claude: [uses find_schools_nearby tool]
        [uses search_nearby for parks, supermarkets]

        Found 3 schools within 2km:

        Primary Schools:
        - PS 151 (450m) - Public elementary school
        - The Cathedral School (680m) - Private K-8

        High Schools:
        - Trinity School (920m) - Private college prep

        Nearby amenities:
        - 2 supermarkets within 500m
        - Central Park 800m away
        - Multiple subway stations nearby
```

## =� Location Format Guide

The tools require different location formats:

### Address Format (geocoding tools only)
-  "Eiffel Tower, Paris, France"
-  "1600 Amphitheatre Parkway, Mountain View, CA"
-  "Big Ben, London"

### Coordinate Format (search and routing tools)
-  "48.8584,2.2945" (lat,lon)
-  "40.7128, -74.0060" (spaces are ok)
- L "2.2945,48.8584" (wrong order - lon,lat)
- L "48.8584� N, 2.2945� E" (no degree symbols)

**Pro tip**: Use the geocode tool first to convert addresses to coordinates, then use those coordinates for search and routing.

## � Configuration

### Environment Variables

The server works out-of-the-box with public OpenStreetMap services. You can customize these in `.env`:

```bash
# API Endpoints (defaults to public instances)
NOMINATIM_URL=https://nominatim.openstreetmap.org
OVERPASS_URL=https://overpass-api.de/api/interpreter
OSRM_URL=https://router.project-osrm.org
TRANSITLAND_URL=https://transit.land/api/v2

# Server Configuration
PORT=8000
LOG_LEVEL=INFO

# Required User-Agent (identifies your app to OSM services)
USER_AGENT=openstreetmap-mcp/0.1.0
```

### Rate Limits

To comply with OpenStreetMap's [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/):

- **Geocoding**: Maximum 1 request per second (enforced by the server)
- **Other services**: No strict limits, but be respectful
- **Caching**: Responses are cached to minimize API load
  - Geocoding: 24 hours
  - POI searches: 1 hour
  - Routes: 5 minutes

## =� Troubleshooting

### "No results found"

**For geocoding:**
- Make sure the address includes enough detail (city/country)
- Try searching for a well-known landmark nearby
- Check for typos in the address

**For nearby search:**
- Verify coordinates are in "lat,lon" format
- Try increasing the search radius
- Check the category name (use common terms like "restaurant" not "dining")

**For routing:**
- Ensure both locations are accessible by the chosen transport mode
- For transit: only major cities have public transport data
- Try a different transport mode

### "Transit data not available"

Public transit routing requires GTFS data, which is only available for major cities. Try:
- Using a different transport mode (driving, cycling, walking)
- Checking if your city is covered at [Transit.land](https://transit.land/)

### Tools not showing in Claude Desktop

1. Check the config file path is correct for your OS
2. Verify the absolute path to the repository is correct
3. Make sure you restarted Claude Desktop after editing the config
4. Check Claude Desktop's logs for MCP connection errors

### "Rate limit exceeded"

The Nominatim API has a strict 1 request/second limit. The server enforces this automatically, but if you see this error:
- Wait a few seconds between requests
- Cached results won't count toward the limit
- Consider self-hosting Nominatim for higher limits

## < Features & Limitations

###  What Works Great

- Global geocoding coverage (anywhere in the world)
- Comprehensive POI data from OpenStreetMap
- Fast routing for car, bike, and walking
- Intelligent caching for better performance
- Graceful error handling with helpful messages

### � Current Limitations

- **Transit routing**: Only available in major cities with GTFS data
- **Real-time traffic**: Not available (routes use average speeds)
- **Neighborhood analysis**: Coming soon (explore_area, analyze_neighborhood)
- **Route optimization**: Single routes only (no multi-stop optimization yet)

### =. Coming Soon

- Comprehensive neighborhood analysis
- Livability scoring for real estate decisions
- Multi-stop route optimization
- Isochrone calculations (areas reachable in X minutes)
- POI categories along routes

## <� Architecture

This server is built with:

- **FastMCP**: Official Python MCP framework
- **OpenStreetMap APIs**: Nominatim (geocoding), Overpass (POI search)
- **OSRM**: Open Source Routing Machine for car/bike/foot routing
- **Transit.land**: Public transit data aggregator
- **In-memory caching**: Thread-safe TTL cache for performance

All external services used are free and open-source.

## =� Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [OpenStreetMap Wiki](https://wiki.openstreetmap.org/)
- [Nominatim API Docs](https://nominatim.org/release-docs/latest/api/Overview/)
- [OSRM API Docs](http://project-osrm.org/docs/v5.24.0/api/)
- [Transit.land Documentation](https://www.transit.land/documentation)

## > Contributing

Contributions are welcome! See [CLAUDE.md](CLAUDE.md) for developer documentation.

## =� License

MIT License - see [LICENSE](LICENSE) file for details.

## =O Acknowledgments

- [OpenStreetMap](https://www.openstreetmap.org/) - Open geographic data
- [Nominatim](https://nominatim.org/) - Geocoding service
- [OSRM](http://project-osrm.org/) - Routing engine
- [Transit.land](https://transit.land/) - Transit data aggregator
- [jagan-shanmugam/open-streetmap-mcp](https://github.com/jagan-shanmugam/open-streetmap-mcp) - Inspiration for area analysis features

---

**Built with d for the MCP ecosystem**

For issues and feature requests, please [open an issue](https://github.com/yourusername/openstreetmap-mcp/issues).
