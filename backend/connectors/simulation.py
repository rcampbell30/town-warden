"""Optional simulation connector used only when ALLOW_SIMULATION is true."""

import random
from datetime import datetime


def generate_event():
    events = [
        {"type": "infrastructure", "location": "North Shore", "text": "simulated pothole reported near promenade"},
        {"type": "infrastructure", "location": "North Shore", "text": "simulated road surface cracking reported"},
        {"type": "waste", "location": "South Shore", "text": "simulated missed bin collection reported"},
        {"type": "incident", "location": "Town Centre", "text": "simulated police incident reported near high street"},
        {"type": "transport", "location": "Blackpool South", "text": "simulated bus route delay reported"},
    ]

    event = random.choice(events)
    event["timestamp"] = datetime.now().isoformat()
    event["source"] = "Simulation"
    event["source_event_id"] = f"simulation:{event['type']}:{event['location']}:{datetime.now().timestamp()}"
    event["real_data"] = False
    return event
