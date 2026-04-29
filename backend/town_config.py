"""Config-file driven town settings for Town Warden.

The backend keeps Blackpool as the default example, but this module lets a
developer point TOWN_CONFIG at another JSON file without changing application
code. Only safe public fields are exposed through /town-config.
"""

import copy
import json
import os
import re
from functools import lru_cache
from pathlib import Path


DEFAULT_TOWN_CONFIG = "config/towns/blackpool.json"

REQUIRED_FIELDS = {
    "town_id",
    "town_name",
    "display_name",
    "country",
    "timezone",
    "dashboard_title",
    "dashboard_subtitle",
    "public_disclaimer",
    "map_centre",
    "approximate_bounding_box",
    "zones",
    "enabled_sources",
    "source_labels",
}

PUBLIC_FIELDS = {
    "town_id",
    "town_name",
    "display_name",
    "country",
    "timezone",
    "dashboard_title",
    "dashboard_subtitle",
    "public_disclaimer",
    "map_centre",
    "zones",
    "enabled_sources",
    "source_labels",
    "footer_text",
    "project_links",
}

SOURCE_IDS = ("police_uk", "open_meteo", "street_manager")


class TownConfigError(RuntimeError):
    """Raised when the selected town configuration is unusable."""


def _project_root():
    return Path(__file__).resolve().parents[1]


def selected_config_path():
    return os.getenv("TOWN_CONFIG", DEFAULT_TOWN_CONFIG).strip() or DEFAULT_TOWN_CONFIG


def resolve_config_path(path_value=None):
    raw_path = Path(path_value or selected_config_path())

    if raw_path.is_absolute():
        return raw_path

    candidates = [
        Path.cwd() / raw_path,
        _project_root() / raw_path,
        Path(__file__).resolve().parent / raw_path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[1]


def _slug(value):
    text = str(value or "zone").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "zone"


def _as_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TownConfigError(f"Town config field {field_name} must be a number.") from exc


def _normalise_zone(zone, index):
    if not isinstance(zone, dict):
        raise TownConfigError("Each town config zone must be an object.")

    label = str(zone.get("label") or zone.get("name") or f"Zone {index + 1}").strip()
    if not label:
        raise TownConfigError("Town config zones require a name or label.")

    zone_id = str(zone.get("id") or _slug(zone.get("name") or label)).strip()

    return {
        "id": zone_id,
        "name": label,
        "label": label,
        "fallback_lat": _as_float(zone.get("fallback_lat"), f"zones[{index}].fallback_lat"),
        "fallback_lng": _as_float(zone.get("fallback_lng"), f"zones[{index}].fallback_lng"),
        "radius_m": int(zone.get("radius_m", 1000) or 1000),
        "risk_weight": float(zone.get("risk_weight", 1.0) or 1.0),
        "keywords": [str(item).strip() for item in zone.get("keywords", []) if str(item).strip()],
    }


def _with_defaults(data):
    config = copy.deepcopy(data)

    config.setdefault("footer_text", f"Built as a civic-tech prototype for {config.get('display_name', 'this town')}.")
    config.setdefault("project_links", {})
    config.setdefault("local_authority_keywords", [config.get("town_name", "")])
    config.setdefault("highway_authority_keywords", config.get("local_authority_keywords", []))
    config.setdefault("street_manager_relevance_keywords", config.get("local_authority_keywords", []))
    config.setdefault("postcode_prefixes", [])
    config.setdefault("boundary_file", None)

    config["enabled_sources"] = {
        source_id: bool(config.get("enabled_sources", {}).get(source_id, True))
        for source_id in SOURCE_IDS
    }
    config["source_labels"] = {
        "police_uk": "Police.uk",
        "open_meteo": "Open-Meteo",
        "street_manager": "Street Manager",
        **config.get("source_labels", {}),
    }
    config["zones"] = [_normalise_zone(zone, idx) for idx, zone in enumerate(config.get("zones") or [])]

    if not config["zones"]:
        raise TownConfigError("Town config must define at least one zone.")

    map_centre = config.get("map_centre") or {}
    config["map_centre"] = {
        "lat": _as_float(map_centre.get("lat"), "map_centre.lat"),
        "lng": _as_float(map_centre.get("lng"), "map_centre.lng"),
        "zoom": int(map_centre.get("zoom", 12) or 12),
    }

    bounds = config.get("approximate_bounding_box") or {}
    config["approximate_bounding_box"] = {
        "min_lat": _as_float(bounds.get("min_lat"), "approximate_bounding_box.min_lat"),
        "max_lat": _as_float(bounds.get("max_lat"), "approximate_bounding_box.max_lat"),
        "min_lng": _as_float(bounds.get("min_lng"), "approximate_bounding_box.min_lng"),
        "max_lng": _as_float(bounds.get("max_lng"), "approximate_bounding_box.max_lng"),
    }

    return config


def validate_config(data):
    if not isinstance(data, dict):
        raise TownConfigError("Town config JSON must be an object.")

    missing = sorted(field for field in REQUIRED_FIELDS if field not in data)
    if missing:
        raise TownConfigError(f"Town config missing required field(s): {', '.join(missing)}")

    return _with_defaults(data)


@lru_cache(maxsize=4)
def load_town_config(path_value=None):
    path = resolve_config_path(path_value)

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError as exc:
        raise TownConfigError(f"Town config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TownConfigError(f"Town config file is not valid JSON: {path}") from exc

    config = validate_config(data)
    config["_config_path"] = str(path)
    return config


def get_town_config():
    return load_town_config(selected_config_path())


def reload_town_config():
    load_town_config.cache_clear()
    return get_town_config()


def _safe_project_links(links):
    if not isinstance(links, dict):
        return {}

    safe = {}
    blocked_fragments = ("internal", "admin_token", "database_url", "secret", "password")

    for key, value in links.items():
        url = str(value or "").strip()
        lower = url.lower()
        if not lower.startswith(("https://", "http://")):
            continue
        if any(fragment in lower for fragment in blocked_fragments):
            continue
        safe[str(key)] = url

    return safe


def public_town_config(config=None):
    config = config or get_town_config()
    public = {key: copy.deepcopy(config[key]) for key in PUBLIC_FIELDS if key in config}
    public["project_links"] = _safe_project_links(public.get("project_links"))
    return public
