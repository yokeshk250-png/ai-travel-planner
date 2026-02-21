# POI Service — Firebase Firestore
# FIX: Firestore composite index error.
# Root cause: querying on category_primary + entry_fee + rating simultaneously
#             requires a composite index that may not exist yet.
# Solution:   Query ONLY on category_primary (single-field, auto-indexed).
#             Apply ALL other filters (entry_fee, rating, tags, wheelchair)
#             in Python after fetching documents.
#
# To create the composite index properly, click the link in the error log
# or run: firebase deploy --only firestore:indexes

from config import db, BUDGET_BANDS
from data.packages import PACKAGES
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Dict, List


def _get_places_ref(city: str = "Chennai"):
    """Return Firestore reference to cities/{city}/places."""
    return db.collection("cities").document(city).collection("places")


def resolve_config(package_id: str, budget_band: str, overrides: dict) -> dict:
    """
    Merge package defaults + budget band + user overrides.
    Priority: overrides > budget band > package defaults
    """
    pkg      = PACKAGES.get(package_id, PACKAGES["pkg-heritage"])
    defaults = pkg["defaults"].copy()
    band     = BUDGET_BANDS.get(budget_band, BUDGET_BANDS["economy"])

    return {
        "name":             pkg["name"],
        "category_primary": pkg["category_primary"],
        "tags":             pkg["tags"],
        "activities":       pkg["activities"] + (overrides.get("extra_activities") or []),
        "max_entry_fee":    overrides.get("max_entry_fee")  or band["max_entry_fee"],
        "min_rating":       4.0,
        "transport_mode":   overrides.get("transport_mode") or band["default_transport"],
        "budget_per_day":   overrides.get("total_budget")   or defaults["budget_per_day"],
        "pace":             overrides.get("pace")            or band["pace"],
        "start_time":       overrides.get("start_time")     or defaults["start_time"],
        "end_time":         overrides.get("end_time")       or defaults["end_time"],
        "wheelchair_only":  overrides.get("wheelchair_only") or False,
        "stops_per_day":    band["stops_per_day"],
    }


def filter_pois(
    config: dict,
    city: str = "Chennai",
    excluded: List[str] = []
) -> List[Dict]:
    """
    Query Firestore for POIs matching package + budget constraints.

    Firestore query (single field only — no composite index needed):
      - category_primary IN [...]   ← only indexed field used

    Python filters (all other conditions applied after fetch):
      - entry_fee  <= max_entry_fee
      - rating     >= min_rating
      - tags       (soft match, at least one tag)
      - wheelchair accessibility
      - excluded POI ids
    """
    ref = _get_places_ref(city)

    # ── Single-field Firestore query (no composite index needed) ──────────────
    # Firestore auto-indexes every field individually.
    # We only filter on category_primary here to avoid composite index errors.
    query = (
        ref
        .where(filter=FieldFilter("category_primary", "in", config["category_primary"]))
        .limit(100)   # fetch up to 100 candidates, then Python filters down
    )

    docs = query.stream()
    pois = []

    for doc in docs:
        poi           = doc.to_dict()
        poi["poi_id"] = doc.id

        # ── Python-side filters (no index required) ──────────────────────────

        # Skip excluded POIs
        if poi["poi_id"] in excluded:
            continue

        # Entry fee filter
        try:
            if float(poi.get("entry_fee", 0)) > float(config["max_entry_fee"]):
                continue
        except (TypeError, ValueError):
            pass

        # Rating filter
        try:
            if float(poi.get("rating", 0)) < float(config.get("min_rating", 4.0)):
                continue
        except (TypeError, ValueError):
            pass

        # Wheelchair filter
        if config.get("wheelchair_only") and not poi.get("wheelchair_accessible"):
            continue

        # Tag soft filter (at least one package tag must appear in POI tags)
        if config.get("tags"):
            poi_tags = str(poi.get("tags", ""))
            if not any(tag in poi_tags for tag in config["tags"]):
                continue

        pois.append(poi)

    # Sort by popularity_score DESC, rating DESC
    pois.sort(key=lambda p: (
        -float(p.get("popularity_score", 0)),
        -float(p.get("rating", 0))
    ))

    return pois


def get_poi_by_ids(poi_ids: List[str], city: str = "Chennai") -> List[Dict]:
    """Fetch specific POIs by document IDs (for fixed_pois in day constraints)."""
    if not poi_ids:
        return []

    ref  = _get_places_ref(city)
    pois = []

    for poi_id in poi_ids:
        doc = ref.document(poi_id).get()
        if doc.exists:
            poi           = doc.to_dict()
            poi["poi_id"] = doc.id
            pois.append(poi)

    return pois


def get_city_meta(city: str = "Chennai") -> dict:
    """Get city-level metadata (total_places, etc.)."""
    doc = db.collection("cities").document(city).get()
    return doc.to_dict() if doc.exists else {}
