"""Create a starter Town Warden town config from the Blackpool example."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "towns" / "blackpool.json"
DEST_DIR = ROOT / "config" / "towns"


def slugify(value):
    text = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return text.strip("-") or "example-town"


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def main():
    town_name = ask("Town name", "Example Town")
    display_name = ask("Public display name", town_name)
    lat = float(ask("Map centre latitude", "53.0"))
    lng = float(ask("Map centre longitude", "-2.0"))
    town_id = slugify(town_name)

    destination = DEST_DIR / f"{town_id}.json"
    if destination.exists():
        raise SystemExit(f"{destination} already exists. Choose another town name or edit the file directly.")

    config = json.loads(SOURCE.read_text(encoding="utf-8"))
    config["town_id"] = town_id
    config["town_name"] = town_name
    config["display_name"] = display_name
    config["dashboard_subtitle"] = f"{display_name} Civic Intelligence Prototype"
    config["footer_text"] = (
        f"Built as a civic-tech prototype for {display_name}. "
        "Not an official council, police, NHS, or emergency-service system."
    )
    config["map_centre"] = {"lat": lat, "lng": lng, "zoom": 12}
    config["approximate_bounding_box"] = {
        "min_lat": round(lat - 0.08, 6),
        "max_lat": round(lat + 0.08, 6),
        "min_lng": round(lng - 0.08, 6),
        "max_lng": round(lng + 0.08, 6),
    }
    config["local_authority_keywords"] = [display_name]
    config["highway_authority_keywords"] = [display_name]
    config["street_manager_relevance_keywords"] = [display_name]
    config["postcode_prefixes"] = []

    for zone in config["zones"]:
        zone["fallback_lat"] = lat
        zone["fallback_lng"] = lng
        zone["keywords"] = [zone["label"].lower()]

    destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    print(f"Created {destination}")
    print("Next steps:")
    print("1. Edit zones, bounding box, postcode prefixes, and authority keywords.")
    print(f"2. Set TOWN_CONFIG=config/towns/{destination.name}")
    print("3. Run backend tests and check /town-config locally.")


if __name__ == "__main__":
    main()
