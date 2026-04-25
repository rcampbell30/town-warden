# Data Sources

## Active

### Police.uk

Used for street-level incident/crime signals near Blackpool.

Town Warden converts records into incident events and maps approximate coordinates into rough Blackpool zones.

### Open-Meteo

Used for current weather pressure.

Town Warden emits weather events when precipitation or wind thresholds are met.

## Pending

### Street Manager

Planned connector for roadworks and street works.

The stub exists at:

```text
backend/connectors/street_manager.py
```

Once API access is available, implement request/auth logic there.
