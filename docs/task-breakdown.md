# OpenStreetMap MCP Server - Task Breakdown

## Overview

This document breaks down the project into discrete tasks, identifies dependencies, and assigns priorities to enable efficient parallel development.

## Priority Levels

- **P0 (Critical Path)**: Must be completed first, blocks other work
- **P1 (High)**: Core functionality, should be done early
- **P2 (Medium)**: Important but not blocking
- **P3 (Low)**: Nice to have, can be deferred

## Dependency Legend

- **Depends on**: Must wait for these tasks to complete
- **Blocks**: Other tasks waiting on this one
- **Can parallel with**: Can be worked on simultaneously

---

## Phase 1: Core Infrastructure

### INFRA-1: Project Setup & Dependencies
**Priority:** P0 (Critical Path)
**Depends on:** None
**Blocks:** All other tasks

**Tasks:**
- [ ] Initialize pyproject.toml with all dependencies
- [ ] Create uv.lock file
- [ ] Set up project directory structure
- [ ] Create __init__.py files for all packages
- [ ] Basic .gitignore configuration

**Estimate:** 1 hour

---

### INFRA-2: Configuration Management
**Priority:** P0 (Critical Path)
**Depends on:** INFRA-1
**Blocks:** INFRA-3, INFRA-4, CLIENT-*

**Tasks:**
- [ ] Create src/config.py with Pydantic models
- [ ] Define all environment variables
- [ ] Implement configuration validation
- [ ] Add default values for optional configs
- [ ] Document required vs optional env vars

**Estimate:** 2 hours

---

### INFRA-3: In-Memory Cache
**Priority:** P0 (Critical Path)
**Depends on:** INFRA-2
**Blocks:** All tool implementations

**Tasks:**
- [ ] Create src/cache.py
- [ ] Implement TTL-based cache with expiration
- [ ] Add cache key generation (hashing strategy)
- [ ] Implement cache cleanup for expired entries
- [ ] Add thread-safety if needed
- [ ] Create cache namespacing by operation type

**Estimate:** 3 hours

---

### INFRA-4: FastMCP Server Setup
**Priority:** P0 (Critical Path)
**Depends on:** INFRA-2
**Blocks:** All tool implementations

**Tasks:**
- [ ] Create main.py entry point
- [ ] Create src/server.py with FastMCP initialization
- [ ] Configure HTTP/SSE transport
- [ ] Set up basic logging (structured JSON)
- [ ] Implement health endpoint (/health)
- [ ] Test server starts and responds

**Estimate:** 3 hours

---

### INFRA-5: Error Handling Framework
**Priority:** P1 (High)
**Depends on:** INFRA-4
**Can parallel with:** CLIENT-*

**Tasks:**
- [ ] Create custom exception classes
- [ ] Implement retry logic with exponential backoff
- [ ] Create error formatting for markdown output
- [ ] Add request timeout handling
- [ ] Implement graceful degradation patterns

**Estimate:** 2 hours

---

### INFRA-6: Dockerfile
**Priority:** P2 (Medium)
**Depends on:** INFRA-1
**Can parallel with:** All other tasks

**Tasks:**
- [ ] Create Dockerfile with Python 3.11-slim base
- [ ] Add uv installation
- [ ] Configure dependency installation
- [ ] Add healthcheck
- [ ] Optimize image layers
- [ ] Test container builds and runs

**Estimate:** 2 hours

---

## Phase 2: API Clients

### CLIENT-1: Nominatim Client
**Priority:** P0 (Critical Path)
**Depends on:** INFRA-2, INFRA-3
**Blocks:** TOOL-1, TOOL-2

**Tasks:**
- [ ] Create src/clients/nominatim.py
- [ ] Implement rate limiting (1 req/sec)
- [ ] Add User-Agent header
- [ ] Implement geocode API call
- [ ] Implement reverse geocode API call
- [ ] Add caching integration
- [ ] Handle API errors and timeouts
- [ ] Add response parsing

**Estimate:** 4 hours

---

### CLIENT-2: Overpass API Client
**Priority:** P1 (High)
**Depends on:** INFRA-2, INFRA-3
**Blocks:** TOOL-3, TOOL-4, TOOL-7, TOOL-8
**Can parallel with:** CLIENT-1

**Tasks:**
- [ ] Create src/clients/overpass.py
- [ ] Implement Overpass QL query builder
- [ ] Add timeout handling (180s default)
- [ ] Implement POI search by category
- [ ] Implement radius-based search
- [ ] Add result parsing and formatting
- [ ] Create OSM tag mapping for common categories
- [ ] Add caching integration
- [ ] Handle "no results" gracefully

**Estimate:** 5 hours

---

### CLIENT-3: OSRM Client
**Priority:** P1 (High)
**Depends on:** INFRA-2, INFRA-3
**Blocks:** TOOL-5, TOOL-6
**Can parallel with:** CLIENT-1, CLIENT-2

**Tasks:**
- [ ] Create src/clients/osrm.py
- [ ] Implement route calculation for car profile
- [ ] Implement route calculation for bike profile
- [ ] Implement route calculation for foot profile
- [ ] Parse turn-by-turn directions
- [ ] Extract distance and duration
- [ ] Handle route geometry (polyline decoding)
- [ ] Add caching integration
- [ ] Handle routing failures (no route found)

**Estimate:** 5 hours

---

### CLIENT-4: Transit Client
**Priority:** P1 (High)
**Depends on:** INFRA-2, INFRA-3
**Blocks:** TOOL-5, TOOL-6
**Can parallel with:** CLIENT-1, CLIENT-2, CLIENT-3

**Tasks:**
- [ ] Create src/clients/transit.py
- [ ] Research Transit.land API v2
- [ ] Implement transit routing API call
- [ ] Parse transit itinerary (stops, transfers, lines)
- [ ] Extract transit-specific metadata
- [ ] Add graceful degradation (when transit unavailable)
- [ ] Add caching integration
- [ ] Handle multi-leg journeys

**Estimate:** 6 hours (includes API research)

---

## Phase 3: Geocoding Tools

### TOOL-1: Geocode Tool
**Priority:** P0 (Critical Path)
**Depends on:** INFRA-4, CLIENT-1
**Blocks:** TOOL-3, TOOL-4, TOOL-5, TOOL-6, TOOL-7, TOOL-8

**Tasks:**
- [ ] Create src/tools/geocoding.py
- [ ] Implement geocode tool function
- [ ] Add input validation (address string)
- [ ] Call Nominatim client
- [ ] Format output as markdown
- [ ] Handle multiple results (limit parameter)
- [ ] Add error handling
- [ ] Register tool with FastMCP server

**Estimate:** 2 hours

---

### TOOL-2: Reverse Geocode Tool
**Priority:** P1 (High)
**Depends on:** INFRA-4, CLIENT-1
**Can parallel with:** TOOL-1

**Tasks:**
- [ ] Implement reverse_geocode tool function
- [ ] Add input validation (lat/lon)
- [ ] Validate coordinate bounds (-90 to 90, -180 to 180)
- [ ] Call Nominatim client
- [ ] Format output as markdown
- [ ] Handle "no address found"
- [ ] Register tool with FastMCP server

**Estimate:** 2 hours

---

## Phase 4: Search Tools

### TOOL-3: Search Nearby Tool
**Priority:** P1 (High)
**Depends on:** INFRA-4, CLIENT-1, CLIENT-2, TOOL-1
**Blocks:** TOOL-7, TOOL-8

**Tasks:**
- [ ] Create src/tools/search.py
- [ ] Implement search_nearby tool function
- [ ] Parse location (address or coordinates)
- [ ] Geocode if address provided
- [ ] Build Overpass query for category
- [ ] Calculate distances from center point
- [ ] Sort results by distance
- [ ] Format output as markdown with distances
- [ ] Handle "no results found"
- [ ] Register tool with FastMCP server

**Estimate:** 4 hours

---

### TOOL-4: Find Schools Nearby Tool
**Priority:** P2 (Medium)
**Depends on:** INFRA-4, CLIENT-1, CLIENT-2, TOOL-1
**Can parallel with:** TOOL-3

**Tasks:**
- [ ] Implement find_schools_nearby tool function
- [ ] Add school type filtering logic
- [ ] Map school types to OSM tags (amenity=school, etc.)
- [ ] Parse location (address or coordinates)
- [ ] Build Overpass query for schools
- [ ] Extract school metadata (grades, type)
- [ ] Format output as markdown
- [ ] Register tool with FastMCP server

**Estimate:** 3 hours

---

## Phase 5: Routing Tools

### TOOL-5: Calculate Route Tool
**Priority:** P1 (High)
**Depends on:** INFRA-4, CLIENT-1, CLIENT-3, CLIENT-4, TOOL-1
**Blocks:** TOOL-6

**Tasks:**
- [ ] Create src/tools/routing.py
- [ ] Implement calculate_route tool function
- [ ] Add mode validation (car/bike/foot/transit)
- [ ] Parse origin and destination
- [ ] Geocode if addresses provided
- [ ] Route dispatcher by mode
- [ ] Call OSRM client for car/bike/foot
- [ ] Call Transit client for transit mode
- [ ] Format turn-by-turn directions as markdown
- [ ] Handle different output formats per mode
- [ ] Add transit-specific formatting (stops, transfers)
- [ ] Register tool with FastMCP server

**Estimate:** 5 hours

---

### TOOL-6: Compare Routes Tool
**Priority:** P2 (Medium)
**Depends on:** INFRA-4, TOOL-5
**Blocks:** None

**Tasks:**
- [ ] Implement compare_routes tool function
- [ ] Call calculate_route for all modes (car/bike/foot/transit)
- [ ] Handle failures for individual modes gracefully
- [ ] Aggregate results into comparison table
- [ ] Implement recommendation logic
- [ ] Format output as markdown table
- [ ] Add mode-specific notes
- [ ] Register tool with FastMCP server

**Estimate:** 3 hours

---

## Phase 6: Area Analysis Tools

### TOOL-7: Explore Area Tool
**Priority:** P2 (Medium)
**Depends on:** INFRA-4, CLIENT-1, CLIENT-2, TOOL-1, TOOL-3
**Can parallel with:** TOOL-8

**Tasks:**
- [ ] Create src/tools/analysis.py
- [ ] Implement explore_area tool function
- [ ] Parse location (address or coordinates)
- [ ] Build multiple Overpass queries (batched if possible)
- [ ] Query for transportation (transit stops, bike stations, parking)
- [ ] Query for amenities (shops, dining, healthcare, education)
- [ ] Query for recreation (parks, gyms, sports)
- [ ] Aggregate and count results by category
- [ ] Calculate walkability score (amenity density)
- [ ] Assess transit access (stop count, proximity)
- [ ] Format comprehensive markdown report
- [ ] Register tool with FastMCP server

**Estimate:** 6 hours

---

### TOOL-8: Analyze Neighborhood Tool
**Priority:** P2 (Medium)
**Depends on:** INFRA-4, CLIENT-1, CLIENT-2, TOOL-1, TOOL-3
**Can parallel with:** TOOL-7

**Tasks:**
- [ ] Implement analyze_neighborhood tool function
- [ ] Parse location and priorities
- [ ] Reuse explore_area logic for data gathering
- [ ] Implement livability scoring algorithm
- [ ] Weight scores by user priorities
- [ ] Generate factor-specific scores (transit, education, amenities, green space)
- [ ] Identify strengths and considerations
- [ ] Generate "best for" recommendations
- [ ] Format detailed markdown analysis
- [ ] Register tool with FastMCP server

**Estimate:** 6 hours

---

## Phase 7: Polish & Documentation

### DOC-1: README Documentation
**Priority:** P2 (Medium)
**Depends on:** All TOOL-* tasks
**Blocks:** None

**Tasks:**
- [ ] Write comprehensive README.md
- [ ] Add installation instructions
- [ ] Document all 8 tools with examples
- [ ] Add configuration guide
- [ ] Include deployment instructions
- [ ] Add troubleshooting section
- [ ] Create usage examples for each tool

**Estimate:** 4 hours

---

### DOC-2: API Documentation
**Priority:** P3 (Low)
**Depends on:** All TOOL-* tasks
**Can parallel with:** DOC-1

**Tasks:**
- [ ] Document tool parameters and types
- [ ] Add example requests and responses
- [ ] Document error messages
- [ ] Create integration guide

**Estimate:** 3 hours

---

### POLISH-1: Performance Optimization
**Priority:** P2 (Medium)
**Depends on:** All TOOL-* tasks
**Can parallel with:** DOC-*

**Tasks:**
- [ ] Profile cache hit rates
- [ ] Optimize Overpass queries
- [ ] Tune cache TTL values
- [ ] Add request batching where possible
- [ ] Optimize markdown formatting
- [ ] Memory profiling

**Estimate:** 4 hours

---

### TEST-1: Integration Testing
**Priority:** P3 (Low)
**Depends on:** All TOOL-* tasks
**Can parallel with:** DOC-*, POLISH-1

**Tasks:**
- [ ] Create test suite structure
- [ ] Add tests for each tool
- [ ] Add tests for caching
- [ ] Add tests for error handling
- [ ] Add tests for rate limiting
- [ ] Mock external API calls

**Estimate:** 8 hours

---

## Task Execution Order

### Critical Path (Do First, Sequential)
1. **INFRA-1** → **INFRA-2** → **INFRA-3** + **INFRA-4** (parallel) → **CLIENT-1** → **TOOL-1**

This establishes the foundation and enables the geocoding tool, which is required by almost all other tools.

### Wave 1: Core Infrastructure (Sequential)
1. INFRA-1: Project setup
2. INFRA-2: Configuration
3. INFRA-3 + INFRA-4 (parallel): Cache + Server setup

**Total: ~8 hours**

### Wave 2: Clients (Parallel)
All can be done simultaneously after Wave 1:
- CLIENT-1: Nominatim (4h)
- CLIENT-2: Overpass (5h)
- CLIENT-3: OSRM (5h)
- CLIENT-4: Transit (6h)

**Total: 6 hours (parallel) or 20 hours (sequential)**

### Wave 3: Error Handling + Geocoding Tools (Parallel)
After CLIENT-1 is ready:
- INFRA-5: Error handling (2h)
- TOOL-1: Geocode (2h)
- TOOL-2: Reverse geocode (2h)

**Total: 2 hours (parallel) or 6 hours (sequential)**

### Wave 4: Search Tools (Parallel)
After CLIENT-2 and TOOL-1 are ready:
- TOOL-3: Search nearby (4h)
- TOOL-4: Find schools nearby (3h)

**Total: 4 hours (parallel) or 7 hours (sequential)**

### Wave 5: Routing Tools (Sequential)
After CLIENT-3, CLIENT-4, and TOOL-1 are ready:
1. TOOL-5: Calculate route (5h)
2. TOOL-6: Compare routes (3h) - depends on TOOL-5

**Total: 8 hours**

### Wave 6: Analysis Tools (Parallel)
After CLIENT-2, TOOL-1, and TOOL-3 are ready:
- TOOL-7: Explore area (6h)
- TOOL-8: Analyze neighborhood (6h)

**Total: 6 hours (parallel) or 12 hours (sequential)**

### Wave 7: Polish (Parallel)
After all tools complete:
- DOC-1: README (4h)
- DOC-2: API docs (3h)
- POLISH-1: Performance (4h)
- TEST-1: Testing (8h)

**Total: 8 hours (parallel) or 19 hours (sequential)**

### Wave 8: Docker (Can start anytime after INFRA-1)
- INFRA-6: Dockerfile (2h)

---

## Summary

### Total Estimated Time
- **Sequential execution:** ~78 hours
- **Optimal parallel execution:** ~40 hours (with 2-3 developers)
- **Single developer (realistic):** ~50-60 hours

### Critical Path Tasks (Must complete first)
1. INFRA-1 (1h)
2. INFRA-2 (2h)
3. INFRA-3 or INFRA-4 (3h)
4. CLIENT-1 (4h)
5. TOOL-1 (2h)

**Critical path minimum:** 12 hours

### Recommended First Sprint (MVP)
To get a working demo quickly:
1. Wave 1: Infrastructure (8h)
2. CLIENT-1 + CLIENT-2 (9h parallel, or prioritize CLIENT-1)
3. TOOL-1 + TOOL-2 + TOOL-3 (8h)
4. INFRA-6: Dockerfile (2h)

**Total for basic MVP:** ~27 hours (geocoding + POI search working)

### Recommended Second Sprint (Routing)
1. CLIENT-3 + CLIENT-4 (11h parallel)
2. TOOL-5 + TOOL-6 (8h)

**Total:** ~19 hours (adds routing capabilities)

### Recommended Third Sprint (Analysis + Polish)
1. TOOL-7 + TOOL-8 (12h parallel)
2. DOC-1 + POLISH-1 (8h parallel)

**Total:** ~20 hours (adds analysis tools and documentation)

---

## Dependency Graph

```
INFRA-1
  ├─→ INFRA-2
  │     ├─→ INFRA-3
  │     ├─→ INFRA-4
  │     │     ├─→ TOOL-1 ←─ CLIENT-1 ←─┐
  │     │     ├─→ TOOL-2 ←─────────────┤
  │     │     ├─→ TOOL-3 ←─ CLIENT-2 ←─┤
  │     │     ├─→ TOOL-4 ←─────────────┤
  │     │     ├─→ TOOL-5 ←─ CLIENT-3 ←─┤
  │     │     │           └─ CLIENT-4 ←─┤
  │     │     ├─→ TOOL-6 (depends on TOOL-5)
  │     │     ├─→ TOOL-7 ←───────────────┤
  │     │     └─→ TOOL-8 ←───────────────┤
  │     │                                 │
  │     └─→ CLIENT-* (all depend on INFRA-2, INFRA-3)
  │
  └─→ INFRA-6 (Dockerfile, independent)

All TOOL-* → DOC-*, POLISH-*, TEST-*
```

---

## Risk Assessment

### High Risk
- **CLIENT-4 (Transit)**: API may have limited coverage or be unreliable
  - **Mitigation**: Implement graceful degradation early

### Medium Risk
- **CLIENT-2 (Overpass)**: Complex query building, potential timeouts
  - **Mitigation**: Start with simple queries, add complexity incrementally

- **TOOL-7/TOOL-8 (Analysis)**: Scoring algorithms subjective
  - **Mitigation**: Use simple heuristics initially, can refine later

### Low Risk
- **INFRA-***: Well-defined, standard implementations
- **CLIENT-1 (Nominatim)**: Mature API, well-documented
- **CLIENT-3 (OSRM)**: Mature API, straightforward

---

## Quick Wins (High Value, Low Effort)

1. **INFRA-6 (Dockerfile)**: Can be done early, enables deployment testing
2. **TOOL-2 (Reverse geocode)**: Simple, same client as TOOL-1
3. **TOOL-4 (Find schools)**: Specialized version of TOOL-3
4. **INFRA-5 (Error handling)**: Improves all subsequent work

---

## Notes

- **Cache is critical**: INFRA-3 must be solid before scaling tool development
- **Geocoding is foundational**: TOOL-1 is required by almost every other tool
- **Overpass is complex**: CLIENT-2 and TOOL-7/TOOL-8 may take longer than estimated
- **Transit is uncertain**: CLIENT-4 needs research; may need to adjust approach
- **Testing deferred**: TEST-1 is P3 to focus on functionality first, but should be added before production
