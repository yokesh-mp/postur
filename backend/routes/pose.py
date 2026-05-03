import json
from fastapi import APIRouter, HTTPException
from config import POSES_FILE_PATH
from providers import get_provider

router = APIRouter()

# Load poses once at startup
with open(POSES_FILE_PATH, "r") as f:
    POSES_DATA = json.load(f)


def get_all_poses(category: str = None) -> list:
    poses = POSES_DATA.get("poses", [])
    if category:
        poses = [p for p in poses if p["category"] == category]
    return poses


def get_next_pose(category: str, current_id: str) -> dict:
    poses = get_all_poses(category)
    if not poses:
        return None

    # Find current pose index
    current_index = next(
        (i for i, p in enumerate(poses) if p["id"] == current_id), -1
    )

    # Return next pose, loop back to start if at end
    next_index = (current_index + 1) % len(poses)
    return poses[next_index]


@router.get("/poses")
async def list_poses(category: str = None):
    """Return full pose library, optionally filtered by category."""
    poses = get_all_poses(category)
    if not poses:
        raise HTTPException(status_code=404, detail="No poses found")
    return {
        "total": len(poses),
        "category": category or "all",
        "poses": poses
    }


@router.get("/next-pose")
async def next_pose(category: str = "casual", current_id: str = ""):
    """Return next pose with AI-generated placement instructions."""
    pose = get_next_pose(category, current_id)
    if not pose:
        raise HTTPException(status_code=404, detail="No poses found")

    provider = await get_provider()
    scene = {"category": category, "setting": "indoor", "lighting": "good"}
    placement = await provider.get_pose_placement(pose["id"], scene)

    # Use defaults if LLM returns empty
    if not placement:
        placement = {
            "anchor_zone": "MC",
            "mirror": False,
            "rotation_deg": 0,
            "scale_hint": "full_body",
            "tip": pose.get("default_tip", "Match the pose")
        }

    return {
        "pose": pose,
        "placement": placement
    }