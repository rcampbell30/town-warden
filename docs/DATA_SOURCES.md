# Data Sources

Town Warden combines public-source signals into a local civic picture for the
configured town.

## Police.uk

Used for public incident/crime signals near the configured map centre.

Police.uk coordinates are approximate/anonymised. Town Warden maps them into
configured local zones and marks coordinates as approximate.

## Open-Meteo

Used for current weather context near the configured map centre.

Town Warden emits weather events when precipitation or wind thresholds are met.
Weather context is not a replacement for official warnings.

## Street Manager

Used for live street works webhook notifications.

Street Manager records are normalised into infrastructure events, deduplicated,
and filtered to the configured pilot area using authority keywords, relevance
keywords, postcodes, coordinates, and the configured bounding box.

Out-of-area Street Manager records are counted as filtered but do not enter
history, analytics, map data, risk scoring, or agent insights.
