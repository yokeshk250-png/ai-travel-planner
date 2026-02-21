# Planner — main orchestrator
# Coordinates: POI filtering → ORS routing → scheduling → costing → LLM summary

import uuid
from typing import List
from models.schemas import TripRequest, ChatRequest, ItineraryResponse, DayConstraint
from data.packages import PACKAGES
from services.poi_service import filter_pois, resolve_config, get_poi_by_ids
from services.scheduler import schedule_day
from services.cost_service import build_cost_summary
from services.llm_service import generate_summary, suggest_budget_fix, parse_user_query


async def generate_trip(req: TripRequest) -> ItineraryResponse:
    """
    Full pipeline:
      1. Resolve package + budget band + overrides → config
      2. For each day: filter POIs → ORS route → schedule slots
      3. Enforce day budgets (LLM fix suggestions if over)
      4. Build cost summary
      5. LLM natural language summary
    """
    config    = resolve_config(req.package_id, req.budget_band, req.overrides.model_dump())
    hotel_lat = req.hotel_lat or 13.0827
    hotel_lon = req.hotel_lon or 80.2707

    user_day_map  = {dc.day_number: dc for dc in req.day_constraints}
    used_pois     = set()
    day_schedules = []

    for day_num in range(1, req.num_days + 1):
        # Use user's day constraint or fall back to package defaults
        dc = user_day_map.get(day_num, DayConstraint(
            day_number=day_num,
            start_time=config["start_time"],
            end_time=config["end_time"],
            pace=config["pace"]
        ))

        # 1. Filter POIs — exclude already-used + day exclusions
        all_excluded = list(used_pois) + dc.excluded_pois
        candidates   = filter_pois(config, city=req.city, excluded=all_excluded)

        # 2. Prepend fixed POIs for this day
        fixed = get_poi_by_ids(dc.fixed_pois, city=req.city)
        pool  = fixed + [p for p in candidates if p["poi_id"] not in dc.fixed_pois]

        # 3. Schedule slots (ORS routing + time assignment)
        day_sched = schedule_day(pool, dc, config["transport_mode"], hotel_lat, hotel_lon)

        # 4. Budget enforcement + LLM fix suggestion
        day_budget = dc.max_budget or config["budget_per_day"]
        if day_sched.cost_breakdown["total"] > day_budget:
            over_by = day_sched.cost_breakdown["total"] - day_budget
            fix     = suggest_budget_fix(over_by, day_sched.model_dump())
            day_sched.cost_breakdown["budget_warning"] = fix

        # 5. Track used POIs to avoid repetition across days
        for slot in day_sched.slots:
            used_pois.add(slot.poi_id)

        day_schedules.append(day_sched)

    # 6. Trip-level cost summary
    cost_summary = build_cost_summary(
        days=day_schedules,
        total_budget=config["budget_per_day"] * req.num_days,
        transport_mode=config["transport_mode"]
    )

    # 7. LLM summary
    llm_summary = generate_summary({
        "package":   config["name"],
        "num_days":  req.num_days,
        "days":      [d.model_dump() for d in day_schedules],
        "cost":      cost_summary.model_dump()
    })

    return ItineraryResponse(
        trip_id=str(uuid.uuid4()),
        city=req.city,
        package_name=config["name"],
        num_days=req.num_days,
        transport_mode=config["transport_mode"],
        days=day_schedules,
        cost_summary=cost_summary,
        llm_summary=llm_summary
    )


async def generate_from_chat(req: ChatRequest) -> ItineraryResponse:
    """
    Chat-driven planning:
      1. LLM parses natural language → structured constraints
      2. Build TripRequest from parsed values
      3. Run same generate_trip pipeline
    """
    parsed = parse_user_query(req.message)

    from models.schemas import PackageOverride
    overrides = PackageOverride(
        transport_mode  = parsed.get("transport_mode"),
        max_entry_fee   = parsed.get("max_entry_fee"),
        total_budget    = parsed.get("total_budget"),
        pace            = parsed.get("pace"),
        start_time      = parsed.get("start_time"),
        end_time        = parsed.get("end_time"),
        wheelchair_only = parsed.get("wheelchair_only")
    )

    trip_req = TripRequest(
        package_id  = parsed.get("package_id") or "pkg-heritage",
        city        = req.city,
        num_days    = parsed.get("num_days", 1),
        budget_band = parsed.get("budget_band", "economy"),
        hotel_lat   = req.hotel_lat,
        hotel_lon   = req.hotel_lon,
        overrides   = overrides
    )

    return await generate_trip(trip_req)
