[Integration]: Google Maps Platform - Geocoding, Routing & Location Intelligence

# Description
Implements Google Maps Platform integration to enable agents to power logistics, delivery, and location-based workflows. This integration provides access to geocoding, routing, and location intelligence capabilities via the MCP protocol.

## Features
- **Geocoding**: Convert addresses to coordinates (`maps_geocode`) and vice versa (`maps_reverse_geocode`).
- **Routing**: Get detailed directions with multi-stop optimization and mode selection (`maps_directions`).
- **Distance Matrix**: Calculate travel times and distances for multiple origins/destinations (`maps_distance_matrix`).
- **Place Intelligence**: Search for places and retrieve detailed information (`maps_place_search`, `maps_place_details`).

## Tools Added
- `maps_geocode`
- `maps_reverse_geocode`
- `maps_directions`
- `maps_distance_matrix`
- `maps_place_details`
- `maps_place_search`

## Environment Setup
| Variable | Description |
| --- | --- |
| `GOOGLE_MAPS_API_KEY` | Google Maps Platform API key with Geocoding, Directions, Distance Matrix, and Places APIs enabled. |

## Use Cases
- **Logistics**: Calculate delivery ETAs and optimize routes.
- **CRM**: Validate and standardize addresses.
- **Local Services**: Find nearest service locations.

## Testing
- Unit tests included for all tools.
- Covered success scenarios, API errors, and edge cases (rate limits, zero results).
- Key-based authentication flow verified.

## Related Issue
- Resolve #3179
