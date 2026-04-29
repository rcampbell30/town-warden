# Federation Public Summary Schema

This document describes a future public-safe summary schema for a possible Town
Warden Network.

The schema is documentation only. Town Warden v1.0 does not implement
federation endpoints or network exchange.

## Core Fields

```json
{
  "node_id": "blackpool",
  "town_name": "Blackpool",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T00:00:00Z",
  "period_end": "2026-04-29T23:59:59Z",
  "signal_type": "location_concentration",
  "severity": "watch",
  "confidence": 0.72,
  "summary": "Repeated public-source incident concentration detected in a local zone.",
  "source_mix": ["Police.uk", "Street Manager"],
  "affected_zone_label": "South Shore",
  "public_safe": true,
  "limitations": [
    "Public-source only.",
    "Police.uk locations are approximate.",
    "Not official public authority advice."
  ]
}
```

## Field Notes

- `node_id`: Stable configured town node identifier.
- `town_name`: Public town display name.
- `generated_at`: Timestamp for when this summary was generated.
- `period_start`: Start of the analysis window.
- `period_end`: End of the analysis window.
- `signal_type`: Summary category, such as `location_concentration`.
- `severity`: Suggested values: `info`, `watch`, `elevated`, `critical`.
- `confidence`: Number from `0` to `1`.
- `summary`: Plain-English public-safe summary.
- `source_mix`: Source labels contributing to the summary.
- `affected_zone_label`: Local zone label when relevant.
- `public_safe`: Must be `true` before sharing outside the local node.
- `limitations`: Required caveats and source constraints.

## Example: Location Concentration

```json
{
  "node_id": "blackpool",
  "town_name": "Blackpool",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T00:00:00Z",
  "period_end": "2026-04-29T12:00:00Z",
  "signal_type": "location_concentration",
  "severity": "watch",
  "confidence": 0.72,
  "summary": "Repeated public-source incident concentration detected in a local zone.",
  "source_mix": ["Police.uk"],
  "affected_zone_label": "Town Centre",
  "public_safe": true,
  "limitations": [
    "Police.uk locations are approximate.",
    "This may reflect reporting patterns or source coverage."
  ]
}
```

## Example: Source Outage

```json
{
  "node_id": "preston",
  "town_name": "Preston",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T11:00:00Z",
  "period_end": "2026-04-29T12:00:00Z",
  "signal_type": "source_outage",
  "severity": "info",
  "confidence": 0.9,
  "summary": "One public-source connector is temporarily unavailable, limiting confidence.",
  "source_mix": ["Open-Meteo"],
  "affected_zone_label": null,
  "public_safe": true,
  "limitations": [
    "This describes source coverage, not civic risk.",
    "No private credentials or raw source data are shared."
  ]
}
```

## Example: Weather Disruption

```json
{
  "node_id": "liverpool",
  "town_name": "Liverpool",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T10:00:00Z",
  "period_end": "2026-04-29T12:00:00Z",
  "signal_type": "weather_disruption",
  "severity": "watch",
  "confidence": 0.68,
  "summary": "Weather context suggests elevated wind or rainfall pressure in the local analysis window.",
  "source_mix": ["Open-Meteo"],
  "affected_zone_label": "Waterfront",
  "public_safe": true,
  "limitations": [
    "Weather context is not an official warning feed.",
    "Use official channels for safety-critical decisions."
  ]
}
```

## Example: Street Works Concentration

```json
{
  "node_id": "blackpool",
  "town_name": "Blackpool",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T00:00:00Z",
  "period_end": "2026-04-29T12:00:00Z",
  "signal_type": "street_works_concentration",
  "severity": "watch",
  "confidence": 0.74,
  "summary": "Several local street works notifications were accepted in the configured pilot area.",
  "source_mix": ["Street Manager"],
  "affected_zone_label": "Promenade",
  "public_safe": true,
  "limitations": [
    "Street Manager payloads may have incomplete location fields.",
    "Out-of-area records are filtered before local analysis."
  ]
}
```

## Example: Cross-Town Pattern Candidate

```json
{
  "node_id": "north-west-regional",
  "town_name": "North West Regional Summary",
  "generated_at": "2026-04-29T12:00:00Z",
  "period_start": "2026-04-29T00:00:00Z",
  "period_end": "2026-04-29T12:00:00Z",
  "signal_type": "cross_town_pattern_candidate",
  "severity": "info",
  "confidence": 0.61,
  "summary": "Several town nodes reported similar public-source transport-hub concentration summaries.",
  "source_mix": ["Police.uk", "Street Manager"],
  "affected_zone_label": null,
  "public_safe": true,
  "limitations": [
    "This is an aggregate pattern candidate, not an official conclusion.",
    "Local context and source coverage may differ between towns."
  ]
}
```

## Sharing Rules

Before a summary is shared beyond the local node, it should satisfy:

- `public_safe` is true.
- No raw payloads are included.
- No personal data is included.
- No secrets or internal URLs are included.
- Limitations are present.
- Confidence is present and conservative.
- The wording does not imply official public authority status.
