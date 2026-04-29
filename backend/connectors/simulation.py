"""Optional simulation connector used only when ALLOW_SIMULATION is true."""

import random
from datetime import datetime

from town_config import get_town_config


def generate_event():
    town_config = get_town_config()
    zones = town_config.get("zones", [])
    zone_names = [zone.get("label") or zone.get("name") for zone in zones] or [town_config.get("display_name", "Town")]
    north_zone = next((name for name in zone_names if "north" in name.lower()), zone_names[0])
    south_zone = next((name for name in zone_names if "south" in name.lower()), zone_names[-1])
    centre_zone = next((name for name in zone_names if "centre" in name.lower() or "center" in name.lower()), zone_names[0])

    events = [
        {"type": "infrastructure", "location": north_zone, "text": "simulated pothole reported near a local road"},
        {"type": "infrastructure", "location": north_zone, "text": "simulated road surface cracking reported"},
        {"type": "waste", "location": south_zone, "text": "simulated missed bin collection reported"},
        {"type": "incident", "location": centre_zone, "text": "simulated public incident signal near a local centre"},
        {"type": "transport", "location": south_zone, "text": "simulated bus route delay reported"},
    ]

    event = random.choice(events)
    event["timestamp"] = datetime.now().isoformat()
    event["source"] = "Simulation"
    event["source_event_id"] = f"simulation:{event['type']}:{event['location']}:{datetime.now().timestamp()}"
    event["real_data"] = False
    return event
