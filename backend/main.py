import asyncio
import hashlib
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.cascade import emergency_pressure_warden, mobility_warden, public_health_warden
from agents.primary import infrastructure_warden, incident_warden, waste_warden, weather_warden
from agents.insights import generate_insights
from agents.trend import trend_warden
from agents.zone import critical_zone_warden, response_warden
from config import (
    ADMIN_TOKEN,
    ALLOW_SIMULATION,
    ENVIRONMENT,
    MAX_NEW_EVENTS_PER_FETCH,
    SOURCE_REFRESH_SECONDS,
    WEBSOCKET_TICK_SECONDS,
)
from connectors import open_meteo, police_uk, simulation, street_manager
from storage import (
    clear_database,
    connect,
    event_exists,
    save_alert,
    save_event,
    save_risk_snapshot,
    setup_database,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://town-warden.netlify.app",
        "https://*.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_database()


history = []
risk_map = {}
real_event_queue = []
agent_log = []
insights = []

duplicate_count = 0
last_source_fetch_time = None
last_wait_log_bucket = None


source_health = {
    "Police.uk": {
        "status": "checking",
        "message": "Waiting for first Police.uk check.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "last_checked": None,
    },
    "Open-Meteo": {
        "status": "checking",
        "message": "Waiting for first Open-Meteo check.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "last_checked": None,
    },
    "Street Manager": {
        "status": "pending",
        "message": "Waiting for live webhook data.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "last_checked": None,
    },
    "Simulation": {
        "status": "enabled" if ALLOW_SIMULATION else "disabled",
        "message": "Simulation fallback enabled." if ALLOW_SIMULATION else "Simulation fallback disabled.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "last_checked": datetime.now().isoformat(),
    },
}


def log_agent(agent, message, level="info"):
    """
    Add an internal system/agent message for the Agent Comms Log.
    """

    agent_log.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "message": message,
        "level": level,
    })

    agent_log[:] = agent_log[-80:]


def log_insight(
    agent,
    title,
    summary,
    location=None,
    pattern_type="general",
    confidence=0.5,
    severity="info",
    evidence=None,
    suggested_action=None,
    source_context=None,
    public_safe=True,
):
    insight = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "title": title,
        "summary": summary,
        "location": location,
        "pattern_type": pattern_type,
        "confidence": confidence,
        "severity": severity,
        "evidence": evidence or [],
        "suggested_action": suggested_action,
        "source_context": source_context,
        "public_safe": public_safe,
    }

    insights.append(insight)
    insights[:] = insights[-100:]

    return insight


log_agent("System", "Town Warden backend started.", "success")


def update_source_health(
    source_name,
    status,
    message,
    records_returned=0,
    events_emitted=0,
    new_events_queued=None,
    duplicates_skipped=None,
):
    current = source_health.get(source_name, {})

    current["status"] = status
    current["message"] = message
    current["records_returned"] = records_returned
    current["events_emitted"] = events_emitted

    if new_events_queued is not None:
        current["new_events_queued"] = new_events_queued

    if duplicates_skipped is not None:
        current["duplicates_skipped"] = duplicates_skipped

    current["last_checked"] = datetime.now().isoformat()
    source_health[source_name] = current


def seconds_until_next_source_refresh():
    if last_source_fetch_time is None:
        return 0

    elapsed = datetime.now() - last_source_fetch_time
    remaining = SOURCE_REFRESH_SECONDS - elapsed.total_seconds()

    return max(0, int(round(remaining)))


def make_payload_fingerprint(prefix, payload):
    """
    Creates a stable fallback ID for webhook payloads.

    If Street Manager does not provide a clean ID field,
    this prevents duplicate webhook payloads being saved repeatedly.
    """

    raw = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return f"{prefix}:{digest}"


def normalise_street_manager_payload(kind, payload):
    """
    Converts a Street Manager webhook payload into a Town Warden event.

    This is defensive because we need to inspect real Street Manager payloads
    before doing more accurate roadworks mapping.
    """

    if not isinstance(payload, dict):
        payload = {"raw_payload": payload}

    possible_id = (
        payload.get("id")
        or payload.get("permitReferenceNumber")
        or payload.get("activityId")
        or payload.get("worksReference")
        or payload.get("reference")
        or payload.get("eventId")
        or payload.get("notificationId")
    )

    source_event_id = (
        f"streetmanager:{kind}:{possible_id}"
        if possible_id
        else make_payload_fingerprint(f"streetmanager:{kind}", payload)
    )

    works_reference = (
        payload.get("worksReference")
        or payload.get("permitReferenceNumber")
        or payload.get("reference")
        or "unknown reference"
    )

    return {
        "type": "infrastructure",
        "location": "Town Centre",
        "text": f"Street Manager {kind} notification received ({works_reference})",
        "timestamp": datetime.now().isoformat(),
        "source": "Street Manager",
        "source_event_id": source_event_id,
        "real_data": True,
    }


def queue_webhook_event(event):
    """
    Save a webhook event and also push it into the live queue if it is new.
    """

    global duplicate_count

    saved = save_event(event)

    if saved:
        real_event_queue.append(event)

        source_health["Street Manager"]["status"] = "connected"
        source_health["Street Manager"]["message"] = (
            "Webhook endpoints are live. Street Manager payload received."
        )
        source_health["Street Manager"]["records_returned"] += 1
        source_health["Street Manager"]["events_emitted"] += 1
        source_health["Street Manager"]["new_events_queued"] += 1
        source_health["Street Manager"]["last_checked"] = datetime.now().isoformat()

        log_agent(
            "Street Manager Connector",
            f"Webhook event saved and queued: {event['source_event_id']}",
            "success",
        )

    else:
        duplicate_count += 1

        source_health["Street Manager"]["status"] = "connected"
        source_health["Street Manager"]["message"] = (
            "Webhook endpoints are live. Duplicate Street Manager payload received and ignored."
        )
        source_health["Street Manager"]["records_returned"] += 1
        source_health["Street Manager"]["duplicates_skipped"] += 1
        source_health["Street Manager"]["last_checked"] = datetime.now().isoformat()

        log_agent(
            "Deduplication Guard",
            f"Skipped duplicate Street Manager webhook: {event['source_event_id']}",
            "warning",
        )

    return saved


def fetch_real_events():
    """
    Fetch all connector events, deduplicate, then return only new events.
    """

    global duplicate_count

    log_agent("Source Monitor", "Source refresh started.", "info")

    fetched_events = []

    fetched_events += police_uk.fetch_events(update_source_health)
    fetched_events += open_meteo.fetch_events(update_source_health)
    fetched_events += street_manager.fetch_events(update_source_health)

    new_events = []
    seen_ids_this_cycle = set()
    duplicates_by_source = {}

    for event in fetched_events:
        source = event.get("source", "unknown")
        source_event_id = event.get("source_event_id")

        if not source_event_id:
            new_events.append(event)
            continue

        if source_event_id in seen_ids_this_cycle or event_exists(source_event_id):
            duplicate_count += 1
            duplicates_by_source[source] = duplicates_by_source.get(source, 0) + 1
            continue

        seen_ids_this_cycle.add(source_event_id)
        new_events.append(event)

        if len(new_events) >= MAX_NEW_EVENTS_PER_FETCH:
            break

    for source, count in duplicates_by_source.items():
        current = source_health.get(source, {})
        current["duplicates_skipped"] = current.get("duplicates_skipped", 0) + count
        current["last_checked"] = datetime.now().isoformat()
        source_health[source] = current

        log_agent(
            "Deduplication Guard",
            f"Skipped {count} duplicate records from {source}.",
            "warning",
        )

    for source_name in ["Police.uk", "Open-Meteo", "Street Manager"]:
        source_new = len([event for event in new_events if event.get("source") == source_name])

        if source_name in source_health:
            base_message = source_health[source_name].get("message", "").split(" New queued:")[0]
            source_health[source_name]["new_events_queued"] = source_new
            source_health[source_name]["message"] = f"{base_message} New queued: {source_new}."

    log_agent(
        "Source Monitor",
        f"Source refresh completed. New queued events: {len(new_events)}.",
        "success",
    )

    return new_events


def force_source_refresh():
    global real_event_queue
    global last_source_fetch_time

    last_source_fetch_time = datetime.now()
    real_event_queue = fetch_real_events()

    log_agent("Developer Controls", f"Manual source refresh queued {len(real_event_queue)} events.", "info")

    return len(real_event_queue)


def _is_local_request(request: Request):
    host = (request.client.host or "").lower() if request.client else ""
    forwarded_for = request.headers.get("x-forwarded-for", "").lower()
    forwarded_host = request.headers.get("x-forwarded-host", "").lower()

    if host in {"127.0.0.1", "localhost", "::1"}:
        return True

    if "127.0.0.1" in forwarded_for or "localhost" in forwarded_for:
        return True

    if "localhost" in forwarded_host:
        return True

    return False


def require_dev_access(request: Request):
    is_local_env = ENVIRONMENT == "local"
    is_local_request = _is_local_request(request)

    if ADMIN_TOKEN:
        supplied_token = request.headers.get("x-admin-token")

        if supplied_token != ADMIN_TOKEN:
            raise HTTPException(status_code=403, detail="Developer controls require a valid admin token.")

        return

    if is_local_env and is_local_request:
        return

    raise HTTPException(
        status_code=403,
        detail="Developer controls are disabled outside local mode when ADMIN_TOKEN is not configured.",
    )


def get_next_event():
    global real_event_queue
    global last_source_fetch_time

    if real_event_queue:
        return real_event_queue.pop(0)

    now = datetime.now()

    should_fetch_sources = (
        last_source_fetch_time is None
        or now - last_source_fetch_time >= timedelta(seconds=SOURCE_REFRESH_SECONDS)
    )

    if should_fetch_sources:
        last_source_fetch_time = now
        real_event_queue = fetch_real_events()

    if real_event_queue:
        return real_event_queue.pop(0)

    if ALLOW_SIMULATION:
        return simulation.generate_event()

    return None


def update_risk(alerts):
    for alert in alerts:
        location = alert["location"]
        impact = alert.get("score_impact", 5)

        risk_map[location] = risk_map.get(location, 0) + impact

    for location in list(risk_map.keys()):
        previous = risk_map[location]
        risk_map[location] *= 0.9

        if previous >= 10:
            log_agent(
                "Risk Engine",
                f"{location} risk decayed from {round(previous, 1)} to {round(risk_map[location], 1)}.",
                "info",
            )

        if risk_map[location] < 1:
            del risk_map[location]


def calculate_health(alerts):
    score = 100

    for alert in alerts:
        score -= alert.get("score_impact", 0)

    return max(score, 0)


def run_agents(events):
    primary_signals = []

    primary_signals += infrastructure_warden(events)
    primary_signals += waste_warden(events)
    primary_signals += incident_warden(events)
    primary_signals += weather_warden(events)

    cascade_signals = []

    cascade_signals += mobility_warden(primary_signals)
    cascade_signals += public_health_warden(primary_signals)
    cascade_signals += emergency_pressure_warden(primary_signals)

    trend_signals = trend_warden(events)

    all_signals = primary_signals + cascade_signals + trend_signals

    if all_signals:
        log_agent("Agent Network", f"{len(all_signals)} agent signals generated.", "success")
    else:
        log_agent("Agent Network", "Agents checked current history. No alert threshold crossed.", "info")

    update_risk(all_signals)

    zone_signals, critical_zones = critical_zone_warden(risk_map)
    response_signals = response_warden(critical_zones)

    if critical_zones:
        log_agent(
            "Critical Zone Warden",
            f"Critical zones active: {', '.join(critical_zones)}.",
            "danger",
        )
    else:
        log_agent("Critical Zone Warden", "No critical zones active.", "info")

    return all_signals + zone_signals + response_signals, critical_zones


def runtime_status():
    return {
        "simulation_enabled": ALLOW_SIMULATION,
        "duplicates_skipped": duplicate_count,
        "source_refresh_seconds": SOURCE_REFRESH_SECONDS,
        "next_source_refresh_seconds": seconds_until_next_source_refresh(),
        "last_source_fetch_time": last_source_fetch_time.isoformat() if last_source_fetch_time else None,
        "queued_events": len(real_event_queue),
        "live_history_count": len(history),
        "risk_map": risk_map,
        "agent_log_count": len(agent_log),
        "insights_count": len(insights),
    }


@app.get("/")
def home():
    return {
        "message": "Town Warden backend is running",
        "status": "live",
        "mode": "real-data-only civic intelligence system",
        "sources": ["Police.uk", "Open-Meteo", "Street Manager pending"],
        **runtime_status(),
    }


@app.get("/source-health")
def get_source_health():
    return {
        "sources": source_health,
        "source_health": source_health,
        **runtime_status(),
    }


@app.get("/agent-log")
def get_agent_log():
    return {
        "agent_log": agent_log[-80:],
        "count": len(agent_log),
    }


@app.get("/insights")
def get_insights():
    latest_insights = insights[-100:]

    return {
        "insights": latest_insights,
        "count": len(insights),
        "public_safe_count": len([item for item in insights if item.get("public_safe")]),
        "data_quality_warnings": len([item for item in insights if item.get("pattern_type") == "data_quality"]),
    }


@app.get("/history")
def get_history():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, type, location, text, source, real_data, source_event_id
        FROM events
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "timestamp": row[0],
            "type": row[1],
            "location": row[2],
            "text": row[3],
            "source": row[4],
            "real_data": bool(row[5]),
            "source_event_id": row[6],
        }
        for row in rows
    ]


@app.get("/analytics")
def get_analytics():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, COUNT(*)
        FROM events
        GROUP BY type
        ORDER BY COUNT(*) DESC
    """)
    events_by_type = [{"type": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT source, COUNT(*)
        FROM events
        GROUP BY source
        ORDER BY COUNT(*) DESC
    """)
    events_by_source = [{"source": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT location, COUNT(*)
        FROM events
        GROUP BY location
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    top_locations = [{"location": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT real_data, COUNT(*)
        FROM events
        GROUP BY real_data
    """)
    real_vs_simulated_rows = cursor.fetchall()

    real_count = 0
    simulated_count = 0

    for real_data, count in real_vs_simulated_rows:
        if real_data:
            real_count = count
        else:
            simulated_count = count

    cursor.execute("""
        SELECT severity, COUNT(*)
        FROM alerts
        GROUP BY severity
        ORDER BY COUNT(*) DESC
    """)
    alerts_by_severity = [{"severity": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT agent, COUNT(*)
        FROM alerts
        GROUP BY agent
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    top_agents = [{"agent": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = cursor.fetchone()[0]

    conn.close()

    return {
        "total_events": total_events,
        "total_alerts": total_alerts,
        "events_by_type": events_by_type,
        "events_by_source": events_by_source,
        "top_locations": top_locations,
        "real_vs_simulated": {
            "real": real_count,
            "simulated": simulated_count,
        },
        "alerts_by_severity": alerts_by_severity,
        "top_agents": top_agents,
        "duplicates_skipped": duplicate_count,
    }


@app.post("/webhooks/street-manager/permits")
async def street_manager_permits(request: Request):
    payload = await request.json()
    event = normalise_street_manager_payload("permit", payload)
    saved = queue_webhook_event(event)

    return {
        "status": "received",
        "kind": "permit",
        "saved": saved,
        "source_event_id": event["source_event_id"],
    }


@app.post("/webhooks/street-manager/activities")
async def street_manager_activities(request: Request):
    payload = await request.json()
    event = normalise_street_manager_payload("activity", payload)
    saved = queue_webhook_event(event)

    return {
        "status": "received",
        "kind": "activity",
        "saved": saved,
        "source_event_id": event["source_event_id"],
    }


@app.post("/webhooks/street-manager/section-58")
async def street_manager_section_58(request: Request):
    payload = await request.json()
    event = normalise_street_manager_payload("section-58", payload)
    saved = queue_webhook_event(event)

    return {
        "status": "received",
        "kind": "section-58",
        "saved": saved,
        "source_event_id": event["source_event_id"],
    }


@app.post("/dev/force-refresh")
def dev_force_refresh(request: Request):
    require_dev_access(request)
    queued = force_source_refresh()

    return {
        "message": "Source refresh forced.",
        "queued_events": queued,
        **runtime_status(),
    }


@app.post("/dev/clear-live-feed")
def dev_clear_live_feed(request: Request):
    require_dev_access(request)
    history.clear()
    log_agent("Developer Controls", "Live feed memory cleared.", "warning")

    return {
        "message": "Live feed memory cleared.",
        **runtime_status(),
    }


@app.post("/dev/clear-risk-map")
def dev_clear_risk_map(request: Request):
    require_dev_access(request)
    risk_map.clear()
    log_agent("Developer Controls", "Risk map cleared.", "warning")

    return {
        "message": "Risk map cleared.",
        **runtime_status(),
    }


@app.post("/dev/reset-database")
def dev_reset_database(request: Request):
    require_dev_access(request)
    global duplicate_count
    global last_source_fetch_time

    clear_database()

    history.clear()
    risk_map.clear()
    real_event_queue.clear()
    agent_log.clear()
    insights.clear()

    duplicate_count = 0
    last_source_fetch_time = None

    for source in source_health.values():
        source["new_events_queued"] = 0
        source["duplicates_skipped"] = 0

    log_agent("Developer Controls", "Local database and runtime memory reset.", "danger")

    return {
        "message": "Local database and runtime memory reset.",
        **runtime_status(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global duplicate_count
    global last_wait_log_bucket

    await websocket.accept()

    while True:
        await asyncio.sleep(WEBSOCKET_TICK_SECONDS)

        event = get_next_event()

        if event is None:
            current_wait_bucket = datetime.now().strftime("%Y-%m-%dT%H:%M")

            if current_wait_bucket != last_wait_log_bucket:
                last_wait_log_bucket = current_wait_bucket
                log_agent(
                    "Source Monitor",
                    "No new event available. Waiting for next source refresh.",
                    "info",
                )

            payload = {
                "event": {
                    "type": "waiting",
                    "location": "System",
                    "text": "No new real events available. Waiting for public data source updates.",
                    "timestamp": datetime.now().isoformat(),
                    "source": "Real Data Monitor",
                    "source_event_id": "system:waiting",
                    "real_data": True,
                },
                "alerts": [],
                "health": calculate_health([]),
                "history_count": len(history),
                "recent_history": history,
                "risk_map": risk_map,
                "critical_zones": [],
                "source_health": source_health,
                "sources": source_health,
                "agent_log": agent_log[-80:],
                "insights": insights[-100:],
                "waiting_for_real_events": True,
                "system_mode": "real-data-only civic intelligence system",
                **runtime_status(),
            }

            await websocket.send_text(json.dumps(payload))
            continue

        saved = save_event(event)

        if not saved:
            duplicate_count += 1

            source = event.get("source", "unknown")
            current = source_health.get(source, {})
            current["duplicates_skipped"] = current.get("duplicates_skipped", 0) + 1
            current["last_checked"] = datetime.now().isoformat()
            source_health[source] = current

            log_agent(
                "Deduplication Guard",
                f"Skipped duplicate event from {source}: {event.get('source_event_id')}",
                "warning",
            )

            continue

        history.append(event)
        history[:] = history[-30:]

        log_agent(
            "Event Router",
            f"Accepted {event['type']} event from {event['source']} for {event['location']}.",
            "success",
        )

        alerts, critical_zones = run_agents(history)
        generated_insights = generate_insights(history, risk_map, source_health, duplicate_count)

        insights_by_agent = {}

        for candidate in generated_insights:
            fingerprint = "::".join([
                str(candidate.get("agent", "")),
                str(candidate.get("title", "")),
                str(candidate.get("location", "")),
                str(candidate.get("pattern_type", "")),
            ])

            existing = next(
                (
                    item for item in reversed(insights)
                    if "::".join([
                        str(item.get("agent", "")),
                        str(item.get("title", "")),
                        str(item.get("location", "")),
                        str(item.get("pattern_type", "")),
                    ]) == fingerprint
                ),
                None,
            )

            should_add = True

            if existing:
                existing_timestamp = existing.get("timestamp")

                if existing_timestamp:
                    existing_time = datetime.fromisoformat(existing_timestamp)
                    should_add = datetime.now() - existing_time >= timedelta(minutes=10)

            if should_add:
                log_insight(
                    agent=candidate.get("agent", "Insight Agent"),
                    title=candidate.get("title", "Insight generated"),
                    summary=candidate.get("summary", "No summary provided."),
                    location=candidate.get("location"),
                    pattern_type=candidate.get("pattern_type", "general"),
                    confidence=candidate.get("confidence", 0.5),
                    severity=candidate.get("severity", "info"),
                    evidence=candidate.get("evidence", []),
                    suggested_action=candidate.get("suggested_action"),
                    source_context=candidate.get("source_context"),
                    public_safe=candidate.get("public_safe", True),
                )

                agent_name = candidate.get("agent", "Insight Agent")
                insights_by_agent[agent_name] = insights_by_agent.get(agent_name, 0) + 1

        for agent_name, generated_count in insights_by_agent.items():
            log_agent(agent_name, f"{agent_name} generated {generated_count} insights.", "info")

        for alert in alerts:
            save_alert(alert)

        save_risk_snapshot(risk_map)

        health = calculate_health(alerts)

        payload = {
            "event": event,
            "alerts": alerts,
            "health": health,
            "history_count": len(history),
            "recent_history": history,
            "risk_map": risk_map,
            "critical_zones": critical_zones,
            "source_health": source_health,
            "sources": source_health,
            "agent_log": agent_log[-80:],
            "insights": insights[-100:],
            "waiting_for_real_events": False,
            "system_mode": "real-data-only civic intelligence system",
            **runtime_status(),
        }

        await websocket.send_text(json.dumps(payload))
