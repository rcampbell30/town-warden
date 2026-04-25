"""Trend detection agent."""

from agents.primary import count_events_by_location


def trend_warden(events):
    alerts = []

    if len(events) < 10:
        return alerts

    midpoint = len(events) // 2
    older_window = events[:midpoint]
    newer_window = events[midpoint:]

    older_counts = count_events_by_location(older_window)
    newer_counts = count_events_by_location(newer_window)

    for location, newer_count in newer_counts.items():
        older_count = older_counts.get(location, 0)

        if newer_count >= older_count + 3:
            alerts.append({
                "type": "trend_signal",
                "agent": "Trend Warden",
                "location": location,
                "message": f"Escalating trend detected: {older_count} earlier signals -> {newer_count} recent signals",
                "severity": "high",
                "caused_by": "event_velocity",
                "score_impact": 12,
            })

        elif newer_count >= older_count + 2:
            alerts.append({
                "type": "trend_signal",
                "agent": "Trend Warden",
                "location": location,
                "message": f"Rising trend detected: {older_count} earlier signals -> {newer_count} recent signals",
                "severity": "medium",
                "caused_by": "event_velocity",
                "score_impact": 6,
            })

    return alerts
