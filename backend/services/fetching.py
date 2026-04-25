"""Small HTTP/JSON helper used by public-data connectors."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def fetch_json(url, timeout=8):
    """Return parsed JSON from a URL, or None if the request fails."""
    try:
        with urlopen(url, timeout=timeout) as response:
            raw = response.read()
            text = raw.decode("utf-8")
            return json.loads(text)
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return None
