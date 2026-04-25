"""Zone-level decision and response agents."""


def critical_zone_warden(risk_map):
    alerts = []
    critical_zones = []

    for location, risk in risk_map.items():
        if risk >= 80:
            alerts.append({
                "type": "zone_signal",
                "agent": "Critical Zone Warden",
                "location": location,
                "message": f"CRITICAL ZONE: systemic stress detected ({round(risk, 1)})",
                "severity": "high",
                "score_impact": 15,
            })
            critical_zones.append(location)

        elif risk >= 50:
            alerts.append({
                "type": "zone_signal",
                "agent": "Critical Zone Warden",
                "location": location,
                "message": f"High-risk zone forming ({round(risk, 1)})",
                "severity": "medium",
                "score_impact": 8,
            })

    return alerts, critical_zones


def response_warden(critical_zones):
    responses = []

    for location in critical_zones:
        responses.append({
            "type": "response_signal",
            "agent": "Response Warden",
            "location": location,
            "message": "Dispatching maintenance teams and rerouting transport",
            "action": "deploy_resources",
            "severity": "high",
            "score_impact": 0,
        })

    return responses
