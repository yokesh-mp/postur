from fastapi import APIRouter
from pydantic import BaseModel
from providers import get_provider

router = APIRouter()


class SceneRequest(BaseModel):
    image: str  # base64 encoded JPEG
    current_category: str = "casual"


@router.post("/analyze-scene")
async def analyze_scene(request: SceneRequest):
    """
    Analyze a camera frame and return scene details + suggested pose category.
    """
    provider = await get_provider()

    scene = await provider.analyze_scene(request.image)

    # Use defaults if LLM returns empty or incomplete
    if not scene:
        scene = {
            "category": request.current_category,
            "lighting": "good",
            "setting": "indoor",
            "subject_count": 1,
            "confidence": 0.5
        }

    return scene