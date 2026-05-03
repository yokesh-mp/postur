import json
import re
import google.generativeai as genai
from .base import AIProvider
from config import GEMINI_API_KEY


class GeminiProvider(AIProvider):

    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.vision_model = genai.GenerativeModel("gemini-1.5-flash")
        self.chat_model = genai.GenerativeModel("gemini-1.5-flash")

    async def analyze_scene(self, image_base64: str) -> dict:
        import base64
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

        image_data = base64.b64decode(image_base64)
        response = self.vision_model.generate_content([
            {"mime_type": "image/jpeg", "data": image_data},
            prompt
        ])
        return self._parse_json(response.text)

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

        response = self.chat_model.generate_content(prompt)
        return self._parse_json(response.text)

    async def get_coaching_instruction(self, mismatches: list) -> str:
        mismatch_text = "\n".join(
            [f"- {m['landmark']}: {m['angle_diff_deg']}° off target"
             for m in mismatches]
        )
        prompt = f"""The user is matching a pose. These body parts are misaligned:
{mismatch_text}

Generate ONE short friendly correction instruction, maximum 10 words.
Return only the instruction text, nothing else."""

        response = self.chat_model.generate_content(prompt)
        return response.text.strip()

    def _parse_json(self, text: str) -> dict:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}