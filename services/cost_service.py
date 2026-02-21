# Cost Service — trip-level budget aggregation
# Sums day totals, checks against budget band,
# flags over-budget days, and returns a structured CostSummary.

from models.schemas import DaySchedule, CostSummary
from typing import List


def build_cost_summary(
    days: List[DaySchedule],
    total_budget: float,
    transport_mode: str
) -> CostSummary:
    grand_total = sum(d.cost_breakdown["total"] for d in days)
    warnings    = []

    for day in days:
        cap = day.cost_breakdown.get("max_budget")
        if cap and day.cost_breakdown["total"] > cap:
            over = day.cost_breakdown["total"] - cap
            warnings.append(f"Day {day.day_number} exceeds day cap by ₹{over:.0f}")

    if grand_total > total_budget:
        over = grand_total - total_budget
        warnings.append(f"Total ₹{grand_total:.0f} exceeds budget ₹{total_budget:.0f} by ₹{over:.0f}")

    return CostSummary(
        grand_total=round(grand_total, 2),
        total_budget=round(total_budget, 2),
        within_budget=grand_total <= total_budget,
        budget_remaining=round(total_budget - grand_total, 2),
        per_day_avg=round(grand_total / max(len(days), 1), 2),
        transport_mode=transport_mode,
        warnings=warnings
    )
