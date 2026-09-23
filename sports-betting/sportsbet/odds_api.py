"""Minimal client for The Odds API v4 (https://the-odds-api.com)."""

import json
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsAPIError(Exception):
    pass


def _get(path, params):
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            remaining = resp.headers.get("x-requests-remaining")
            return json.load(resp), remaining
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise OddsAPIError(f"HTTP {e.code} for {path}: {body}") from e


def list_sports(api_key):
    """Return in-season sports that have head-to-head games (no futures/outrights)."""
    sports, _ = _get("/sports/", {"apiKey": api_key})
    return [s for s in sports if s.get("active") and not s.get("has_outrights")]


def get_odds(api_key, sport_key, regions="us,eu", markets="h2h"):
    """Return (events, requests_remaining) for one sport.

    Each call costs (number of regions x number of markets) requests from the quota.
    """
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    return _get(f"/sports/{sport_key}/odds/", params)
