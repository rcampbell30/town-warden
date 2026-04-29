from agents.insights import generate_insights


def source_health(street_manager_status="connected", open_meteo_status="connected"):
    return {
        "Police.uk": {"status": "connected"},
        "Open-Meteo": {"status": open_meteo_status},
        "Street Manager": {"status": street_manager_status},
        "Simulation": {"status": "disabled"},
    }


def test_connected_street_manager_without_recent_events_is_not_pending():
    events = [
        {"source": "Police.uk", "type": "incident", "location": "Town Centre"}
        for _ in range(8)
    ]

    insights = generate_insights(events, {}, source_health("connected"), 0)
    combined_text = " ".join(
        [item.get("source_context", "") for item in insights]
        + [line for item in insights for line in item.get("evidence", [])]
    )

    assert "Pending sources: Street Manager" not in combined_text
    assert "Pending/checking sources: Street Manager" not in combined_text
    assert (
        "Street Manager is connected but has not contributed recent Blackpool-relevant events in this analysis window."
        in combined_text
    )


def test_checking_street_manager_is_labelled_pending_or_checking():
    events = [
        {"source": "Police.uk", "type": "incident", "location": "Town Centre"}
        for _ in range(8)
    ]

    insights = generate_insights(events, {}, source_health("checking"), 0)
    combined_text = " ".join(
        [item.get("source_context", "") for item in insights]
        + [line for item in insights for line in item.get("evidence", [])]
    )

    assert "Pending/checking sources: Street Manager" in combined_text


def test_dominant_police_source_is_still_reported():
    events = (
        [{"source": "Police.uk", "type": "incident", "location": "Town Centre"} for _ in range(7)]
        + [{"source": "Street Manager", "type": "infrastructure", "location": "Promenade"}]
    )

    insights = generate_insights(events, {}, source_health("connected"), 0)
    source_contexts = [item.get("source_context", "") for item in insights]

    assert any("Dominant source is Police.uk" in context for context in source_contexts)


def test_public_insight_text_does_not_contradict_connected_source_health():
    events = [
        {"source": "Police.uk", "type": "incident", "location": "Town Centre"}
        for _ in range(8)
    ]

    insights = generate_insights(events, {}, source_health("connected"), 0)

    for insight in insights:
        text = " ".join([insight.get("source_context", ""), insight.get("summary", ""), *insight.get("evidence", [])])
        assert "Pending sources: Street Manager" not in text
        assert "Sources with errors: Street Manager" not in text
