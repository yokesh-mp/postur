import httpx
from .base import AIProvider
from .ollama import OllamaProvider
from .gemini import GeminiProvider
from config import OLLAMA_BASE_URL


async def get_provider() -> AIProvider:
    """
    Auto-detect which AI provider to use.
    Tries Ollama first (free, local).
    Falls back to Gemini if Ollama is unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                print("✅ Ollama reachable — using local provider")
                return OllamaProvider()
    except Exception:
        pass

    print("☁️  Ollama unreachable — falling back to Gemini")
    return GeminiProvider()