from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Serve test UI at http://localhost:8000/ui/
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


@app.get("/")
def root():
    return {
        "status":  "ok",
        "message": "AI Travel Planner API is running",
        "docs":    "/docs",
        "ui":      "/ui"
    }
