# POI Service — Firebase Firestore
# FIX 1: Simplified Firestore query (single field) to avoid composite index errors.
# FIX 2: tags stored as Firestore ARRAY — use proper list membership check.

from config import db, BUDGET_BANDS
from data.packages import PACKAGES
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Dict, List


def _get_places_ref(city: str = "Chennai"):
    """Return Firestore reference to cities/{city}/places."""
    return db.collection("cities").document(city).collection("places")


def _to_list(value) -> List[str]:
    """
    Normalise a Firestore field to a Python list.
    Handles: Firestore array (list), comma-string, None.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    return [s.strip() for s in str(value).split(",") if s.strip()]


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

    Firestore query (single field — no composite index needed):
      - category_primary IN [...]

    Python filters (applied after fetch):
      - entry_fee  <= max_entry_fee
      - rating     >= min_rating
      - tags       (list intersection check)
      - wheelchair accessibility
      - excluded POI ids
    """
    ref = _get_places_ref(city)

    query = (
        ref
        .where(filter=FieldFilter("category_primary", "in", config["category_primary"]))
        .limit(100)
    )

    docs = query.stream()
    pois = []

    for doc in docs:
        poi           = doc.to_dict()
        poi["poi_id"] = doc.id

        # Skip excluded
        if poi["poi_id"] in excluded:
            continue

        # Entry fee
        try:
            if float(poi.get("entry_fee", 0) or 0) > float(config["max_entry_fee"]):
                continue
        except (TypeError, ValueError):
            pass

        # Rating
        try:
            if float(poi.get("rating", 0) or 0) < float(config.get("min_rating", 4.0)):
                continue
        except (TypeError, ValueError):
            pass

        # Wheelchair
        if config.get("wheelchair_only") and not poi.get("wheelchair_accessible"):
            continue

        # ── FIX: tags is a Firestore ARRAY — use list intersection ─────────────
        if config.get("tags"):
            poi_tags = _to_list(poi.get("tags", []))
            if not any(tag in poi_tags for tag in config["tags"]):
                continue

        pois.append(poi)

    # Sort: popularity_score DESC, rating DESC
    pois.sort(key=lambda p: (
        -float(p.get("popularity_score", 0) or 0),
        -float(p.get("rating", 0) or 0)
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
