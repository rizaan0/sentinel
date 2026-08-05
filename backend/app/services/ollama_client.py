"""
Thin HTTP client for a local Ollama instance. No external API keys - the
AI Investigation Assistant runs entirely on infrastructure we control.
"""
import httpx

from app.core.config import settings


class OllamaUnavailableError(Exception):
    pass


def chat(system_prompt: str, user_prompt: str) -> str:
    """Calls Ollama's /api/chat (non-streaming) and returns the assistant's reply text."""
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    try:
        response = httpx.post(url, json=payload, timeout=settings.OLLAMA_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(f"Could not reach Ollama at {url}: {exc}") from exc

    data = response.json()
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaUnavailableError(f"Unexpected Ollama response shape: {data}") from exc
