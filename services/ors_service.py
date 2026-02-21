# ORS Service — OpenRouteService route optimization
# Uses Matrix API for travel time between all candidate POIs,
# then greedy nearest-neighbor to order them per day.
# Falls back to haversine + average speed if no API key.

import numpy as np
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict
from config import ORS_API_KEY

try:
    import openrouteservice
    ors_client = openrouteservice.Client(key=ORS_API_KEY) if ORS_API_KEY else None
except ImportError:
    ors_client = None

# Map internal transport modes to ORS profiles
ORS_PROFILES = {
    "bus":        "driving-car",
    "auto":       "driving-car",
    "cab":        "driving-car",
    "metro":      "driving-car",
    "self_drive": "driving-car",
    "walking":    "foot-walking",
    "cycling":    "cycling-regular"
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance in km between two lat/lon points."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _fallback_matrix(coords: List[List[float]]) -> np.ndarray:
    """Haversine-based travel time matrix (minutes) at 20 km/h average."""
    n = len(coords)
    m = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            m[i][j] = (dist / 20) * 60  # 20 km/h → minutes
    return m


def get_travel_matrix(coords: List[List[float]], mode: str = "auto") -> np.ndarray:
    """
    Return NxN travel time matrix (minutes).
    Uses ORS Matrix API if key available, else haversine fallback.
    """
    if not ors_client or len(coords) < 2:
        return _fallback_matrix(coords)

    profile = ORS_PROFILES.get(mode, "driving-car")
    try:
        matrix = ors_client.distance_matrix(
            locations=coords,
            profile=profile,
            metrics=["duration"],
            units="m"
        )
        return np.array(matrix["durations"]) / 60  # seconds → minutes
    except Exception:
        return _fallback_matrix(coords)


def get_route_details(coords: List[List[float]], mode: str = "auto") -> Dict:
    """
    Return total distance (km) and duration (mins) for an ordered route.
    Uses ORS Directions API if available, else haversine fallback.
    """
    if not ors_client or len(coords) < 2:
        total_km = sum(
            haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
            for i in range(len(coords) - 1)
        )
        return {"distance_km": round(total_km, 2), "duration_mins": round((total_km / 20) * 60, 1)}

    profile = ORS_PROFILES.get(mode, "driving-car")
    try:
        route   = ors_client.directions(coordinates=coords, profile=profile, format="json")
        summary = route["routes"][0]["summary"]
        return {
            "distance_km":   round(summary["distance"] / 1000, 2),
            "duration_mins": round(summary["duration"] / 60, 1)
        }
    except Exception:
        total_km = sum(
            haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
            for i in range(len(coords) - 1)
        )
        return {"distance_km": round(total_km, 2), "duration_mins": round((total_km / 20) * 60, 1)}


def optimize_route_greedy(
    pois: List[Dict],
    start_lat: float,
    start_lon: float,
    mode: str = "auto"
) -> List[Dict]:
    """
    Greedy nearest-neighbor route optimization using ORS travel time matrix.
    Returns pois reordered to minimize total travel time.
    """
    if not pois:
        return []

    # Build coordinate list: hotel (index 0) + all POIs
    coords    = [[start_lat, start_lon]] + [[p["lat"], p["lon"]] for p in pois]
    matrix    = get_travel_matrix(coords, mode)  # (n+1) x (n+1)

    ordered   = []
    remaining = list(range(len(pois)))  # indices into pois list
    cur_idx   = 0  # start from hotel (matrix row 0)

    while remaining:
        # Pick the nearest unvisited POI from current position
        nearest = min(remaining, key=lambda i: matrix[cur_idx][i + 1])
        ordered.append(pois[nearest])
        cur_idx = nearest + 1
        remaining.remove(nearest)

    return ordered
