"""Primary wardens that watch direct event types."""


def count_events_by_location(events, event_type=None):
    counts = {}

    for event in events:
        if event_type and event["type"] != event_type:
            continue

        location = event["location"]
        counts[location] = counts.get(location, 0) + 1

    return counts


def infrastructure_warden(events):
    alerts = []
    counts = count_events_by_location(events, "infrastructure")

    for location, count in counts.items():
        if count >= 3:
            alerts.append({
                "type": "agent_signal",
                "agent": "Infrastructure Warden",
                "location": location,
                "message": f"Infrastructure degradation cluster detected: {count} recent reports",
                "severity": "high",
                "triggers": ["transport"],
                "score_impact": 10,
            })

    return alerts


def waste_warden(events):
    alerts = []
    counts = count_events_by_location(events, "waste")

    for location, count in counts.items():
        if count >= 2:
            alerts.append({
                "type": "agent_signal",
                "agent": "Waste Warden",
                "location": location,
                "message": f"Waste reliability issue detected: {count} recent reports",
                "severity": "medium",
                "triggers": ["public_health"],
                "score_impact": 5,
            })

    return alerts


def incident_warden(events):
    alerts = []
    counts = count_events_by_location(events, "incident")

    for location, count in counts.items():
        if count >= 2:
            alerts.append({
                "type": "agent_signal",
                "agent": "Incident Warden",
                "location": location,
                "message": f"Incident concentration detected: {count} recent reports",
                "severity": "high",
                "triggers": ["emergency_pressure"],
                "score_impact": 10,
            })

    return alerts


def weather_warden(events):
    alerts = []
    counts = count_events_by_location(events, "weather")

    for location, count in counts.items():
        if count >= 1:
            alerts.append({
                "type": "agent_signal",
                "agent": "Weather Warden",
                "location": location,
                "message": f"Weather pressure detected: {count} recent weather signals",
                "severity": "medium",
                "triggers": ["transport", "infrastructure"],
                "score_impact": 5,
            })

    return alerts
