from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any


class DayConstraint(BaseModel):
    day_number:         int
    start_time:         str = "09:00"
    end_time:           str = "19:00"
    pace:               Literal["relaxed", "normal", "packed"] = "normal"
    fixed_pois:         List[str] = []
    excluded_pois:      List[str] = []
    max_budget:         Optional[float] = None
    transport_override: Optional[str]   = None


class PackageOverride(BaseModel):
    transport_mode:   Optional[str]       = None
    max_entry_fee:    Optional[float]     = None
    total_budget:     Optional[float]     = None
    num_days:         Optional[int]       = None
    start_time:       Optional[str]       = None
    end_time:         Optional[str]       = None
    pace:             Optional[str]       = None
    wheelchair_only:  Optional[bool]      = None
    extra_activities: Optional[List[str]] = []


class TripRequest(BaseModel):
    package_id:      str
    city:            str = "Chennai"
    num_days:        int = 1
    budget_band:     Literal["budget", "economy", "premium"] = "economy"
    hotel_lat:       Optional[float] = 13.0827
    hotel_lon:       Optional[float] = 80.2707
    overrides:       PackageOverride = PackageOverride()
    day_constraints: List[DayConstraint] = []


class ChatRequest(BaseModel):
    message:   str
    city:      str = "Chennai"
    hotel_lat: Optional[float] = None
    hotel_lon: Optional[float] = None


class TimeSlot(BaseModel):
    poi_id:                str
    name:                  str
    start_time:            str
    end_time:              str
    duration_mins:         int
    travel_from_prev_mins: int
    travel_from_prev_cost: float
    entry_fee:             float
    activity_extras:       float
    slot_total:            float
    lat:                   float
    lon:                   float
    address:               str
    activities:            List[str]
    rating:                float
    best_time:             str


class DaySchedule(BaseModel):
    day_number:     int
    slots:          List[TimeSlot]
    total_mins:     int
    free_mins:      int
    cost_breakdown: Dict[str, Any]


class CostSummary(BaseModel):
    grand_total:      float
    total_budget:     float
    within_budget:    bool
    budget_remaining: float
    per_day_avg:      float
    transport_mode:   str
    warnings:         List[str] = []


class ItineraryResponse(BaseModel):
    trip_id:        str
    city:           str
    package_name:   str
    num_days:       int
    transport_mode: str
    days:           List[DaySchedule]
    cost_summary:   CostSummary
    llm_summary:    Optional[str] = None
    suggestions:    List[str] = []
