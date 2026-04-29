import asyncio
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, WebSocket, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.cascade import emergency_pressure_warden, mobility_warden, public_health_warden
from agents.primary import infrastructure_warden, incident_warden, waste_warden, weather_warden
from agents.insights import generate_insights
from agents.trend import trend_warden
from agents.zone import critical_zone_warden, response_warden
from config import (
    ADMIN_TOKEN,
    ALLOW_SIMULATION,
    ALERT_RETENTION_DAYS,
    EVENT_RETENTION_DAYS,
    ENVIRONMENT,
    MAX_NEW_EVENTS_PER_FETCH,
    RISK_SNAPSHOT_RETENTION_DAYS,
    SOURCE_REFRESH_SECONDS,
    TOWN_WARDEN_AREA_NAME,
    WEBSOCKET_TICK_SECONDS,
)
from connectors import open_meteo, police_uk, simulation, street_manager
from storage import (
    clear_database,
    cleanup_old_records,
    connect,
    database_backend,
    event_exists,
    save_alert,
    save_event,
    save_risk_snapshot,
    setup_database,
)
from town_config import TownConfigError, get_town_config, public_town_config


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
try:
    TOWN_CONFIG_DATA = get_town_config()
except TownConfigError as exc:
    print(f"Town Warden config error: {exc}", flush=True)
    raise

print(
    "Town Warden startup: "
    f"environment={ENVIRONMENT}, "
    f"town_config={TOWN_CONFIG_DATA.get('town_id')}, "
    f"town={TOWN_CONFIG_DATA.get('display_name')}, "
    f"database_backend={database_backend()}, "
    f"dev_routes_protected={ENVIRONMENT == 'production'}, "
    f"simulation_enabled={ALLOW_SIMULATION}",
    flush=True,
)


history = []
risk_map = {}
real_event_queue = []
agent_log = []
insights = []

duplicate_count = 0
last_source_fetch_time = None
last_wait_log_bucket = None

SOURCE_IDS = ("police_uk", "open_meteo", "street_manager")
SOURCE_NAME_BY_ID = {
    "police_uk": "Police.uk",
    "open_meteo": "Open-Meteo",
    "street_manager": "Street Manager",
}
SOURCE_ID_BY_NAME = {label: source_id for source_id, label in SOURCE_NAME_BY_ID.items()}
REAL_SOURCE_NAMES = [
    SOURCE_NAME_BY_ID[source_id]
    for source_id in SOURCE_IDS
    if TOWN_CONFIG_DATA["enabled_sources"].get(source_id, True)
]
TOWN_DISPLAY_NAME = TOWN_CONFIG_DATA.get("display_name") or TOWN_CONFIG_DATA.get("town_name") or TOWN_WARDEN_AREA_NAME


def source_enabled(source_id):
    return bool(TOWN_CONFIG_DATA.get("enabled_sources", {}).get(source_id, True))


source_health = {
    "Police.uk": {
        "status": "checking",
        "message": "Waiting for first Police.uk check.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "filtered_out_of_area": 0,
        "latest_message": "Waiting for first Police.uk check.",
        "last_error": None,
        "last_checked": None,
    },
    "Open-Meteo": {
        "status": "checking",
        "message": "Waiting for first Open-Meteo check.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "filtered_out_of_area": 0,
        "latest_message": "Waiting for first Open-Meteo check.",
        "last_error": None,
        "last_checked": None,
    },
    "Street Manager": {
        "status": "pending",
        "message": "Waiting for live webhook data.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "filtered_out_of_area": 0,
        "latest_message": "Waiting for live webhook data.",
        "last_error": None,
        "last_checked": None,
    },
    "Simulation": {
        "status": "enabled" if ALLOW_SIMULATION else "disabled",
        "message": "Simulation fallback enabled." if ALLOW_SIMULATION else "Simulation fallback disabled.",
        "records_returned": 0,
        "events_emitted": 0,
        "new_events_queued": 0,
        "duplicates_skipped": 0,
        "filtered_out_of_area": 0,
        "latest_message": "Simulation fallback enabled." if ALLOW_SIMULATION else "Simulation fallback disabled.",
        "last_error": None,
        "last_checked": datetime.now().isoformat(),
    },
}

for configured_source_id, configured_source_name in SOURCE_NAME_BY_ID.items():
    if not source_enabled(configured_source_id) and configured_source_name in source_health:
        disabled_message = "Source disabled in active town config."
        source_health[configured_source_name].update({
            "status": "disabled",
            "message": disabled_message,
            "latest_message": disabled_message,
            "last_checked": datetime.now().isoformat(),
        })

def build_map_zones(town_config):
    zones = {}
    for zone in town_config.get("zones", []):
        zones[zone["id"]] = {
            "id": zone["id"],
            "name": zone["label"],
            "label": zone["label"],
            "lat": zone["fallback_lat"],
            "lng": zone["fallback_lng"],
            "radius_m": zone.get("radius_m", 1000),
            "risk_weight": zone.get("risk_weight", 1.0),
            "keywords": zone.get("keywords", []),
        }
    return zones


MAP_ZONES = build_map_zones(TOWN_CONFIG_DATA)

SOURCE_LAYER_FLAGS = {
    source_id: bool(TOWN_CONFIG_DATA["enabled_sources"].get(source_id, True))
    for source_id in SOURCE_IDS
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
    filtered_out_of_area=None,
):
    current = source_health.get(source_name, {})

    current["status"] = status
    current["message"] = message
    current["latest_message"] = message
    current["records_returned"] = records_returned
    current["events_emitted"] = events_emitted
    current["last_error"] = message if str(status).lower() in {"error", "failed", "offline", "unavailable", "disconnected"} else None

    if new_events_queued is not None:
        current["new_events_queued"] = new_events_queued

    if duplicates_skipped is not None:
        current["duplicates_skipped"] = duplicates_skipped

    if filtered_out_of_area is not None:
        current["filtered_out_of_area"] = filtered_out_of_area
    else:
        current.setdefault("filtered_out_of_area", 0)

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


def normalise_field_name(value):
    return "".join(char for char in str(value).lower() if char.isalnum())


def iter_mapping_items(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from iter_mapping_items(item)
    elif isinstance(value, list):
        for item in value[:25]:
            yield from iter_mapping_items(item)


def get_nested_field(payload, aliases):
    """
    Find a field anywhere in a Street Manager payload using common naming variants.

    Street Manager messages can arrive as nested JSON inside an AWS SNS envelope and
    field names vary between camelCase, snake_case, and occasionally short labels.
    """

    wanted = {normalise_field_name(alias) for alias in aliases}

    for key, value in iter_mapping_items(payload):
        if normalise_field_name(key) in wanted and value not in (None, "", [], {}):
            return value

    return None


def parse_json_if_possible(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    return value


def unwrap_street_manager_message(payload):
    if not isinstance(payload, dict):
        return {"raw_payload": payload}, False

    message = parse_json_if_possible(payload.get("Message"))

    if isinstance(message, dict):
        return message, True

    return payload, False


def first_present(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def as_text(value):
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def extract_coordinates(payload):
    latitude = get_nested_field(payload, ["latitude", "lat", "y"])
    longitude = get_nested_field(payload, ["longitude", "lng", "lon", "x"])

    if latitude is not None and longitude is not None:
        try:
            return {
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        except (TypeError, ValueError):
            pass

    coordinates = get_nested_field(payload, ["coordinates", "coordinate", "geometry"])

    if isinstance(coordinates, dict):
        lon = first_present(coordinates.get("longitude"), coordinates.get("lng"), coordinates.get("lon"), coordinates.get("x"))
        lat = first_present(coordinates.get("latitude"), coordinates.get("lat"), coordinates.get("y"))
        if lat is not None and lon is not None:
            try:
                return {
                    "latitude": float(lat),
                    "longitude": float(lon),
                }
            except (TypeError, ValueError):
                return coordinates

    return coordinates if coordinates not in (None, "", [], {}) else None


def compact_metadata(metadata):
    return {key: value for key, value in metadata.items() if value not in (None, "", [], {})}


def inspect_street_manager_payload(payload, topic, metadata, unwrapped_sns_message):
    """
    Log a small production-safe summary rather than dumping the whole payload.

    This helps inspect live message shape without exposing oversized raw payloads or
    leaving permanent full-body logging in Render.
    """

    field_names = []
    if isinstance(payload, dict):
        field_names = sorted(str(key) for key in payload.keys())[:20]

    summary = {
        "topic": topic,
        "unwrapped_sns_message": unwrapped_sns_message,
        "top_level_fields": field_names,
        "reference": metadata.get("reference"),
        "street_name": metadata.get("street_name"),
        "activity_type": metadata.get("activity_type"),
        "works_category": metadata.get("works_category"),
        "start_date": metadata.get("start_date"),
        "end_date": metadata.get("end_date"),
    }

    print(f"Street Manager payload summary: {json.dumps(summary, default=str)}", flush=True)


def format_street_manager_text(topic, metadata):
    topic_label = {
        "permit": "permit",
        "activity": "activity",
        "section-58": "Section 58",
    }.get(topic, topic)

    location = first_present(
        metadata.get("street_name"),
        metadata.get("location_description"),
        metadata.get("town_area"),
        TOWN_DISPLAY_NAME,
    )

    detail = first_present(
        metadata.get("activity_type"),
        metadata.get("works_category"),
        metadata.get("traffic_management_type"),
    )

    date_range = None
    if metadata.get("start_date") and metadata.get("end_date"):
        date_range = f"{metadata['start_date']} to {metadata['end_date']}"
    elif metadata.get("start_date"):
        date_range = f"from {metadata['start_date']}"
    elif metadata.get("end_date"):
        date_range = f"until {metadata['end_date']}"

    text = f"Street works {topic_label} on {location}"

    extras = [value for value in [detail, date_range] if value]
    if extras:
        text += f": {', '.join(str(value) for value in extras)}"

    if metadata.get("reference"):
        text += f" ({metadata['reference']})"

    return text


def normalize_street_manager_payload(payload, topic):
    """
    Converts a Street Manager webhook payload into a Town Warden event.

    Mapping assumptions:
    - AWS SNS notification envelopes may wrap the useful Street Manager JSON in
      Message, so we unwrap it before looking for roadworks fields.
    - Field names vary, so extraction uses aliases and recursive lookup.
    - Missing fields are expected; location and text fall back gracefully.
    """

    street_payload, unwrapped_sns_message = unwrap_street_manager_message(payload)

    permit_reference = as_text(get_nested_field(street_payload, [
        "permitReferenceNumber", "permitReference", "permit_reference", "permitRef", "permit_ref",
    ]))
    works_reference = as_text(get_nested_field(street_payload, [
        "worksReference", "works_reference", "worksReferenceNumber", "workReference", "work_reference",
    ]))
    activity_reference = as_text(get_nested_field(street_payload, [
        "activityReference", "activity_reference", "activityId", "activity_id", "activityReferenceNumber",
    ]))
    street_manager_id = as_text(get_nested_field(street_payload, [
        "id", "eventId", "notificationId", "notification_id", "messageId",
    ]))

    street_name = as_text(get_nested_field(street_payload, [
        "streetName", "street_name", "roadName", "road_name", "street", "usrnStreetName",
    ]))
    location_description = as_text(get_nested_field(street_payload, [
        "locationDescription", "location_description", "location", "areaDescription", "siteLocation",
    ]))
    town_area = as_text(get_nested_field(street_payload, [
        "town", "area", "townArea", "town_area", "locality", "district",
    ]))
    activity_type = as_text(get_nested_field(street_payload, [
        "activityType", "activity_type", "eventType", "event_type", "notificationType",
    ]))
    works_category = as_text(get_nested_field(street_payload, [
        "worksCategory", "works_category", "workCategory", "category",
    ]))
    traffic_management_type = as_text(get_nested_field(street_payload, [
        "trafficManagementType", "traffic_management_type", "trafficManagement", "tmType",
    ]))
    start_date = as_text(get_nested_field(street_payload, [
        "startDate", "start_date", "proposedStartDate", "actualStartDate", "worksStartDate",
    ]))
    end_date = as_text(get_nested_field(street_payload, [
        "endDate", "end_date", "proposedEndDate", "actualEndDate", "worksEndDate",
    ]))

    metadata = compact_metadata({
        "topic": topic,
        "permit_reference": permit_reference,
        "works_reference": works_reference,
        "activity_reference": activity_reference,
        "street_manager_id": street_manager_id,
        "reference": first_present(permit_reference, works_reference, activity_reference, street_manager_id),
        "street_name": street_name,
        "location_description": location_description,
        "town_area": town_area,
        "activity_type": activity_type,
        "works_category": works_category,
        "traffic_management_type": traffic_management_type,
        "start_date": start_date,
        "end_date": end_date,
        "coordinates": extract_coordinates(street_payload),
        "postcode": as_text(get_nested_field(street_payload, [
            "postcode", "postalCode", "post_code",
        ])),
        "district": as_text(get_nested_field(street_payload, [
            "district", "borough", "administrativeArea", "administrative_area",
        ])),
        "county": as_text(get_nested_field(street_payload, [
            "county", "region",
        ])),
        "responsible_organisation": as_text(get_nested_field(street_payload, [
            "responsibleOrganisation", "responsible_organisation", "promoterOrganisation", "organisation",
        ])),
        "highway_authority": as_text(get_nested_field(street_payload, [
            "highwayAuthority", "highway_authority", "authority", "highwayAuthorityName",
        ])),
        "sns_message_id": as_text(payload.get("MessageId")) if isinstance(payload, dict) else None,
    })

    inspect_street_manager_payload(street_payload, topic, metadata, unwrapped_sns_message)

    stable_id = metadata.get("reference")
    source_event_id = (
        f"streetmanager:{topic}:{stable_id}"
        if stable_id
        else make_payload_fingerprint(f"streetmanager:{topic}", street_payload)
    )

    location = first_present(
        street_name,
        location_description,
        town_area,
        TOWN_DISPLAY_NAME,
    )

    return {
        "type": "infrastructure",
        "location": location,
        "text": format_street_manager_text(topic, metadata),
        "timestamp": datetime.now().isoformat(),
        "source": "Street Manager",
        "source_event_id": source_event_id,
        "real_data": True,
        "metadata": metadata,
    }


def normalise_street_manager_payload(kind, payload):
    return normalize_street_manager_payload(payload, kind)


def configured_keywords(*groups):
    keywords = []
    for group in groups:
        for item in TOWN_CONFIG_DATA.get(group, []):
            text = str(item or "").strip()
            if text:
                keywords.append(text.lower())
    if not keywords:
        keywords.append(TOWN_DISPLAY_NAME.lower())
    return keywords


def text_contains_configured_keyword(value, *groups):
    text = str(value or "").lower()
    return any(keyword in text for keyword in configured_keywords(*groups))


def text_contains_area(value):
    return text_contains_configured_keyword(
        value,
        "local_authority_keywords",
        "highway_authority_keywords",
        "street_manager_relevance_keywords",
    )


def coordinates_in_town_warden_bounds(coordinates):
    if not isinstance(coordinates, dict):
        return False

    lat = coerce_float(first_present(coordinates.get("latitude"), coordinates.get("lat"), coordinates.get("y")))
    lng = coerce_float(first_present(coordinates.get("longitude"), coordinates.get("lng"), coordinates.get("lon"), coordinates.get("x")))

    if lat is None or lng is None:
        return False

    bounds = TOWN_CONFIG_DATA["approximate_bounding_box"]
    # Legacy TOWN_WARDEN_* bounds are kept as backwards-compatible overrides,
    # while new town clones should prefer approximate_bounding_box in TOWN_CONFIG.
    def env_float(name, default):
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return float(default)

    min_lat = env_float("TOWN_WARDEN_MIN_LAT", bounds["min_lat"])
    max_lat = env_float("TOWN_WARDEN_MAX_LAT", bounds["max_lat"])
    min_lng = env_float("TOWN_WARDEN_MIN_LNG", bounds["min_lng"])
    max_lng = env_float("TOWN_WARDEN_MAX_LNG", bounds["max_lng"])

    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def postcode_indicates_project_area(value):
    postcode = str(value or "").strip().upper().replace(" ", "")
    if not postcode:
        return False

    prefixes = [str(prefix).strip().upper().replace(" ", "") for prefix in TOWN_CONFIG_DATA.get("postcode_prefixes", [])]
    return any(postcode.startswith(prefix) for prefix in prefixes)


def street_manager_location_evidence(metadata):
    return {
        "town_area": metadata.get("town_area"),
        "highway_authority": metadata.get("highway_authority"),
        "street_name": metadata.get("street_name"),
        "location_description": metadata.get("location_description"),
        "district": metadata.get("district"),
        "county": metadata.get("county"),
        "postcode": metadata.get("postcode"),
        "coordinates": metadata.get("coordinates"),
    }


def is_relevant_to_town_street_manager(payload, normalized_event):
    """
    Decide whether a Street Manager payload belongs in the configured town area.

    The filter is intentionally conservative: without clear area, authority,
    postcode, or coordinate evidence, the webhook is accepted by the endpoint
    but not stored as a Town Warden civic event.
    """

    metadata = normalized_event.get("metadata") or {}
    evidence = street_manager_location_evidence(metadata)
    direct_text_values = [
        evidence.get("town_area"),
        evidence.get("highway_authority"),
        evidence.get("street_name"),
        evidence.get("location_description"),
        evidence.get("district"),
    ]

    if any(text_contains_area(value) for value in direct_text_values):
        return True, "area_text"

    if coordinates_in_town_warden_bounds(evidence.get("coordinates")):
        return True, "coordinate_bounds"

    if postcode_indicates_project_area(evidence.get("postcode")):
        return True, "postcode"

    payload_area_fields = [
        get_nested_field(payload, ["town", "area", "district", "borough", "highwayAuthority", "highwayAuthorityName"]),
        get_nested_field(payload, ["postcode", "postalCode", "post_code"]),
    ]

    if any(text_contains_area(value) for value in payload_area_fields):
        return True, "payload_area_text"

    if any(postcode_indicates_project_area(value) for value in payload_area_fields):
        return True, "payload_postcode"

    return False, "out_of_area_or_missing_location"


def is_relevant_to_blackpool_street_manager(payload, normalized_event):
    # Backwards-compatible name used by existing tests and earlier integrations.
    return is_relevant_to_town_street_manager(payload, normalized_event)


def record_street_manager_filtered_event(event, reason):
    info = source_health["Street Manager"]
    info["status"] = "connected"
    info["message"] = (
        f"Webhook received but filtered outside the {TOWN_DISPLAY_NAME} pilot area."
    )
    info["latest_message"] = info["message"]
    info["last_error"] = None
    info["records_returned"] += 1
    info["filtered_out_of_area"] = info.get("filtered_out_of_area", 0) + 1
    info["last_checked"] = datetime.now().isoformat()

    filtered = info["filtered_out_of_area"]
    if filtered == 1 or filtered % 25 == 0:
        log_agent(
            "Street Manager Geographic Filter",
            f"Street Manager geographic filter discarded {filtered} out-of-area records.",
            "warning",
        )

    return {
        "status": "filtered_out",
        "kind": event.get("metadata", {}).get("topic"),
        "saved": False,
        "reason": reason,
        "source_event_id": event.get("source_event_id"),
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
        source_health["Street Manager"]["latest_message"] = source_health["Street Manager"]["message"]
        source_health["Street Manager"]["last_error"] = None
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
        source_health["Street Manager"]["latest_message"] = source_health["Street Manager"]["message"]
        source_health["Street Manager"]["last_error"] = None
        source_health["Street Manager"]["records_returned"] += 1
        source_health["Street Manager"]["duplicates_skipped"] += 1
        source_health["Street Manager"]["last_checked"] = datetime.now().isoformat()

        log_agent(
            "Deduplication Guard",
            f"Skipped duplicate Street Manager webhook: {event['source_event_id']}",
            "warning",
        )

    return saved


async def handle_street_manager_webhook(kind, request):
    raw_body = await request.body()
    print(f"Street Manager webhook body received [{kind}]: {len(raw_body)} bytes", flush=True)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        message = f"Invalid Street Manager webhook JSON for {kind}: {exc}"
        print(message, flush=True)
        log_agent("Street Manager Connector", message, "danger")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not source_enabled("street_manager"):
        disabled_message = "Street Manager source disabled in active town config."
        source_health["Street Manager"].update({
            "status": "disabled",
            "message": disabled_message,
            "latest_message": disabled_message,
            "last_checked": datetime.now().isoformat(),
        })
        return {
            "status": "disabled",
            "kind": kind,
            "saved": False,
        }

    if payload.get("Type") == "SubscriptionConfirmation":
        subscribe_url = payload.get("SubscribeURL")
        topic = payload.get("TopicArn") or kind

        if not isinstance(subscribe_url, str) or not subscribe_url.startswith("https://sns."):
            message = f"Rejected invalid SNS SubscribeURL for {kind}: {subscribe_url}"
            print(message, flush=True)
            log_agent("Street Manager Connector", message, "danger")
            raise HTTPException(status_code=400, detail="Invalid SNS SubscribeURL.")

        try:
            with urllib.request.urlopen(subscribe_url, timeout=10) as response:
                response.read()
        except Exception as exc:
            message = f"Failed to confirm SNS subscription for {kind}: {exc}"
            print(message, flush=True)
            log_agent("Street Manager Connector", message, "danger")
            raise HTTPException(status_code=502, detail="SNS subscription confirmation failed.")

        message = f"SNS subscription confirmed for Street Manager {kind}: {topic}"
        print(message, flush=True)
        log_agent("Street Manager Connector", message, "success")

        return {
            "status": "subscription_confirmed",
            "topic": topic,
        }

    event = normalise_street_manager_payload(kind, payload)
    relevant, relevance_reason = is_relevant_to_town_street_manager(payload, event)

    if not relevant:
        return record_street_manager_filtered_event(event, relevance_reason)

    event["metadata"]["geographic_relevance"] = relevance_reason
    saved = queue_webhook_event(event)

    return {
        "status": "received",
        "kind": kind,
        "saved": saved,
        "source_event_id": event["source_event_id"],
    }


def fetch_real_events():
    """
    Fetch all connector events, deduplicate, then return only new events.
    """

    global duplicate_count

    log_agent("Source Monitor", "Source refresh started.", "info")

    fetched_events = []

    if source_enabled("police_uk"):
        fetched_events += police_uk.fetch_events(update_source_health)
    if source_enabled("open_meteo"):
        fetched_events += open_meteo.fetch_events(update_source_health)
    if source_enabled("street_manager"):
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

    for source_name in REAL_SOURCE_NAMES:
        source_new = len([event for event in new_events if event.get("source") == source_name])

        if source_name in source_health:
            base_message = source_health[source_name].get("message", "").split(" New queued:")[0]
            source_health[source_name]["new_events_queued"] = source_new
            source_health[source_name]["message"] = f"{base_message} New queued: {source_new}."
            source_health[source_name]["latest_message"] = source_health[source_name]["message"]

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


def require_dev_access(request: Request):
    """
    Protects /dev routes at the backend layer.

    Local mode allows no-token access so local development and debugging stay easy.
    Production mode requires a valid x-admin-token header to prevent public access
    to dangerous developer controls (refresh/clear/reset operations).
    """

    if ENVIRONMENT != "production":
        return

    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Developer controls are disabled because ADMIN_TOKEN is not configured.",
        )

    supplied_token = request.headers.get("x-admin-token")

    if supplied_token == ADMIN_TOKEN:
        return

    raise HTTPException(
        status_code=403,
        detail="Developer controls require a valid admin token.",
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


def source_is_active(info):
    status = str((info or {}).get("status") or "").lower()
    if status in {"connected", "healthy", "ok", "live", "enabled"}:
        return True
    if status in {"pending", "disabled", "error", "failed", "offline", "unavailable", "disconnected"}:
        return False

    return (
        int((info or {}).get("records_returned") or 0)
        + int((info or {}).get("events_emitted") or 0)
    ) > 0


def source_has_error(info):
    status = str((info or {}).get("status") or "").lower()
    return status in {"error", "failed", "offline", "unavailable", "disconnected"}


def risk_label_from_score(score):
    if score >= 90:
        return "Critical"
    if score >= 55:
        return "Elevated"
    if score >= 25:
        return "Watch"
    return "Low"


def highest_risk_zone_summary():
    if not risk_map:
        return None

    name, score = max(risk_map.items(), key=lambda item: item[1])
    return {
        "name": name,
        "score": round(score, 1),
        "risk_level": map_risk_level(score),
    }


def system_status_summary():
    active_sources = [name for name in REAL_SOURCE_NAMES if source_is_active(source_health.get(name))]
    source_errors = [
        {
            "source": name,
            "status": source_health.get(name, {}).get("status"),
            "message": source_health.get(name, {}).get("message"),
        }
        for name in REAL_SOURCE_NAMES
        if source_has_error(source_health.get(name))
    ]

    score = 100
    if source_errors:
        score -= 20 * len(source_errors)
    if len(active_sources) < len(REAL_SOURCE_NAMES):
        score -= 10 * (len(REAL_SOURCE_NAMES) - len(active_sources))
    if ALLOW_SIMULATION:
        score -= 10
    if ENVIRONMENT == "production" and not ADMIN_TOKEN:
        score -= 10

    score = max(0, min(100, score))
    if score >= 85:
        label = "Stable"
    elif score >= 60:
        label = "Degraded"
    else:
        label = "Limited"

    return {
        "system_health_score": score,
        "system_health_label": label,
        "active_sources_count": len(active_sources),
        "total_sources_count": len(REAL_SOURCE_NAMES),
        "source_errors": source_errors,
        "source_status_summary": {
            "active": active_sources,
            "errors": source_errors,
            "simulation_enabled": ALLOW_SIMULATION,
        },
        "dev_routes_protected": ENVIRONMENT == "production",
    }


def civic_risk_summary():
    top_zone = highest_risk_zone_summary()
    highest_score = top_zone["score"] if top_zone else 0
    risk_from_zones = min(100, int(round((highest_score / 150) * 100))) if highest_score else 0

    severe_insights = len([
        item for item in insights[-50:]
        if str(item.get("severity") or "").lower() in {"critical", "high", "danger", "error"}
    ])
    medium_insights = len([
        item for item in insights[-50:]
        if str(item.get("severity") or "").lower() in {"warning", "medium", "watch"}
    ])

    score = min(100, risk_from_zones + min(20, severe_insights * 5) + min(10, medium_insights * 2))
    system_summary = system_status_summary()

    if system_summary["active_sources_count"] == 0 or system_summary["source_errors"]:
        return {
            "civic_risk_score": None,
            "civic_risk_label": "Limited confidence",
            "highest_risk_zone": top_zone,
            "risk_context": "Source coverage is degraded, so civic risk is uncertain.",
        }

    return {
        "civic_risk_score": score,
        "civic_risk_label": risk_label_from_score(score),
        "highest_risk_zone": top_zone,
        "risk_context": "Civic risk reflects current public-source signals, not system uptime.",
    }


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
    system_summary = system_status_summary()
    risk_summary = civic_risk_summary()

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
        "insight_count": len(insights),
        "environment": ENVIRONMENT,
        "town_id": TOWN_CONFIG_DATA.get("town_id"),
        "town_name": TOWN_CONFIG_DATA.get("town_name"),
        "display_name": TOWN_DISPLAY_NAME,
        "database_backend": database_backend(),
        "dev_routes_protected": ENVIRONMENT == "production",
        "public_dev_routes_protected": ENVIRONMENT == "production",
        "retention": {
            "events_days": EVENT_RETENTION_DAYS,
            "alerts_days": ALERT_RETENTION_DAYS,
            "risk_snapshots_days": RISK_SNAPSHOT_RETENTION_DAYS,
        },
        **system_summary,
        **risk_summary,
    }


def map_risk_level(score):
    if score >= 150:
        return "critical"
    if score >= 80:
        return "elevated"
    if score >= 40:
        return "watch"
    return "low"


def infer_zone_from_location(location_text):
    text = str(location_text or "").lower()

    for zone in MAP_ZONES.values():
        names = [zone.get("name"), zone.get("label"), *(zone.get("keywords") or [])]
        if any(str(item or "").lower() in text for item in names if item):
            return zone

    if "north" in text:
        return next((zone for zone in MAP_ZONES.values() if "north" in zone["name"].lower()), next(iter(MAP_ZONES.values())))
    if "south" in text:
        return next((zone for zone in MAP_ZONES.values() if "south" in zone["name"].lower()), next(iter(MAP_ZONES.values())))
    if "centre" in text or "center" in text or "town" in text:
        return next((zone for zone in MAP_ZONES.values() if "centre" in zone["name"].lower() or "center" in zone["name"].lower()), next(iter(MAP_ZONES.values())))

    return next(iter(MAP_ZONES.values()))


def zone_summary(name, risk_level):
    if risk_level == "critical":
        return f"{name} currently has concentrated civic signals and should be monitored closely."
    if risk_level == "elevated":
        return f"{name} is showing an elevated pattern of recent civic signals."
    if risk_level == "watch":
        return f"{name} has a watch-level pattern of early indicators."
    return f"{name} is currently showing a low concentration of civic signals."


def map_trend(score):
    if score >= 150:
        return "rising"
    if score >= 80:
        return "steady"
    return "stable"


def parse_event_metadata(metadata_raw):
    if not metadata_raw:
        return {}
    try:
        metadata = json.loads(metadata_raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metadata_coordinates(metadata):
    coordinates = metadata.get("coordinates") if isinstance(metadata, dict) else None
    if isinstance(coordinates, dict):
        lat = coerce_float(first_present(coordinates.get("latitude"), coordinates.get("lat"), coordinates.get("y")))
        lng = coerce_float(first_present(coordinates.get("longitude"), coordinates.get("lng"), coordinates.get("lon"), coordinates.get("x")))
        if lat is not None and lng is not None:
            return lat, lng

    lat = coerce_float(first_present(metadata.get("latitude"), metadata.get("lat")))
    lng = coerce_float(first_present(metadata.get("longitude"), metadata.get("lng"), metadata.get("lon")))
    if lat is not None and lng is not None:
        return lat, lng

    return None


def event_coordinate_confidence(source, metadata):
    confidence = str(metadata.get("coordinate_confidence") or "").lower()
    if confidence in {"exact", "approximate", "zone_fallback"}:
        return confidence

    # Police.uk public crime coordinates are deliberately approximate.
    if source == "Police.uk":
        return "approximate"

    return "exact"


def map_event_coordinates(source, zone, metadata):
    coords = metadata_coordinates(metadata)
    if coords:
        lat, lng = coords
        confidence = event_coordinate_confidence(source, metadata)
        return lat, lng, confidence

    return zone["lat"], zone["lng"], "zone_fallback"


def map_event_severity(signal_type, source, metadata):
    text = " ".join(str(value).lower() for value in [
        signal_type,
        source,
        metadata.get("traffic_management_type"),
        metadata.get("works_category"),
        metadata.get("activity_type"),
    ] if value)

    if any(term in text for term in ["closure", "emergency", "urgent", "major"]):
        return "high"
    if any(term in text for term in ["temporary lights", "multi-way", "diversion", "permit", "infrastructure"]):
        return "medium"
    return "low"


def map_event_title(signal_type, source, metadata, text):
    if source == "Street Manager":
        topic = str(metadata.get("topic") or "").lower()
        if topic == "permit":
            return "Street works permit"
        if topic == "activity":
            return "Street works activity"
        if topic == "section-58":
            return "Section 58 notice"
        return "Street works"

    if source == "Police.uk":
        return "Incident signal"

    return str(signal_type or "Civic signal").replace("_", " ").title()


def map_event_reference(metadata):
    return first_present(
        metadata.get("reference"),
        metadata.get("permit_reference"),
        metadata.get("works_reference"),
        metadata.get("activity_reference"),
        metadata.get("street_manager_id"),
    )


@app.get("/")
def home():
    return {
        "message": "Town Warden backend is running",
        "status": "live",
        "mode": "real-data-only civic intelligence system",
        "sources": REAL_SOURCE_NAMES,
        **runtime_status(),
    }


@app.get("/source-health")
def get_source_health():
    return {
        "sources": source_health,
        "source_health": source_health,
        **runtime_status(),
    }


@app.get("/runtime-status")
def get_runtime_status():
    return runtime_status()


@app.get("/town-config")
def get_public_town_config():
    return public_town_config(TOWN_CONFIG_DATA)


@app.get("/map-data")
def get_map_data():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT source_event_id, type, source, location, text, timestamp, metadata
        FROM events
        ORDER BY id DESC
        LIMIT 120
    """)
    rows = cursor.fetchall()
    conn.close()

    zone_signal_counts = {zone["name"]: 0 for zone in MAP_ZONES.values()}
    zone_source_counts = {zone["name"]: {} for zone in MAP_ZONES.values()}
    recent_zone_signals = {zone["name"]: 0 for zone in MAP_ZONES.values()}

    events = []
    now = datetime.now()

    for idx, row in enumerate(rows):
        signal_id, signal_type, source, location, text, timestamp, metadata_raw = row
        metadata = parse_event_metadata(metadata_raw)

        zone = infer_zone_from_location(location)
        zone_name = zone["name"]
        lat, lng, coordinate_confidence = map_event_coordinates(source, zone, metadata)

        zone_signal_counts[zone_name] += 1
        zone_source_counts[zone_name][source] = zone_source_counts[zone_name].get(source, 0) + 1

        try:
            event_time = datetime.fromisoformat(timestamp) if timestamp else None
        except ValueError:
            event_time = None

        if event_time and now - event_time <= timedelta(hours=24):
            recent_zone_signals[zone_name] += 1

        severity = map_event_severity(signal_type, source, metadata)
        title = map_event_title(signal_type, source, metadata, text)
        reference = map_event_reference(metadata)
        is_approximate = coordinate_confidence != "exact"
        confidence_note = {
            "exact": "Coordinates came from the source payload.",
            "approximate": "Coordinates are approximate because the source only publishes approximate positions.",
            "zone_fallback": f"Coordinates use the mapped {TOWN_DISPLAY_NAME} zone centre because the source did not include coordinates.",
        }.get(coordinate_confidence, "Coordinate confidence is unknown.")

        events.append({
            "id": signal_id or f"signal:{idx}",
            "type": signal_type or "signal",
            "source": source or "Unknown",
            "title": title,
            "description": text or "No additional source-limited detail.",
            "text": text or "No additional source-limited detail.",
            "location": location or zone_name,
            "zone": zone_name,
            "lat": lat,
            "lng": lng,
            "timestamp": timestamp,
            "severity": severity,
            "coordinate_confidence": coordinate_confidence,
            "is_approximate": is_approximate,
            "approximate_note": confidence_note if is_approximate else "",
            "reference": reference,
            "metadata": metadata,
        })

    zones = []

    for zone in MAP_ZONES.values():
        zone_name = zone["name"]
        score = int(round(risk_map.get(zone_name, 0)))
        risk_level = map_risk_level(score)

        dominant_source = "No dominant source"
        if zone_source_counts[zone_name]:
            dominant_source = max(zone_source_counts[zone_name], key=zone_source_counts[zone_name].get)

        zones.append({
            "id": zone["id"],
            "name": zone_name,
            "label": zone.get("label", zone_name),
            "risk_score": score,
            "risk_level": risk_level,
            "lat": zone["lat"],
            "lng": zone["lng"],
            "radius_m": zone["radius_m"],
            "risk_weight": zone.get("risk_weight", 1.0),
            "latest_signal_count": recent_zone_signals[zone_name] or zone_signal_counts[zone_name],
            "dominant_source": dominant_source,
            "source_coverage_note": "Patterns may reflect source coverage because available public feeds are uneven.",
            "summary": zone_summary(zone_name, risk_level),
            "trend": map_trend(score),
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "town_id": TOWN_CONFIG_DATA.get("town_id"),
        "display_name": TOWN_DISPLAY_NAME,
        "map_centre": TOWN_CONFIG_DATA.get("map_centre"),
        "approximate_bounding_box": TOWN_CONFIG_DATA.get("approximate_bounding_box"),
        "zones": zones,
        "events": events,
        "signals": events,
        "source_layers": SOURCE_LAYER_FLAGS,
        "map_diagnostics": {
            "total_mapped_events": len(events),
            "exact_coordinate_events": len([event for event in events if event.get("coordinate_confidence") == "exact"]),
            "approximate_coordinate_events": len([event for event in events if event.get("coordinate_confidence") == "approximate"]),
            "zone_fallback_events": len([event for event in events if event.get("coordinate_confidence") == "zone_fallback"]),
            "unmapped_events": 0,
            "latest_mapped_street_manager_event": next((event for event in events if event.get("source") == "Street Manager"), None),
        },
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
        SELECT timestamp, type, location, text, source, real_data, source_event_id, metadata
        FROM events
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    history_rows = []

    for row in rows:
        try:
            metadata = json.loads(row[7]) if row[7] else {}
        except json.JSONDecodeError:
            metadata = {}

        history_rows.append({
            "timestamp": row[0],
            "type": row[1],
            "location": row[2],
            "text": row[3],
            "source": row[4],
            "real_data": bool(row[5]),
            "source_event_id": row[6],
            "metadata": metadata,
        })

    return history_rows


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
    return await handle_street_manager_webhook("permit", request)


@app.post("/webhooks/street-manager/activities")
async def street_manager_activities(request: Request):
    return await handle_street_manager_webhook("activity", request)


@app.post("/webhooks/street-manager/section-58")
async def street_manager_section_58(request: Request):
    return await handle_street_manager_webhook("section-58", request)


@app.post("/dev/force-refresh")
def dev_force_refresh(_: None = Depends(require_dev_access)):
    queued = force_source_refresh()

    return {
        "message": "Source refresh forced.",
        "queued_events": queued,
        **runtime_status(),
    }


@app.post("/dev/clear-live-feed")
def dev_clear_live_feed(_: None = Depends(require_dev_access)):
    history.clear()
    log_agent("Developer Controls", "Live feed memory cleared.", "warning")

    return {
        "message": "Live feed memory cleared.",
        **runtime_status(),
    }


@app.post("/dev/clear-risk-map")
def dev_clear_risk_map(_: None = Depends(require_dev_access)):
    risk_map.clear()
    log_agent("Developer Controls", "Risk map cleared.", "warning")

    return {
        "message": "Risk map cleared.",
        **runtime_status(),
    }


@app.post("/dev/cleanup-retention")
def dev_cleanup_retention(_: None = Depends(require_dev_access)):
    deleted = cleanup_old_records(
        event_retention_days=EVENT_RETENTION_DAYS,
        alert_retention_days=ALERT_RETENTION_DAYS,
        risk_snapshot_retention_days=RISK_SNAPSHOT_RETENTION_DAYS,
    )
    agent_log[:] = agent_log[-80:]
    insights[:] = insights[-100:]
    log_agent("Developer Controls", f"Retention cleanup completed: {deleted}.", "info")

    return {
        "message": "Retention cleanup completed.",
        "deleted": deleted,
        **runtime_status(),
    }


@app.post("/dev/reset-database")
def dev_reset_database(_: None = Depends(require_dev_access)):
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
        source["filtered_out_of_area"] = 0

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
