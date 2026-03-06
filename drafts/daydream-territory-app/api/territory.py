"""
DayDream Dental — Territory Scanner API
Vercel serverless function: GET /api/territory?city=Chicago, IL&radius=10&max=15

Returns ranked dental practices scored by Claude Haiku.
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import re
import time
import concurrent.futures

import googlemaps
import anthropic


# ── Known DSO chains — instant score=0 without any AI call ──────────────────
KNOWN_DSOS = [
    "aspen dental", "heartland dental", "pacific dental", "western dental",
    "bright now", "castle dental", "affordable dentures", "dental care alliance",
    "sage dental", "mb2 dental", "foreversmile", "smile brands",
    "dentalworks", "dental works", "comfort dental", "coast dental",
    "great expressions", "perfect teeth", "gentle dental", "clear choice",
    "clearchoice", "altus dental", "birner dental", "kool smiles",
    "small smiles", "community dental",
]

SCORING_SYSTEM = """You are a dental industry analyst screening practices for DayDream Dental — AI billing automation for INDEPENDENT dental practices.

DSOs (Dental Support Organizations / corporate chains) are BAD targets. They have centralized in-house billing staff and don't need DayDream. Independent practices that handle their own billing are the ideal customer.

Given a practice name, address, and website, score it and return ONLY valid JSON (no text before or after):

{
  "independence": {"score": <int 0-40>, "is_dso": <bool>, "evidence": "<one sentence>"},
  "practice_size": {"score": <int 0-30>, "dentist_count": <int or null>, "evidence": "<one sentence>"},
  "billing_complexity": {"score": <int 0-20>, "specialties": [<list>], "evidence": "<one sentence>"},
  "key_signals": [<3-5 short bullets a sales rep would want to know>]
}

Scoring guide:
- Independence (0-40): confirmed independent=35-40, unclear=20-25, some DSO signals=5-15, confirmed DSO=0
- Practice size (0-30): 4+ dentists or open 7 days=25-30, 2-3 dentists or 6 days=16-22, solo 5 days=10-15, unknown=15
- Billing complexity (0-20): multi-specialty=12-20, general+many insurance=8-12, general few plans=4-8, cash only=2-5"""


def is_known_dso(name: str) -> str | None:
    lower = name.lower()
    for dso in KNOWN_DSOS:
        if dso in lower:
            return dso.title()
    return None


def velocity_score(most_recent_days: int | None) -> int:
    """Score based on how recently a Google review was posted."""
    if most_recent_days is None: return 3   # no data — neutral
    if most_recent_days <= 30:   return 10
    if most_recent_days <= 90:   return 7
    if most_recent_days <= 180:  return 4
    return 2


def priority_label(total: int) -> str:
    if total >= 70: return "Hot Lead"
    if total >= 50: return "Warm Lead"
    if total >= 30: return "Research"
    return "Skip"


def dso_risk_label(ind_score: int) -> str:
    if ind_score <= 10: return "High"
    if ind_score <= 25: return "Medium"
    return "Low"


def parse_score_json(raw: str) -> dict:
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {
        "independence": {"score": 20, "is_dso": False, "evidence": "Could not assess"},
        "practice_size": {"score": 15, "dentist_count": None, "evidence": "Could not assess"},
        "billing_complexity": {"score": 10, "specialties": [], "evidence": "Could not assess"},
        "key_signals": ["Manual review recommended"],
    }


def score_with_claude(client: anthropic.Anthropic, name: str, address: str, website: str | None) -> dict:
    context = f"Practice: {name}\nLocation: {address}\nWebsite: {website or 'Not found'}"
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=450,
        temperature=0,
        system=SCORING_SYSTEM,
        messages=[{"role": "user", "content": context}],
    )
    return parse_score_json(response.content[0].text)


# ── Google Places discovery ──────────────────────────────────────────────────

PLACE_FIELDS = [
    "name", "formatted_address", "formatted_phone_number", "website",
    "rating", "user_ratings_total", "place_id", "business_status", "geometry",
    "reviews",
]

CLUB_FIELDS = [
    "name", "formatted_address", "formatted_phone_number", "website",
    "place_id", "geometry",
]

CLUB_QUERIES = [
    "dental study club",
    "dental society",
    "dental association",
]


def discover_study_clubs(gmaps_client, city: str) -> list[dict]:
    """Find dental study clubs / societies near city via text search."""
    seen = set()
    clubs = []

    def fetch_club_detail(pid: str) -> dict | None:
        try:
            return gmaps_client.place(place_id=pid, fields=CLUB_FIELDS).get("result", {})
        except Exception:
            return None

    for query in CLUB_QUERIES:
        try:
            resp = gmaps_client.places(query=f"{query} {city}")
        except Exception:
            continue
        place_ids = [r["place_id"] for r in resp.get("results", [])[:5]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            for detail in ex.map(fetch_club_detail, place_ids):
                if not detail:
                    continue
                pid = detail.get("place_id", "")
                if pid in seen:
                    continue
                seen.add(pid)
                loc = detail.get("geometry", {}).get("location", {})
                clubs.append({
                    "name": detail.get("name", ""),
                    "address": detail.get("formatted_address", ""),
                    "phone": detail.get("formatted_phone_number", ""),
                    "website": detail.get("website"),
                    "place_id": pid,
                    "lat": loc.get("lat"),
                    "lng": loc.get("lng"),
                })

    return clubs


def discover(gmaps_client, city: str, radius_miles: float, max_results: int) -> list[dict]:
    geo = gmaps_client.geocode(city)
    if not geo:
        raise ValueError(f"Could not geocode '{city}'")

    lat = geo[0]["geometry"]["location"]["lat"]
    lon = geo[0]["geometry"]["location"]["lng"]
    radius_m = int(radius_miles * 1609.34)

    response = gmaps_client.places_nearby(
        location=(lat, lon), radius=radius_m, type="dentist"
    )
    place_ids = [r["place_id"] for r in response.get("results", [])][:max_results]

    def fetch_detail(pid: str) -> dict | None:
        try:
            return gmaps_client.place(place_id=pid, fields=PLACE_FIELDS).get("result", {})
        except Exception:
            return None

    practices = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for detail in ex.map(fetch_detail, place_ids):
            if not detail or detail.get("business_status") == "CLOSED_PERMANENTLY":
                continue
            loc = detail.get("geometry", {}).get("location", {})
            reviews = detail.get("reviews", [])
            if reviews:
                most_recent_ts = max(r.get("time", 0) for r in reviews)
                most_recent_days = int((time.time() - most_recent_ts) / 86400)
            else:
                most_recent_days = None
            practices.append({
                "name": detail.get("name", ""),
                "address": detail.get("formatted_address", ""),
                "phone": detail.get("formatted_phone_number", ""),
                "website": detail.get("website"),
                "rating": detail.get("rating", 0.0),
                "review_count": detail.get("user_ratings_total", 0),
                "most_recent_review_days": most_recent_days,
                "place_id": detail.get("place_id", ""),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
            })
    return practices


# ── Full pipeline ────────────────────────────────────────────────────────────

def run_scan(city: str, radius: float, max_results: int) -> list[dict]:
    gmaps_key     = os.environ.get("GOOGLE_MAPS_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not gmaps_key:
        raise EnvironmentError("GOOGLE_MAPS_API_KEY is not set")
    if not anthropic_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")

    gmaps = googlemaps.Client(key=gmaps_key)
    claude = anthropic.Anthropic(api_key=anthropic_key)

    # Run practice discovery and study club discovery in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_practices = ex.submit(discover, gmaps, city, radius, max_results)
        f_clubs     = ex.submit(discover_study_clubs, gmaps, city)
        practices   = f_practices.result()
        clubs       = f_clubs.result()

    if not practices:
        return {"practices": [], "clubs": clubs}

    def score_one(p: dict) -> dict:
        hard_dso = is_known_dso(p["name"])
        if hard_dso:
            result = {
                "independence": {"score": 0, "is_dso": True, "evidence": f"Known DSO chain: {hard_dso}"},
                "practice_size": {"score": 15, "dentist_count": None, "evidence": "DSO — scoring skipped"},
                "billing_complexity": {"score": 10, "specialties": [], "evidence": "DSO — scoring skipped"},
                "key_signals": [f"DSO chain ({hard_dso})", "Has centralized in-house billing", "Not a DayDream target"],
            }
        else:
            result = score_with_claude(claude, p["name"], p["address"], p.get("website"))

        ind = result.get("independence", {})
        ind_score  = min(int(ind.get("score", 20)), 40)
        is_dso     = hard_dso is not None or bool(ind.get("is_dso", False))
        size_score = min(int(result.get("practice_size", {}).get("score", 15)), 30)
        bill_score = min(int(result.get("billing_complexity", {}).get("score", 10)), 20)
        vel        = velocity_score(p.get("most_recent_review_days"))
        total      = ind_score + size_score + bill_score + vel

        return {
            **p,
            "independence_score": ind_score,
            "size_score": size_score,
            "billing_complexity_score": bill_score,
            "velocity_score": vel,
            "total_score": total,
            "is_dso": is_dso,
            "dso_name": hard_dso or ind.get("dso_name"),
            "dso_risk": dso_risk_label(ind_score),
            "priority": priority_label(total),
            "key_signals": result.get("key_signals", []),
            "independence_evidence": result.get("independence", {}).get("evidence", ""),
            "size_evidence": result.get("practice_size", {}).get("evidence", ""),
            "billing_evidence": result.get("billing_complexity", {}).get("evidence", ""),
        }

    # 5 concurrent Claude calls — stays within rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        scored = list(ex.map(score_one, practices))

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    for i, p in enumerate(scored):
        p["rank"] = i + 1
    return {"practices": scored, "clubs": clubs}


# ── Vercel handler ───────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        city   = params.get("city",   ["San Francisco, CA"])[0]
        radius = float(params.get("radius", ["10"])[0])
        max_r  = min(int(params.get("max",  ["15"])[0]), 20)

        try:
            result = run_scan(city, radius, max_r)
            body   = json.dumps({"city": city, "radius": radius, **result})
            status = 200
        except Exception as e:
            body   = json.dumps({"error": str(e)})
            status = 500

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass
