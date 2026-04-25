"""Cascade wardens that react to signals from primary wardens."""


def mobility_warden(agent_signals):
    alerts = []

    for signal in agent_signals:
        if "transport" in signal.get("triggers", []):
            alerts.append({
                "type": "cascade_signal",
                "agent": "Mobility Warden",
                "location": signal["location"],
                "message": "Transport risk increased due to upstream civic pressure",
                "severity": "medium",
                "caused_by": signal["agent"],
                "score_impact": 5,
            })

    return alerts


def public_health_warden(agent_signals):
    alerts = []

    for signal in agent_signals:
        if "public_health" in signal.get("triggers", []):
            alerts.append({
                "type": "cascade_signal",
                "agent": "Public Health Warden",
                "location": signal["location"],
                "message": "Public health risk increased due to waste service instability",
                "severity": "medium",
                "caused_by": signal["agent"],
                "score_impact": 5,
            })

    return alerts


def emergency_pressure_warden(agent_signals):
    alerts = []

    for signal in agent_signals:
        if "emergency_pressure" in signal.get("triggers", []):
            alerts.append({
                "type": "cascade_signal",
                "agent": "Emergency Pressure Warden",
                "location": signal["location"],
                "message": "Emergency service pressure rising due to incident concentration",
                "severity": "high",
                "caused_by": signal["agent"],
                "score_impact": 10,
            })

    return alerts
