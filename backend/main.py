"""Town Warden FastAPI backend."""

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from agents.cascade import emergency_pressure_warden, mobility_warden, public_health_warden
from agents.primary import infrastructure_warden, incident_warden, waste_warden, weather_warden
from agents.trend import trend_warden
from agents.zone import critical_zone_warden, response_warden
from config import (
    ALLOW_SIMULATION,
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_database()

history = []
risk_map = {}
real_event_queue = []
duplicate_count = 0
last_source_fetch_time = None
MAX_AGENT_LOGS = 150
agent_log = deque(maxlen=MAX_AGENT_LOGS)

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
        "message": "API registration pending.",
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


def log_agent(agent, message, level="info", data=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "message": message,
        "level": level,
    }
    if data is not None:
        entry["data"] = data
    agent_log.append(entry)


def recent_agent_log():
    return list(agent_log)


log_agent("Source Monitor", "Backend startup complete. Awaiting source refresh cycle.")


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


def fetch_real_events():
    """Fetch all connector events, deduplicate, then return only new events."""
    global duplicate_count
    log_agent("Source Monitor", "Source refresh started.", data={"refresh_window_seconds": SOURCE_REFRESH_SECONDS})

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
            f"Skipped duplicate records from {source}.",
            level="warning",
            data={"duplicates_skipped": count},
        )

    for source_name in ["Police.uk", "Open-Meteo", "Street Manager"]:
        source_new = len([event for event in new_events if event.get("source") == source_name])

        if source_name in source_health:
            base_message = source_health[source_name].get("message", "").split(" New queued:")[0]
            source_health[source_name]["new_events_queued"] = source_new
            source_health[source_name]["message"] = f"{base_message} New queued: {source_new}."

    log_agent(
        "Source Monitor",
        "Source refresh completed.",
        data={
            "records_fetched": len(fetched_events),
            "new_events_accepted": len(new_events),
            "duplicates_skipped_cycle": sum(duplicates_by_source.values()),
        },
    )
    return new_events


def force_source_refresh():
    global real_event_queue
    global last_source_fetch_time

    last_source_fetch_time = datetime.now()
    real_event_queue = fetch_real_events()
    log_agent("Source Monitor", "Manual source refresh completed.", data={"queued_events": len(real_event_queue)})
    return len(real_event_queue)


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
        log_agent("Source Monitor", "No real events available; simulation fallback emitted an event.", level="warning")
        return simulation.generate_event()

    log_agent(
        "Source Monitor",
        "No new event available. Waiting for next source refresh.",
        data={"seconds_until_next_refresh": seconds_until_next_source_refresh()},
    )
    return None


def update_risk(alerts):
    before = dict(risk_map)
    for alert in alerts:
        location = alert["location"]
        impact = alert.get("score_impact", 5)
        risk_map[location] = risk_map.get(location, 0) + impact

    for location in list(risk_map.keys()):
        risk_map[location] *= 0.9
        if risk_map[location] < 1:
            del risk_map[location]

    if alerts:
        log_agent(
            "Risk Engine",
            "Risk map updated from active alerts.",
            data={"alerts_processed": len(alerts), "locations": list(risk_map.keys()), "prior_locations": list(before.keys())},
        )


def calculate_health(alerts):
    score = 100
    for alert in alerts:
        score -= alert.get("score_impact", 0)
    return max(score, 0)


def run_agents(events):
    primary_signals = []
    log_agent("Infrastructure Warden", "Checking recent events.", data={"event_count": len(events)})
    infra_signals = infrastructure_warden(events)
    if not infra_signals:
        log_agent("Infrastructure Warden", "No alerts generated from recent events.")
    primary_signals += infra_signals

    log_agent("Waste Warden", "Checking recent events.", data={"event_count": len(events)})
    waste_signals = waste_warden(events)
    if not waste_signals:
        log_agent("Waste Warden", "No alerts generated from recent events.")
    primary_signals += waste_signals

    log_agent("Incident Warden", "Checking recent events.", data={"event_count": len(events)})
    incident_signals = incident_warden(events)
    if not incident_signals:
        log_agent("Incident Warden", "No alerts generated from recent events.")
    primary_signals += incident_signals

    log_agent("Weather Warden", "Checking recent events.", data={"event_count": len(events)})
    weather_signals = weather_warden(events)
    if not weather_signals:
        log_agent("Weather Warden", "No alerts generated from recent events.")
    primary_signals += weather_signals

    cascade_signals = []
    log_agent("Mobility Warden", "Checking primary signals.", data={"primary_signal_count": len(primary_signals)})
    mobility_signals = mobility_warden(primary_signals)
    if not mobility_signals:
        log_agent("Mobility Warden", "No alerts generated from primary signals.")
    cascade_signals += mobility_signals

    log_agent("Public Health Warden", "Checking primary signals.", data={"primary_signal_count": len(primary_signals)})
    health_signals = public_health_warden(primary_signals)
    if not health_signals:
        log_agent("Public Health Warden", "No alerts generated from primary signals.")
    cascade_signals += health_signals

    log_agent(
        "Emergency Pressure Warden",
        "Checking primary signals.",
        data={"primary_signal_count": len(primary_signals)},
    )
    emergency_signals = emergency_pressure_warden(primary_signals)
    if not emergency_signals:
        log_agent("Emergency Pressure Warden", "No alerts generated from primary signals.")
    cascade_signals += emergency_signals

    log_agent("Trend Warden", "Checking recent events for patterns.", data={"event_count": len(events)})
    trend_signals = trend_warden(events)
    if not trend_signals:
        log_agent("Trend Warden", "No pattern alerts generated.")
    all_signals = primary_signals + cascade_signals + trend_signals

    update_risk(all_signals)

    log_agent("Critical Zone Warden", "Evaluating zone pressure.", data={"risk_locations": len(risk_map)})
    zone_signals, critical_zones = critical_zone_warden(risk_map)
    if not critical_zones:
        log_agent("Critical Zone Warden", "No critical zones active.")

    log_agent("Response Warden", "Reviewing critical zones for response actions.", data={"critical_zone_count": len(critical_zones)})
    response_signals = response_warden(critical_zones)
    if not response_signals:
        log_agent("Response Warden", "No response actions required.")

    return all_signals + zone_signals + response_signals, critical_zones


def runtime_status():
    return {
        "simulation_enabled": ALLOW_SIMULATION,
        "duplicates_skipped": duplicate_count,
        "agent_log_count": len(agent_log),
        "source_refresh_seconds": SOURCE_REFRESH_SECONDS,
        "next_source_refresh_seconds": seconds_until_next_source_refresh(),
        "last_source_fetch_time": last_source_fetch_time.isoformat() if last_source_fetch_time else None,
        "queued_events": len(real_event_queue),
        "live_history_count": len(history),
        "risk_map": risk_map,
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
        "agent_log": recent_agent_log(),
        **runtime_status(),
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


@app.post("/dev/force-refresh")
def dev_force_refresh():
    queued = force_source_refresh()
    return {
        "message": "Source refresh forced.",
        "queued_events": queued,
        **runtime_status(),
    }


@app.post("/dev/clear-live-feed")
def dev_clear_live_feed():
    history.clear()
    return {
        "message": "Live feed memory cleared.",
        **runtime_status(),
    }


@app.post("/dev/clear-risk-map")
def dev_clear_risk_map():
    risk_map.clear()
    return {
        "message": "Risk map cleared.",
        **runtime_status(),
    }


@app.post("/dev/reset-database")
def dev_reset_database():
    global duplicate_count
    global last_source_fetch_time

    clear_database()
    history.clear()
    risk_map.clear()
    real_event_queue.clear()
    agent_log.clear()
    duplicate_count = 0
    last_source_fetch_time = None

    for source in source_health.values():
        source["new_events_queued"] = 0
        source["duplicates_skipped"] = 0

    return {
        "message": "Local database and runtime memory reset.",
        **runtime_status(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global duplicate_count

    await websocket.accept()

    while True:
        await asyncio.sleep(WEBSOCKET_TICK_SECONDS)

        event = get_next_event()

        if event is None:
            log_agent(
                "Source Monitor",
                "System waiting for next source refresh cycle.",
                data={"seconds_until_next_refresh": seconds_until_next_source_refresh()},
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
                "agent_log": recent_agent_log(),
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
                "Duplicate record skipped before persistence.",
                level="warning",
                data={"source": source, "source_event_id": event.get("source_event_id")},
            )
            continue

        history.append(event)
        history[:] = history[-30:]

        alerts, critical_zones = run_agents(history)
        if not alerts:
            log_agent("Incident Warden", "No active public alerts in this processing cycle.")

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
            "agent_log": recent_agent_log(),
            "waiting_for_real_events": False,
            "system_mode": "real-data-only civic intelligence system",
            **runtime_status(),
        }

        await websocket.send_text(json.dumps(payload))
