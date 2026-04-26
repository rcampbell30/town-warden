"""Rule-based developer-facing insight generation."""

from collections import Counter


CRITICAL_RISK_THRESHOLD = 80


def _safe_ratio(count, total):
    if total <= 0:
        return 0
    return count / total


def _confidence(base, ratio, threshold):
    if ratio <= threshold:
        return round(base, 2)

    boost = min(0.4, (ratio - threshold) * 0.8)
    return round(min(0.95, base + boost), 2)


def _source_context(source_health):
    grouped = {
        "connected": [],
        "pending": [],
        "rate_limited": [],
        "disconnected": [],
        "disabled": [],
    }

    for source_name, data in (source_health or {}).items():
        status = str(data.get("status", "unknown")).lower()

        if status in grouped:
            grouped[status].append(source_name)

    return grouped


def _dominant_source(events):
    sources = [event.get("source", "Unknown") for event in (events or [])]

    if not sources:
        return "Unknown", 0

    source_counts = Counter(sources)
    return source_counts.most_common(1)[0]


def generate_insights(events, risk_map, source_health, duplicate_count):
    insights = []
    total_events = len(events or [])
    dominant_source, dominant_count = _dominant_source(events)
    dominant_ratio = _safe_ratio(dominant_count, total_events)
    source_groups = _source_context(source_health)

    source_note = (
        f"Dominant source is {dominant_source} ({round(dominant_ratio * 100)}% of recent events)."
        if total_events > 0
        else "No recent events available yet."
    )

    if source_groups["pending"]:
        source_note += f" Pending sources: {', '.join(source_groups['pending'])}."

    if total_events >= 8:
        location_counts = Counter(event.get("location", "Unknown") for event in events)
        top_location, top_location_count = location_counts.most_common(1)[0]
        location_ratio = _safe_ratio(top_location_count, total_events)

        if location_ratio >= 0.5:
            insights.append({
                "agent": "Pattern Warden",
                "title": "Location concentration signal",
                "summary": (
                    f"{top_location} accounts for {round(location_ratio * 100)}% of recent processed events "
                    f"({top_location_count}/{total_events}). This may reflect source coverage rather than a complete "
                    "real-world distribution, so treat it as an early source-limited pattern."
                ),
                "location": top_location,
                "pattern_type": "location_concentration",
                "confidence": _confidence(0.55, location_ratio, 0.5),
                "severity": "warning" if location_ratio >= 0.65 else "info",
                "evidence": [
                    f"Recent events analysed: {total_events}",
                    f"Events in {top_location}: {top_location_count}",
                    f"Dominant source: {dominant_source}",
                    f"Dominant source share: {round(dominant_ratio * 100)}%",
                ],
                "source_context": source_note,
                "suggested_action": "Cross-check with additional sources before treating this as a confirmed geographic hotspot.",
                "public_safe": True,
            })

        type_counts = Counter(event.get("type", "unknown") for event in events)
        top_type, top_type_count = type_counts.most_common(1)[0]
        type_ratio = _safe_ratio(top_type_count, total_events)

        if type_ratio >= 0.6:
            insights.append({
                "agent": "Event Type Warden",
                "title": "Event type concentration signal",
                "summary": (
                    f"{top_type} events represent {round(type_ratio * 100)}% of recent processed activity "
                    f"({top_type_count}/{total_events}). This can indicate a real emerging pattern, but it can also be "
                    "amplified when one source currently contributes most incoming records."
                ),
                "location": None,
                "pattern_type": "event_type_concentration",
                "confidence": _confidence(0.57, type_ratio, 0.6),
                "severity": "warning" if type_ratio >= 0.75 else "info",
                "evidence": [
                    f"Recent events analysed: {total_events}",
                    f"{top_type} events: {top_type_count}",
                    f"Dominant source: {dominant_source}",
                    f"Street Manager status: {source_health.get('Street Manager', {}).get('status', 'unknown')}",
                ],
                "source_context": source_note,
                "suggested_action": "Treat this as provisional until source balance improves or trend persists over more cycles.",
                "public_safe": True,
            })

    for location, risk in (risk_map or {}).items():
        if 30 <= risk < CRITICAL_RISK_THRESHOLD:
            insights.append({
                "agent": "Risk Warden",
                "title": "Emerging risk signal",
                "summary": (
                    f"{location} has an emerging risk signal at {round(risk, 1)}, below the critical threshold "
                    f"({CRITICAL_RISK_THRESHOLD}). This is an early indicator, not a confirmed incident escalation."
                ),
                "location": location,
                "pattern_type": "emerging_risk",
                "confidence": 0.66 if risk >= 50 else 0.54,
                "severity": "warning" if risk >= 50 else "info",
                "evidence": [
                    f"Risk score: {round(risk, 1)}",
                    f"Recent events analysed: {total_events}",
                    f"Dominant source: {dominant_source}",
                ],
                "source_context": source_note,
                "suggested_action": "Monitor nearby alerts and validate against independent sources before escalation decisions.",
                "public_safe": True,
            })

    if source_health:
        pending = ", ".join(source_groups["pending"]) or "none"
        rate_limited = ", ".join(source_groups["rate_limited"]) or "none"
        disconnected = ", ".join(source_groups["disconnected"]) or "none"
        connected = ", ".join(source_groups["connected"]) or "none"
        simulation_status = source_health.get("Simulation", {}).get("status", "unknown")

        if source_groups["pending"] or source_groups["rate_limited"] or source_groups["disconnected"]:
            insights.append({
                "agent": "Data Quality Warden",
                "title": "Source coverage limits confidence",
                "summary": (
                    "Current insight confidence is constrained by source availability. Treat current patterns as "
                    "source-limited early indicators rather than complete town-wide conclusions."
                ),
                "location": None,
                "pattern_type": "data_quality",
                "confidence": 0.78,
                "severity": "warning",
                "evidence": [
                    f"Connected sources: {connected}",
                    f"Pending sources: {pending}",
                    f"Rate-limited sources: {rate_limited}",
                    f"Disconnected sources: {disconnected}",
                    f"Simulation status: {simulation_status}",
                ],
                "source_context": source_note,
                "suggested_action": "Flag public outputs as experimental until pending or rate-limited sources stabilise.",
                "public_safe": False,
            })

    if duplicate_count > 0:
        insights.append({
            "agent": "Deduplication Warden",
            "title": "Repeated source records filtered",
            "summary": (
                f"Deduplication has filtered {duplicate_count} repeated records from live analysis. "
                "This protects signal quality but also indicates noisy or overlapping source feeds."
            ),
            "location": None,
            "pattern_type": "deduplication",
            "confidence": 0.87,
            "severity": "info",
            "evidence": [
                f"Duplicate records skipped: {duplicate_count}",
                f"Dominant source: {dominant_source}",
            ],
            "source_context": source_note,
            "suggested_action": "Review high-repeat sources for identifier quality and payload overlap.",
            "public_safe": True,
        })

    return insights
