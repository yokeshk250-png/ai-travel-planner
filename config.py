import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

ORS_API_KEY        = os.getenv("ORS_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# ── Firebase initialization (runs once) ─────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ── Budget bands (INR/day) ───────────────────────────────────────
BUDGET_BANDS = {
    "budget": {
        "daily_budget":    800,
        "max_entry_fee":   100,
        "default_transport": "bus",
        "pace":            "relaxed",
        "stops_per_day":   (2, 3)
    },
    "economy": {
        "daily_budget":    1500,
        "max_entry_fee":   300,
        "default_transport": "auto",
        "pace":            "normal",
        "stops_per_day":   (3, 5)
    },
    "premium": {
        "daily_budget":    3500,
        "max_entry_fee":   1000,
        "default_transport": "cab",
        "pace":            "packed",
        "stops_per_day":   (5, 7)
    }
}

# ── Transport cost per km (INR) ──────────────────────────────────
TRANSPORT_RATES = {
    "bus":        {"base": 5,  "per_km": 1.5},
    "metro":      {"base": 10, "per_km": 2.5},
    "auto":       {"base": 30, "per_km": 18},
    "cab":        {"base": 50, "per_km": 22},
    "self_drive": {"base": 0,  "per_km": 6}
}

# ── Average speed (km/h) per mode ───────────────────────────────
TRANSPORT_SPEED = {
    "bus": 15, "metro": 35, "auto": 20, "cab": 25, "self_drive": 30
}

# ── Activity extra costs (INR) ───────────────────────────────────
ACTIVITY_EXTRAS = {
    "lion_safari":       300,
    "water_rides":       400,
    "elephant_ride":     200,
    "planetarium_shows": 40,
    "horseback_riding":  150,
    "drive_in":          200,
    "bowling":           250,
    "battery_vehicle":   50
}
