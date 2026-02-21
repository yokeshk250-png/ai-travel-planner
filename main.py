from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import packages, planner

app = FastAPI(
    title="AI Travel Planner — Chennai",
    description="Constraint-based, LLM-assisted, ORS-optimized travel planner backed by Firebase Firestore",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(packages.router)
app.include_router(planner.router)

@app.get("/")
def root():
    return {
        "status":  "ok",
        "message": "AI Travel Planner API is running",
        "docs":    "/docs"
    }
