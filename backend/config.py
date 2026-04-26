"""Central configuration for the Town Warden backend."""

import os


def _env_bool(name, default=False):
    raw = os.getenv(name)

    if raw is None:
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


ALLOW_SIMULATION = _env_bool("ALLOW_SIMULATION", False)

BLACKPOOL_LAT = 53.8175
BLACKPOOL_LNG = -3.0357

POLICE_CANDIDATE_LIMIT = _env_int("POLICE_CANDIDATE_LIMIT", 80)
MAX_NEW_EVENTS_PER_FETCH = _env_int("MAX_NEW_EVENTS_PER_FETCH", 8)
SOURCE_REFRESH_SECONDS = _env_int("SOURCE_REFRESH_SECONDS", 60)

WEBSOCKET_TICK_SECONDS = _env_int("WEBSOCKET_TICK_SECONDS", 2)

ENVIRONMENT = os.getenv("ENVIRONMENT", "local").strip().lower()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# Placeholder for the roadworks connector once Street Manager access is ready.
STREET_MANAGER_ENABLED = _env_bool("STREET_MANAGER_ENABLED", False)
STREET_MANAGER_API_KEY = os.getenv("STREET_MANAGER_API_KEY")
