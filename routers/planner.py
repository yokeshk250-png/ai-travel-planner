from fastapi import APIRouter, HTTPException
from models.schemas import TripRequest, ChatRequest
from services.planner import generate_trip, generate_from_chat
from data.packages import PACKAGES

router = APIRouter(prefix="/plan", tags=["planner"])


@router.post("/generate")
async def generate(req: TripRequest):
    """
    Generate a full multi-day itinerary from a structured request.
    Includes ORS route optimization, time slots, and cost breakdown.
    """
    if req.package_id not in PACKAGES:
        raise HTTPException(status_code=404, detail=f"Package '{req.package_id}' not found")
    return await generate_trip(req)


@router.post("/chat")
async def chat_plan(req: ChatRequest):
    """
    Generate an itinerary from natural language.
    LLM parses the message into constraints, then runs the same pipeline.
    """
    return await generate_from_chat(req)
