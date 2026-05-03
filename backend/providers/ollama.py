import httpx
import json
import re
from .base import AIProvider
from config import OLLAMA_BASE_URL, OLLAMA_VISION_MODEL, OLLAMA_CHAT_MODEL


class OllamaProvider(AIProvider):

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.vision_model = OLLAMA_VISION_MODEL
        self.chat_model = OLLAMA_CHAT_MODEL

    async def analyze_scene(self, image_base64: str) -> dict:
        prompt = """Analyze this scene. Detect lighting quality, background type,
number of people, and whether it is indoor or outdoor.

Return ONLY this JSON, nothing else:
{
  "category": "fitness or portrait or casual or group",
  "lighting": "good or low or harsh",
  "setting": "indoor or outdoor",
  "subject_count": 1,
  "confidence": 0.9
}"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                }
            )
            result = response.json()
            return self._parse_json(result.get("response", "{}"))

    async def get_pose_placement(self, pose_id: str, scene: dict) -> dict:
        prompt = f"""Scene: {scene.get('setting', 'indoor')}, {scene.get('lighting', 'good')} lighting, 
{scene.get('subject_count', 1)} person, center of frame.
Pose category: {scene.get('category', 'casual')}.
Selected pose: {pose_id}.

Return ONLY this JSON, nothing else:
{{
  "anchor_zone": "MC",
  "mirror": false,
  "rotation_deg": 0,
  "scale_hint": "full_body",
  "tip": "one short pose tip for the user"
}}"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            result = response.json()
            return self._parse_json(result.get("response", "{}"))

    async def get_coaching_instruction(self, mismatches: list) -> str:
        mismatch_text = "\n".join(
            [f"- {m['landmark']}: {m['angle_diff_deg']}° off target"
             for m in mismatches]
        )
        prompt = f"""The user is matching a pose. These body parts are misaligned:
{mismatch_text}

Generate ONE short friendly correction instruction, maximum 10 words.
Return only the instruction text, nothing else."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            result = response.json()
            return result.get("response", "Adjust your position slightly").strip()

    def _parse_json(self, text: str) -> dict:
        try:
            # Extract JSON from response even if there's extra text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}