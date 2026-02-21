# POI Service — Firebase Firestore
#
# IMPROVEMENTS IN STEP 2:
#   1. Opening hours check   — skip POIs closed during the day window
#   2. Tag SCORING           — count matching tags instead of binary yes/no
#   3. Tag-less fallback     — if tag filter returns 0 results, fall back to category-only
#   4. Safe override merge   — use `is not None` so max_entry_fee=0 (free) is respected
#   5. Relevance sort        — sort by tag_score + popularity + rating combined

from config import db, BUDGET_BANDS
from data.packages import PACKAGES
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
from typing import Dict, List, Optional


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _get_places_ref(city: str = "Chennai"):
    return db.collection("cities").document(city).collection("places")


def _to_list(value) -> List[str]:
    """Normalise Firestore array or comma-string to a Python list."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    return [s.strip() for s in str(value).split(",") if s.strip()]


def _parse_time(t: str) -> Optional[datetime]:
    """Parse HH:MM to datetime. Returns None if unparseable."""
    for fmt in ("%H:%M", "%I:%M %p", "%H.%M"):
        try:
            return datetime.strptime(t.strip(), fmt)
        except ValueError:
            continue
    return None


def _is_open_during(poi: dict, day_start: str, day_end: str) -> bool:
    """
    FIX 1 — Opening hours check.
    Returns True if the POI is open at ANY point during the day window.
    Fields used: is_open_24hrs (bool), opening_hours (str '05:00-20:00').
    Fails open (returns True) if hours are missing or unparseable.
    """
    if poi.get("is_open_24hrs"):
        return True

    hours = poi.get("opening_hours", "")
    if not hours or "-" not in str(hours):
        return True  # no data → assume open

    try:
        open_str, close_str = str(hours).split("-", 1)
        opens  = _parse_time(open_str)
        closes = _parse_time(close_str)
        starts = _parse_time(day_start)
        ends   = _parse_time(day_end)

        if not all([opens, closes, starts, ends]):
            return True  # can't parse → assume open

        # POI open window must overlap with day window
        # Overlap exists unless POI closes before day starts OR opens after day ends
        return not (closes <= starts or opens >= ends)
    except Exception:
        return True  # any error → assume open


def _tag_score(poi: dict, package_tags: List[str]) -> int:
    """
    FIX 2 — Tag scoring.
    Count how many package tags appear in POI tags.
    Returns 0..len(package_tags). Used for relevance ranking.
    """
    if not package_tags:
        return 0
    poi_tags = set(_to_list(poi.get("tags", [])))
    return sum(1 for t in package_tags if t in poi_tags)


def _override(overrides: dict, key: str, fallback):
    """
    FIX 4 — Safe override merge.
    Use `is not None` so that override value 0 (e.g. free-only filter)
    is NOT skipped by the old `overrides.get(key) or fallback` pattern.
    """
    v = overrides.get(key)
    return v if v is not None else fallback


# ── Public API ──────────────────────────────────────────────────────────────────────

def resolve_config(package_id: str, budget_band: str, overrides: dict) -> dict:
    """
    Merge package defaults + budget band + user overrides.
    Priority: overrides > budget band > package defaults.
    Uses safe _override() for numeric fields so 0 is respected.
    """
    pkg      = PACKAGES.get(package_id, PACKAGES["pkg-heritage"])
    defaults = pkg["defaults"].copy()
    band     = BUDGET_BANDS.get(budget_band, BUDGET_BANDS["economy"])

    return {
        "name":             pkg["name"],
        "category_primary": pkg["category_primary"],
        "tags":             pkg["tags"],
        "activities":       pkg["activities"] + (overrides.get("extra_activities") or []),
        # FIX 4: use _override() so max_entry_fee=0 (free-only) is not ignored
        "max_entry_fee":    _override(overrides, "max_entry_fee",  band["max_entry_fee"]),
        "min_rating":       4.0,
        "transport_mode":   _override(overrides, "transport_mode", band["default_transport"]),
        "budget_per_day":   _override(overrides, "total_budget",   defaults["budget_per_day"]),
        "pace":             _override(overrides, "pace",            band["pace"]),
        "start_time":       _override(overrides, "start_time",      defaults["start_time"]),
        "end_time":         _override(overrides, "end_time",        defaults["end_time"]),
        "wheelchair_only":  _override(overrides, "wheelchair_only", False),
        "stops_per_day":    band["stops_per_day"],
    }


def filter_pois(
    config: dict,
    city: str = "Chennai",
    excluded: List[str] = []
) -> List[Dict]:
    """
    IMPROVED Step 2 — Filter + score POIs from Firestore.

    Firestore query  : category_primary IN [...]  (no composite index needed)
    Hard filters     : entry_fee, rating, wheelchair, excluded, opening hours
    Soft scoring     : tag_score (0–N matching tags)
    Fallback         : if tag filter yields 0, return category-only results
    Sort             : tag_score DESC → popularity DESC → rating DESC
    """
    ref = _get_places_ref(city)

    query = (
        ref
        .where(filter=FieldFilter("category_primary", "in", config["category_primary"]))
        .limit(100)
    )

    docs       = query.stream()
    passed     = []   # passed ALL hard filters + at least 1 tag match
    no_tag     = []   # passed hard filters but 0 tag matches (fallback pool)

    day_start  = config.get("start_time", "09:00")
    day_end    = config.get("end_time",   "20:00")
    pkg_tags   = config.get("tags", [])
    max_fee    = float(config["max_entry_fee"])
    min_rating = float(config.get("min_rating", 4.0))

    for doc in docs:
        poi           = doc.to_dict()
        poi["poi_id"] = doc.id

        # ── Hard filter: excluded ────────────────────────────────────────────
        if poi["poi_id"] in excluded:
            continue

        # ── Hard filter: entry fee ─────────────────────────────────────────
        try:
            if float(poi.get("entry_fee", 0) or 0) > max_fee:
                continue
        except (TypeError, ValueError):
            pass

        # ── Hard filter: rating ───────────────────────────────────────────
        try:
            if float(poi.get("rating", 0) or 0) < min_rating:
                continue
        except (TypeError, ValueError):
            pass

        # ── Hard filter: wheelchair ───────────────────────────────────────
        if config.get("wheelchair_only") and not poi.get("wheelchair_accessible"):
            continue

        # ── FIX 1: Opening hours check ─────────────────────────────────────
        if not _is_open_during(poi, day_start, day_end):
            continue

        # ── FIX 2: Tag scoring (soft — score 0 goes to fallback, not dropped) ──
        score = _tag_score(poi, pkg_tags)
        poi["_tag_score"] = score

        if score > 0 or not pkg_tags:
            passed.append(poi)
        else:
            no_tag.append(poi)  # category match but no tag match

    # ── FIX 3: Fallback if tag filter wiped everything ───────────────────────
    # e.g. package wants ["fort", "colonial"] but all POIs have different tags
    pool = passed if passed else no_tag

    # ── FIX 5: Relevance sort: tag_score → popularity → rating ──────────────
    pool.sort(key=lambda p: (
        -int(p.get("_tag_score", 0)),
        -float(p.get("popularity_score", 0) or 0),
        -float(p.get("rating", 0) or 0)
    ))

    # Strip internal scoring key before returning
    for p in pool:
        p.pop("_tag_score", None)

    return pool


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
    doc = db.collection("cities").document(city).get()
    return doc.to_dict() if doc.exists else {}
