# 🗺️ AI Travel Planner — Chennai

A complete AI-driven travel planner using:
- **LLM (Perplexity API)** for natural language planning
- **OpenRouteService** for real route optimization
- **Firebase Firestore** for POI data (`cities/{city}/places/{poi_id}`)
- **FastAPI** backend with packages, day constraints, scheduling, and cost estimation

## 📁 Project Structure
```
ai_travel_planner/
├── data/
│   └── packages.py          # Pre-defined tour packages
├── models/
│   └── schemas.py           # Pydantic models
├── services/
│   ├── poi_service.py       # Firestore POI querying + filtering
│   ├── ors_service.py       # OpenRouteService route optimization
│   ├── scheduler.py         # Day + time slot scheduling
│   ├── cost_service.py      # Budget + cost estimation
│   ├── llm_service.py       # Perplexity LLM integration
│   └── planner.py           # Main orchestrator
├── routers/
│   ├── packages.py          # GET /packages
│   └── planner.py           # POST /plan/generate, /plan/chat
├── main.py                  # FastAPI entry point
├── config.py                # Settings + Firebase init
├── firestore.indexes.json   # Composite index definitions
├── requirements.txt
└── .env.example
```

## 🚀 Quick Start
```bash
git clone https://github.com/yokeshk250-png/ai-travel-planner
cd ai-travel-planner
pip install -r requirements.txt
cp .env.example .env   # Add your API keys
# Add serviceAccountKey.json from Firebase Console
uvicorn main:app --reload
```

## 🔑 API Keys Needed
| Key | Source |
|-----|--------|
| `ORS_API_KEY` | https://openrouteservice.org (free tier) |
| `PERPLEXITY_API_KEY` | https://www.perplexity.ai/api |
| `serviceAccountKey.json` | Firebase Console → Project Settings → Service Accounts |

## 📡 Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/packages` | List all tour packages |
| `POST` | `/plan/generate` | Generate full itinerary from structured request |
| `POST` | `/plan/chat` | Natural language → full itinerary |

## 📦 Example Request
```json
POST /plan/generate
{
  "package_id": "pkg-family",
  "num_days": 2,
  "budget_band": "economy",
  "hotel_lat": 13.0827,
  "hotel_lon": 80.2707,
  "overrides": { "transport_mode": "cab" },
  "day_constraints": [
    {
      "day_number": 1,
      "start_time": "09:00",
      "end_time": "18:00",
      "pace": "normal",
      "fixed_pois": ["tn-chn-001"]
    },
    {
      "day_number": 2,
      "start_time": "10:00",
      "end_time": "20:00",
      "pace": "relaxed",
      "max_budget": 800
    }
  ]
}
```

## 🗃️ Firestore Structure
```
cities/
└── Chennai/
     ├── total_places: 57
     └── places/
           ├── tn-chn-001  (Marina Beach)
           ├── tn-chn-002  (Fort St. George)
           └── ...
```

## ⚙️ How It Works
```
Request (UI or Chat)
       ↓
LLM Service        → parse natural language → constraints
       ↓
POI Service        → Firestore query (category + fee + rating + tags)
       ↓
ORS Service        → travel time matrix + greedy route optimization
       ↓
Scheduler          → assign time slots per day (pace + opening hours)
       ↓
Cost Service       → entry fees + transport + extras per day
       ↓
LLM Service        → natural language summary
       ↓
ItineraryResponse  → days + slots + cost breakdown + summary
```
