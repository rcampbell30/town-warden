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


def generate_insights(events, risk_map, source_health, duplicate_count):
    insights = []
    total_events = len(events or [])

    if total_events >= 8:
        location_counts = Counter(event.get("location", "Unknown") for event in events)
        top_location, top_location_count = location_counts.most_common(1)[0]
        location_ratio = _safe_ratio(top_location_count, total_events)

        if location_ratio >= 0.5:
            insights.append({
                "agent": "Pattern Warden",
                "title": "Location concentration detected",
                "summary": (
                    f"{top_location} accounts for {round(location_ratio * 100)}% "
                    f"of recent events ({top_location_count}/{total_events})."
                ),
                "location": top_location,
                "pattern_type": "location_concentration",
                "confidence": _confidence(0.6, location_ratio, 0.5),
                "severity": "warning" if location_ratio >= 0.65 else "info",
                "evidence": [
                    f"recent_events={total_events}",
                    f"{top_location}_events={top_location_count}",
                ],
                "suggested_action": "Review local causes and check whether service pressure is localized.",
                "public_safe": True,
            })

        type_counts = Counter(event.get("type", "unknown") for event in events)
        top_type, top_type_count = type_counts.most_common(1)[0]
        type_ratio = _safe_ratio(top_type_count, total_events)

        if type_ratio >= 0.6:
            insights.append({
                "agent": "Event Type Warden",
                "title": "Event type concentration detected",
                "summary": (
                    f"{top_type} events represent {round(type_ratio * 100)}% "
                    f"of recent activity ({top_type_count}/{total_events})."
                ),
                "location": None,
                "pattern_type": "event_type_concentration",
                "confidence": _confidence(0.62, type_ratio, 0.6),
                "severity": "warning" if type_ratio >= 0.75 else "info",
                "evidence": [
                    f"recent_events={total_events}",
                    f"{top_type}_events={top_type_count}",
                ],
                "suggested_action": "Validate whether this reflects a genuine pattern or a reporting/source skew.",
                "public_safe": True,
            })

    for location, risk in (risk_map or {}).items():
        if 30 <= risk < CRITICAL_RISK_THRESHOLD:
            insights.append({
                "agent": "Risk Warden",
                "title": "Emerging risk pressure",
                "summary": (
                    f"{location} risk is forming at {round(risk, 1)} "
                    f"and is below the critical threshold ({CRITICAL_RISK_THRESHOLD})."
                ),
                "location": location,
                "pattern_type": "emerging_risk",
                "confidence": 0.7 if risk >= 50 else 0.58,
                "severity": "warning" if risk >= 50 else "info",
                "evidence": [f"risk_score={round(risk, 1)}"],
                "suggested_action": "Monitor adjacent alerts and sources before escalation.",
                "public_safe": True,
            })

    for source_name, source in (source_health or {}).items():
        status = str(source.get("status", "")).lower()

        if status in {"disconnected", "rate_limited", "pending"}:
            severity = "warning" if status in {"disconnected", "rate_limited"} else "info"
            insights.append({
                "agent": "Data Quality Warden",
                "title": "Source health may affect insight quality",
                "summary": f"{source_name} is currently {status.replace('_', ' ')}.",
                "location": None,
                "pattern_type": "data_quality",
                "confidence": 0.82 if severity == "warning" else 0.65,
                "severity": severity,
                "evidence": [
                    f"source={source_name}",
                    f"status={status}",
                    f"message={source.get('message', 'n/a')}",
                ],
                "suggested_action": "Treat downstream insights as provisional until source health recovers.",
                "public_safe": False,
            })

    if duplicate_count > 0:
        insights.append({
            "agent": "Deduplication Warden",
            "title": "Repeated source records blocked",
            "summary": (
                f"Deduplication guard has blocked {duplicate_count} repeated source records "
                "from entering live analysis."
            ),
            "location": None,
            "pattern_type": "deduplication",
            "confidence": 0.9,
            "severity": "info",
            "evidence": [f"duplicates_skipped={duplicate_count}"],
            "suggested_action": "Check high-repeat sources for noisy identifiers or overlapping feeds.",
            "public_safe": True,
        })

    return insights
