from abc import ABC, abstractmethod


class AIProvider(ABC):

    @abstractmethod
    async def analyze_scene(self, image_base64: str) -> dict:
        """
        Analyze a camera frame and return scene details.
        Returns: category, lighting, setting, subject_count, confidence
        """
        pass

    @abstractmethod
    async def get_pose_placement(self, pose_id: str, scene: dict) -> dict:
        """
        Given a pose and scene context, return placement instructions.
        Returns: anchor_zone, mirror, rotation_deg, scale_hint, tip
        """
        pass

    @abstractmethod
    async def get_coaching_instruction(self, mismatches: list) -> str:
        """
        Given a list of body part mismatches, return one coaching instruction.
        Returns: single instruction string (max 10 words)
        """
        pass