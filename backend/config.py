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


def _env_float(name, default):
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return float(raw)
    except ValueError:
        return default


ALLOW_SIMULATION = _env_bool("ALLOW_SIMULATION", False)

TOWN_CONFIG = os.getenv("TOWN_CONFIG", "config/towns/blackpool.json").strip() or "config/towns/blackpool.json"
BLACKPOOL_LAT = 53.8175
BLACKPOOL_LNG = -3.0357
TOWN_WARDEN_AREA_NAME = os.getenv("TOWN_WARDEN_AREA_NAME", "Blackpool").strip() or "Blackpool"
TOWN_WARDEN_MIN_LAT = _env_float("TOWN_WARDEN_MIN_LAT", 53.73)
TOWN_WARDEN_MAX_LAT = _env_float("TOWN_WARDEN_MAX_LAT", 53.90)
TOWN_WARDEN_MIN_LNG = _env_float("TOWN_WARDEN_MIN_LNG", -3.10)
TOWN_WARDEN_MAX_LNG = _env_float("TOWN_WARDEN_MAX_LNG", -2.95)

POLICE_CANDIDATE_LIMIT = _env_int("POLICE_CANDIDATE_LIMIT", 80)
MAX_NEW_EVENTS_PER_FETCH = _env_int("MAX_NEW_EVENTS_PER_FETCH", 8)
SOURCE_REFRESH_SECONDS = _env_int("SOURCE_REFRESH_SECONDS", 60)

WEBSOCKET_TICK_SECONDS = _env_int("WEBSOCKET_TICK_SECONDS", 2)

ENVIRONMENT = os.getenv("ENVIRONMENT", "local").strip().lower()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
EVENT_RETENTION_DAYS = _env_int("EVENT_RETENTION_DAYS", 90)
ALERT_RETENTION_DAYS = _env_int("ALERT_RETENTION_DAYS", 90)
RISK_SNAPSHOT_RETENTION_DAYS = _env_int("RISK_SNAPSHOT_RETENTION_DAYS", 30)

# Placeholder for the roadworks connector once Street Manager access is ready.
STREET_MANAGER_ENABLED = _env_bool("STREET_MANAGER_ENABLED", False)
STREET_MANAGER_API_KEY = os.getenv("STREET_MANAGER_API_KEY")
