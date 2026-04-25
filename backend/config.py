"""Central configuration for the Town Warden backend."""

ALLOW_SIMULATION = False

BLACKPOOL_LAT = 53.8175
BLACKPOOL_LNG = -3.0357

POLICE_CANDIDATE_LIMIT = 80
MAX_NEW_EVENTS_PER_FETCH = 8
SOURCE_REFRESH_SECONDS = 60

WEBSOCKET_TICK_SECONDS = 2

# Placeholder for the roadworks connector once Street Manager access is ready.
STREET_MANAGER_ENABLED = False
STREET_MANAGER_API_KEY = None
