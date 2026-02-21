# Scheduler — builds concrete time slots for each day
# Uses ORS-optimized route order, then assigns arrival/departure
# times respecting day window, POI duration, and pace limits.
#
# FIX: Firestore stores activities, best_time_to_visit, tags as ARRAYS.
#      All helpers now accept both list and string gracefully.

from datetime import datetime, timedelta
from typing import List, Dict, Union
from models.schemas import TimeSlot, DaySchedule, DayConstraint
from services.ors_service import optimize_route_greedy, haversine
from config import TRANSPORT_RATES, TRANSPORT_SPEED, ACTIVITY_EXTRAS

PACE_STOPS = {"relaxed": (2, 3), "normal": (3, 5), "packed": (5, 7)}


def _parse(t: str) -> datetime:
    return datetime.strptime(t, "%H:%M")


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _to_list(value) -> List[str]:
    """
    Normalise a Firestore field to a clean Python list.
    Handles: list, comma-string, None, empty.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    # comma-separated string fallback
    return [s.strip() for s in str(value).split(",") if s.strip()]


def _to_str(value) -> str:
    """
    Normalise a Firestore field to a plain string.
    Handles: list → 'a, b, c', string → as-is, None → ''
    """
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def transport_cost(dist_km: float, mode: str) -> float:
    r = TRANSPORT_RATES.get(mode, TRANSPORT_RATES["auto"])
    return round(r["base"] + r["per_km"] * dist_km, 2)


def travel_mins(dist_km: float, mode: str) -> int:
    speed = TRANSPORT_SPEED.get(mode, 20)
    return max(5, int((dist_km / speed) * 60))


def activity_extra_cost(activities) -> float:
    """
    Calculate extra activity costs.
    Accepts both list (Firestore) and comma-string (legacy).
    """
    acts = _to_list(activities)
    return sum(ACTIVITY_EXTRAS.get(a, 0) for a in acts)


def schedule_day(
    pois:           List[Dict],
    dc:             DayConstraint,
    transport_mode: str,
    hotel_lat:      float,
    hotel_lon:      float
) -> DaySchedule:
    """
    Build a DaySchedule from a filtered+ordered list of POIs.
    Steps:
      1. Cap candidates by pace
      2. ORS greedy route optimization
      3. Assign arrival/departure times sequentially
      4. Stop when day window is full
      5. Add return-to-hotel transport cost
    """
    effective_mode = dc.transport_override or transport_mode
    _, max_stops   = PACE_STOPS[dc.pace]

    # Optimize order using ORS matrix
    candidates = pois[:max_stops * 2]  # wider pool, then cap
    ordered    = optimize_route_greedy(candidates[:max_stops], hotel_lat, hotel_lon, effective_mode)

    slots           = []
    cur_time        = _parse(dc.start_time)
    end_time        = _parse(dc.end_time)
    prev_lat        = hotel_lat
    prev_lon        = hotel_lon
    day_entry       = 0.0
    day_transport   = 0.0
    day_extras      = 0.0
    total_mins_used = 0

    for poi in ordered:
        dist   = haversine(prev_lat, prev_lon, poi["lat"], poi["lon"])
        t_mins = travel_mins(dist, effective_mode)
        t_cost = transport_cost(dist, effective_mode)
        fee    = float(poi.get("entry_fee", 0) or 0)
        dur    = int(poi.get("duration_minutes", 60) or 60)

        # ── FIX: activities is an array in Firestore ────────────────────────
        activities_list = _to_list(poi.get("activities", []))
        ext             = activity_extra_cost(activities_list)

        # ── FIX: best_time_to_visit is an array in Firestore ────────────────
        best_time_str = _to_str(poi.get("best_time_to_visit", ""))

        arrive = cur_time + timedelta(minutes=t_mins)
        depart = arrive + timedelta(minutes=dur)

        # Stop if this POI would push past end_time
        if depart > end_time:
            break

        slots.append(TimeSlot(
            poi_id                = poi["poi_id"],
            name                  = poi["name"],
            start_time            = _fmt(arrive),
            end_time              = _fmt(depart),
            duration_mins         = dur,
            travel_from_prev_mins = t_mins,
            travel_from_prev_cost = t_cost,
            entry_fee             = fee,
            activity_extras       = ext,
            slot_total            = round(fee + t_cost + ext, 2),
            lat                   = float(poi["lat"]),
            lon                   = float(poi["lon"]),
            address               = poi.get("address", ""),
            activities            = activities_list,   # ✔ proper list
            rating                = float(poi.get("rating", 0) or 0),
            best_time             = best_time_str      # ✔ always a string
        ))

        day_entry       += fee
        day_transport   += t_cost
        day_extras      += ext
        total_mins_used += t_mins + dur
        cur_time         = depart
        prev_lat, prev_lon = float(poi["lat"]), float(poi["lon"])

    # Return to hotel
    ret_dist        = haversine(prev_lat, prev_lon, hotel_lat, hotel_lon)
    ret_cost        = transport_cost(ret_dist, effective_mode)
    ret_mins        = travel_mins(ret_dist, effective_mode)
    day_transport  += ret_cost
    total_mins_used += ret_mins

    available_mins = int((_parse(dc.end_time) - _parse(dc.start_time)).total_seconds() / 60)

    return DaySchedule(
        day_number=dc.day_number,
        slots=slots,
        total_mins=total_mins_used,
        free_mins=max(0, available_mins - total_mins_used),
        cost_breakdown={
            "entry":            round(day_entry, 2),
            "transport":        round(day_transport, 2),
            "extras":           round(day_extras, 2),
            "return_transport": round(ret_cost, 2),
            "total":            round(day_entry + day_transport + day_extras, 2)
        }
    )
