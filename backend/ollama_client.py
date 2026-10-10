"""Talk to a local Gemma model through Ollama."""

import json
import os
from typing import Any

import httpx

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma2"


class OllamaError(Exception):
    """Raised when the local Ollama model cannot generate an activity."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


def get_ollama_url() -> str:
    return os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")


def get_model_name() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)


def pick_installed_model(requested: str, names: list[str]) -> str | None:
    """Match an installed Ollama tag, including names like gemma2:2b."""
    if requested in names:
        return requested

    tagged = [name for name in names if name.startswith(f"{requested}:")]
    if tagged:
        return sorted(tagged)[0]

    family = requested.split(":", 1)[0]
    family_matches = [
        name for name in names if name == family or name.startswith(f"{family}:")
    ]
    if family_matches:
        return sorted(family_matches)[0]

    gemma_matches = [name for name in names if name.startswith("gemma")]
    if requested.startswith("gemma") and gemma_matches:
        return sorted(gemma_matches)[0]
    return None


def _connection_hint() -> str:
    model = get_model_name()
    return (
        "Install Ollama from https://ollama.com, start it, then run "
        f"`ollama pull {model}` and `ollama serve`."
    )


async def list_model_names() -> list[str]:
    url = f"{get_ollama_url()}/api/tags"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    return [item.get("name", "") for item in response.json().get("models", [])]


async def resolve_model_name() -> str:
    requested = get_model_name()
    try:
        names = await list_model_names()
    except httpx.RequestError as exc:
        raise OllamaError(
            "Could not reach the local Gemma model through Ollama.",
            hint=_connection_hint(),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaError(
            "Ollama responded with an unexpected error.",
            hint="Restart Ollama and try again.",
        ) from exc

    resolved = pick_installed_model(requested, names)
    if not resolved:
        raise OllamaError(
            f"The local model '{requested}' was not found.",
            hint=f"Run `ollama pull {requested}` and try again.",
        )
    return resolved


async def check_ollama() -> dict[str, Any]:
    """Return whether Ollama is reachable and a matching Gemma model exists."""
    try:
        names = await list_model_names()
    except httpx.RequestError:
        return {
            "available": False,
            "model_found": False,
            "message": "Ollama is not running on this computer.",
        }
    except httpx.HTTPStatusError:
        return {
            "available": False,
            "model_found": False,
            "message": "Ollama responded with an unexpected error.",
        }

    resolved = pick_installed_model(get_model_name(), names)
    if resolved:
        message = f"Ollama is ready with {resolved}."
    else:
        message = (
            f"Ollama is running, but the {get_model_name()} model is not installed."
        )
    return {
        "available": True,
        "model_found": bool(resolved),
        "message": message,
    }


async def generate_json(prompt: str) -> dict[str, Any]:
    """Ask Gemma for a JSON activity. Never returns a fake example."""
    model = await resolve_model_name()
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are GreenBreak AI, a friendly outdoor-break coach. "
                    "Reply with JSON only. Do not include markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.8},
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{get_ollama_url()}/api/chat",
                json=payload,
            )
    except httpx.RequestError as exc:
        raise OllamaError(
            "Could not reach the local Gemma model through Ollama.",
            hint=_connection_hint(),
        ) from exc

    if response.status_code == 404:
        raise OllamaError(
            f"The local model '{model}' was not found.",
            hint=f"Run `ollama pull {model}` and try again.",
        )
    if response.status_code >= 400:
        raise OllamaError(
            "Ollama could not generate an activity right now.",
            hint="Check that Ollama is running and the Gemma model finished loading.",
        )

    try:
        data = response.json()
        content = data["message"]["content"]
        parsed = json.loads(content)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OllamaError(
            "Gemma returned a response that was not valid JSON.",
            hint="Try generating again. If this continues, restart Ollama.",
        ) from exc

    if not isinstance(parsed, dict):
        raise OllamaError(
            "Gemma returned JSON that was not an activity object.",
            hint="Try generating again with the same options.",
        )
    return parsed
