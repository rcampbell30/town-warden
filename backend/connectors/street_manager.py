"""Placeholder connector for Street Manager roadworks data."""

from config import STREET_MANAGER_ENABLED


def fetch_events(update_source_health):
    """
    Return no events until API access is configured.

    Once Street Manager access arrives, this file is where the roadworks
    connector should be implemented without disturbing the main backend.
    """
    if not STREET_MANAGER_ENABLED:
        update_source_health(
            "Street Manager",
            "pending",
            "API registration pending. Connector stub is ready.",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return []

    update_source_health(
        "Street Manager",
        "checking",
        "Street Manager enabled but connector implementation is pending.",
        records_returned=0,
        events_emitted=0,
        new_events_queued=0,
    )
    return []
