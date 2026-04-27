def test_analytics_counts_real_street_manager_events(client, permit_payload, activity_payload):
    client.post("/webhooks/street-manager/permits", json=permit_payload)
    client.post("/webhooks/street-manager/activities", json=activity_payload)

    analytics = client.get("/analytics").json()

    assert analytics["total_events"] == 2
    assert {"source": "Street Manager", "count": 2} in analytics["events_by_source"]
    assert {"type": "infrastructure", "count": 2} in analytics["events_by_type"]
    assert analytics["real_vs_simulated"]["real"] == 2
    assert analytics["real_vs_simulated"]["simulated"] == 0
