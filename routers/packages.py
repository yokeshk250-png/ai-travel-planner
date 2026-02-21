from fastapi import APIRouter
from data.packages import PACKAGES

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("/")
def list_packages():
    """Return all available tour packages with defaults."""
    return [
        {
            "package_id":     pid,
            "name":           pkg["name"],
            "icon":           pkg["icon"],
            "theme":          pkg["theme"],
            "budget_per_day": pkg["defaults"]["budget_per_day"],
            "transport":      pkg["defaults"]["transport_mode"],
            "pace":           pkg["defaults"]["pace"],
            "hours":          pkg["defaults"]["num_hours"],
            "activities":     pkg["activities"],
            "categories":     pkg["category_primary"]
        }
        for pid, pkg in PACKAGES.items()
    ]


@router.get("/{package_id}")
def get_package(package_id: str):
    """Get details for a specific package."""
    if package_id not in PACKAGES:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return PACKAGES[package_id]
