import os
import requests
from functools import lru_cache

WALKSCORE_BASE = "https://api.walkscore.com/score"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
RENTCAST_BASE  = "https://api.rentcast.io/v1"

CENSUS_BASE = "https://api.census.gov/data/2024/acs/acs5"
CENSUS_VARS = "NAME,B19013_001E,B01003_001E,B25003_001E,B25003_003E"

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
    "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
    "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
    "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
    "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    "DC": "11",
}

# Sentinel value Census uses for missing/suppressed data
_CENSUS_NULL = "-666666666"


def _safe_int(value: str) -> int | None:
    if value and value != _CENSUS_NULL:
        try:
            return int(value)
        except ValueError:
            pass
    return None


@lru_cache(maxsize=128)
def fetch_census_data(city: str, state: str) -> dict:
    """
    Fetch city-level demographics from the ACS 5-Year estimates.
    Cached by (city, state) so duplicate leads don't make repeat calls.
    Returns a dict with income, population, and renter % (or empty dict on failure).
    """
    fips = STATE_FIPS.get(state.upper())
    if not fips:
        return {}

    url = f"{CENSUS_BASE}?get={CENSUS_VARS}&for=place:*&in=state:{fips}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
    except Exception:
        return {}

    headers = rows[0]
    idx = {h: i for i, h in enumerate(headers)}

    city_lower = city.lower()
    best = None
    best_pop = -1

    for row in rows[1:]:
        place_name = row[idx["NAME"]].lower()
        if city_lower not in place_name:
            continue
        pop = _safe_int(row[idx["B01003_001E"]]) or 0
        if pop > best_pop:
            best_pop = pop
            best = row

    if best is None:
        return {}

    total_housing = _safe_int(best[idx["B25003_001E"]])
    renter_units = _safe_int(best[idx["B25003_003E"]])
    renter_pct = (
        round(renter_units / total_housing * 100, 1)
        if total_housing and renter_units
        else None
    )
    return {
        "median_household_income": _safe_int(best[idx["B19013_001E"]]),
        "population": _safe_int(best[idx["B01003_001E"]]),
        "renter_occupied_pct": renter_pct,
    }


@lru_cache(maxsize=256)
def _geocode(address: str, city: str, state: str) -> tuple[float, float] | None:
    """Convert a street address to (lat, lon) using OpenStreetMap Nominatim."""
    query = f"{address}, {city}, {state}"
    try:
        resp = requests.get(
            NOMINATIM_BASE,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "EliseAI-LeadTool/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


@lru_cache(maxsize=256)
def _fetch_walkscore_cached(address: str, city: str, state: str, api_key: str) -> dict:
    """Cached by (address, city, state, api_key) so a missing key never poisons the cache."""
    coords = _geocode(address, city, state)
    if not coords:
        return {}

    lat, lon = coords
    full_address = f"{address}, {city}, {state}"
    try:
        resp = requests.get(
            WALKSCORE_BASE,
            params={
                "format": "json",
                "address": full_address,
                "lat": lat,
                "lon": lon,
                "transit": 1,
                "bike": 1,
                "wsapikey": api_key,
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 1:
            return {}
        return {
            "walk_score": data.get("walkscore"),
            "walk_description": data.get("description"),
            "transit_score": data.get("transit", {}).get("score"),
            "transit_description": data.get("transit", {}).get("description"),
            "bike_score": data.get("bike", {}).get("score"),
            "bike_description": data.get("bike", {}).get("description"),
        }
    except Exception:
        return {}


def fetch_walkscore(address: str, city: str, state: str) -> dict:
    """Public wrapper — reads the API key fresh each call so .env changes take effect on restart."""
    api_key = os.environ.get("WALKSCORE_API_KEY")
    if not api_key:
        return {}
    return _fetch_walkscore_cached(address, city, state, api_key)


@lru_cache(maxsize=256)
def _fetch_rentcast_cached(address: str, city: str, state: str, api_key: str) -> dict:
    full_address = f"{address}, {city}, {state}"
    try:
        resp = requests.get(
            f"{RENTCAST_BASE}/properties",
            params={"address": full_address, "limit": 1},
            headers={"X-Api-Key": api_key, "accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 404:
            return {"found": False, "property_type": None}
        resp.raise_for_status()
        data = resp.json()
        prop = data[0] if isinstance(data, list) else data
        if not prop:
            return {"found": False, "property_type": None}
        return {
            "found": True,
            "property_type": prop.get("propertyType"),  # may be None even when found
        }
    except Exception:
        return {"found": False, "property_type": None}


def fetch_rentcast(address: str, city: str, state: str) -> dict:
    """Public wrapper — reads API key fresh so .env changes take effect on restart."""
    api_key = os.environ.get("RENTCAST_API_KEY")
    if not api_key:
        return {}
    
    return _fetch_rentcast_cached(address, city, state, api_key)


def _extract_domain(email: str) -> str | None:
    if email and "@" in email:
        return email.split("@")[-1].lower()
    return None


def enrich_lead(lead: dict) -> dict:
    """Enrich a single lead dict with Census, WalkScore, RentCast, and email domain."""
    census = fetch_census_data(lead.get("city", ""), lead.get("state", ""))
    walkscore = fetch_walkscore(
        lead.get("address", ""), lead.get("city", ""), lead.get("state", "")
    )
    rentcast = fetch_rentcast(
        lead.get("address", ""), lead.get("city", ""), lead.get("state", "")
    )

    return {
        **lead,
        "enrichment": {
            "census": census,
            "walkscore": walkscore,
            "rentcast": rentcast,
            "email_domain": _extract_domain(lead.get("email", "")),
        },
    }
