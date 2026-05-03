from fastapi import APIRouter
from pydantic import BaseModel
from providers import get_provider

router = APIRouter()

# Rule-based instant responses for common mismatches
RULE_BASED_RESPONSES = {
    "left_elbow":    "Adjust your left elbow",
    "right_elbow":   "Adjust your right elbow",
    "left_shoulder": "Lower your left shoulder",
    "right_shoulder":"Lower your right shoulder",
    "left_knee":     "Bend your left knee more",
    "right_knee":    "Bend your right knee more",
    "left_wrist":    "Reposition your left wrist",
    "right_wrist":   "Reposition your right wrist",
    "left_hip":      "Shift your left hip",
    "right_hip":     "Shift your right hip",
    "left_ankle":    "Adjust your left foot",
    "right_ankle":   "Adjust your right foot",
}


class Mismatch(BaseModel):
    landmark: str
    angle_diff_deg: float


class CoachRequest(BaseModel):
    mismatches: list[Mismatch]
    pose_id: str = ""
    use_llm: bool = True


@router.post("/coach-instruction")
async def coach_instruction(request: CoachRequest):
    """
    Accept mismatch data and return one coaching instruction.
    Uses rule engine for instant response.
    Uses LLM for better natural language when use_llm=True.
    """
    if not request.mismatches:
        return {"instruction": "Looking good! Hold the pose.", "source": "rule"}

    # Sort mismatches by biggest angle difference first
    sorted_mismatches = sorted(
        request.mismatches,
        key=lambda m: m.angle_diff_deg,
        reverse=True
    )

    # Rule-based instant response
    worst = sorted_mismatches[0]
    rule_instruction = RULE_BASED_RESPONSES.get(
        worst.landmark,
        "Adjust your position slightly"
    )

    # Return rule-based immediately if LLM not requested
    if not request.use_llm:
        return {"instruction": rule_instruction, "source": "rule"}

    # Use LLM for better natural language
    try:
        provider = await get_provider()
        mismatches_dict = [m.dict() for m in sorted_mismatches[:3]]
        instruction = await provider.get_coaching_instruction(mismatches_dict)
        return {"instruction": instruction, "source": "llm"}
    except Exception:
        # Fall back to rule-based if LLM fails
        return {"instruction": rule_instruction, "source": "rule"}