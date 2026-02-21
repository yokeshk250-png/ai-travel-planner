# LLM Service — Perplexity API integration
# Two roles:
#   1. parse_user_query  — extract structured constraints from natural language
#   2. generate_summary  — produce human-friendly trip summary
#   3. suggest_budget_fix — recommend cost reductions when over budget

import json
from config import PERPLEXITY_API_KEY

try:
    from openai import OpenAI
    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    ) if PERPLEXITY_API_KEY else None
except ImportError:
    client = None

MODEL = "llama-3.1-sonar-small-128k-online"

PARSE_SYSTEM = """
Extract travel requirements from user text.
Return ONLY valid JSON with exactly these fields:
{
  "package_id": "pkg-heritage|pkg-family|pkg-budget|pkg-spiritual|pkg-beach|pkg-shopping|null",
  "num_days": integer,
  "budget_band": "budget|economy|premium",
  "transport_mode": "bus|metro|auto|cab|self_drive|null",
  "total_budget": float_or_null,
  "max_entry_fee": float_or_null,
  "pace": "relaxed|normal|packed|null",
  "start_time": "HH:MM or null",
  "end_time": "HH:MM or null",
  "wheelchair_only": true|false|null
}
Return no extra text, only the JSON object.
"""

SUMMARY_SYSTEM = """
You are a friendly Chennai travel guide.
Given a structured itinerary with days, slots, and costs,
write 3-4 engaging sentences.
Mention: key highlights per day, total cost in INR, one practical travel tip.
Be warm and concise.
"""


def parse_user_query(text: str) -> dict:
    """Use LLM to extract trip constraints from natural language."""
    if not client:
        return {}
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PARSE_SYSTEM},
                {"role": "user",   "content": text}
            ],
            temperature=0
        )
        raw = r.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        return {}


def generate_summary(plan: dict) -> str:
    """Generate a human-friendly summary of the finalized itinerary."""
    if not client:
        return "Your itinerary has been generated successfully!"
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user",   "content": json.dumps(plan, default=str)}
            ],
            temperature=0.7
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return "Your trip is ready — enjoy exploring Chennai!"


def suggest_budget_fix(over_by: float, day_info: dict) -> str:
    """Ask LLM to suggest 2 specific ways to reduce cost for an over-budget day."""
    if not client:
        return ""
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a cost-conscious Chennai travel advisor."},
                {"role": "user",   "content":
                    f"The day is over budget by ₹{over_by:.0f}. "
                    f"Schedule: {json.dumps(day_info, default=str)}. "
                    "Suggest 2 specific changes to reduce cost."
                }
            ],
            temperature=0.5
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return ""
