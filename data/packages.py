# Pre-defined tour packages for Chennai
# Each package defines theme, category filters, tag filters,
# activity hints, and sensible defaults.
# These are merged with user overrides + budget bands at runtime.

PACKAGES = {
    "pkg-heritage": {
        "name": "Heritage & History",
        "icon": "🏛️",
        "theme": "heritage",
        "category_primary": ["heritage", "temple", "museum"],
        "tags": ["fort", "colonial", "dravidian", "8th_century", "british"],
        "activities": ["museum_visit", "history_tour", "photography", "architecture"],
        "defaults": {
            "max_entry_fee":  150,
            "min_rating":     4.3,
            "transport_mode": "auto",
            "num_hours":      8,
            "budget_per_day": 1200,
            "pace":           "normal",
            "start_time":     "09:00",
            "end_time":       "20:00"
        }
    },
    "pkg-family": {
        "name": "Family Fun Day",
        "icon": "👨‍👩‍👧",
        "theme": "family",
        "category_primary": ["beach", "park", "museum", "attraction"],
        "tags": ["family", "zoo", "amusement", "wildlife", "science"],
        "activities": ["wildlife", "water_rides", "planetarium_shows", "safari"],
        "defaults": {
            "max_entry_fee":  500,
            "min_rating":     4.2,
            "transport_mode": "cab",
            "num_hours":      8,
            "budget_per_day": 2000,
            "pace":           "normal",
            "start_time":     "09:00",
            "end_time":       "19:00"
        }
    },
    "pkg-budget": {
        "name": "Budget Explorer",
        "icon": "💰",
        "theme": "budget",
        "category_primary": ["beach", "temple", "attraction", "heritage"],
        "tags": ["free", "beach", "urban"],
        "activities": ["jogging", "prayer", "photography", "architecture"],
        "defaults": {
            "max_entry_fee":  0,
            "min_rating":     4.0,
            "transport_mode": "bus",
            "num_hours":      6,
            "budget_per_day": 400,
            "pace":           "relaxed",
            "start_time":     "08:00",
            "end_time":       "18:00"
        }
    },
    "pkg-spiritual": {
        "name": "Spiritual Trail",
        "icon": "🛕",
        "theme": "spiritual",
        "category_primary": ["temple"],
        "tags": ["hindu", "shiva", "vishnu", "divya_desam", "heritage"],
        "activities": ["prayer", "utsavam", "architecture", "heritage"],
        "defaults": {
            "max_entry_fee":  50,
            "min_rating":     4.4,
            "transport_mode": "auto",
            "num_hours":      6,
            "budget_per_day": 700,
            "pace":           "relaxed",
            "start_time":     "06:00",
            "end_time":       "21:00"
        }
    },
    "pkg-beach": {
        "name": "Coastal Escape",
        "icon": "🏖️",
        "theme": "beach",
        "category_primary": ["beach", "attraction"],
        "tags": ["beach", "sunset", "relaxation", "ecr", "drive_in"],
        "activities": ["relaxation", "food_stalls", "surfing", "movies"],
        "defaults": {
            "max_entry_fee":  300,
            "min_rating":     4.2,
            "transport_mode": "self_drive",
            "num_hours":      6,
            "budget_per_day": 900,
            "pace":           "relaxed",
            "start_time":     "15:00",
            "end_time":       "23:00"
        }
    },
    "pkg-shopping": {
        "name": "Shop & Dine",
        "icon": "🛍️",
        "theme": "shopping",
        "category_primary": ["attraction"],
        "tags": ["shopping", "mall", "retail", "jewellery", "street_food"],
        "activities": ["shopping", "street_food", "dining", "bargaining"],
        "defaults": {
            "max_entry_fee":  0,
            "min_rating":     4.0,
            "transport_mode": "metro",
            "num_hours":      5,
            "budget_per_day": 1500,
            "pace":           "packed",
            "start_time":     "11:00",
            "end_time":       "22:00"
        }
    }
}
