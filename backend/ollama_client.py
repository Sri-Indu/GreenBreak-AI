"""Talk to a local open-weight model through Ollama's HTTP API."""

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from backend.schemas import ActivityResponse, GenerateRequest

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma2:2b"
TAGS_TIMEOUT_SECONDS = 5.0
GENERATE_TIMEOUT = httpx.Timeout(90.0, connect=5.0)


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


def build_break_prompt(request: GenerateRequest) -> str:
    """Ask the local model for one structured outdoor break."""
    return (
        "Create one personalized outdoor break plan.\n"
        f"Duration: {request.duration_minutes} minutes.\n"
        f"Activity: {request.activity_type}.\n"
        f"Adventure level: {request.difficulty}.\n"
        "Return a JSON object with exactly these keys: title, description, steps, tip.\n"
        "title is a short plain-text name.\n"
        "description is one or two plain-text sentences.\n"
        "steps is an array of 3 to 5 plain-text instructions a person can do outdoors near home.\n"
        "tip is one short plain-text suggestion.\n"
        "Do not use HTML, markdown, or code fences.\n"
        "Keep the plan safe, realistic, and specific to the duration, activity, and adventure level."
    )


async def list_model_names() -> list[str]:
    url = f"{get_ollama_url()}/api/tags"
    async with httpx.AsyncClient(timeout=TAGS_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
    return [item.get("name", "") for item in response.json().get("models", [])]


async def resolve_model_name() -> str:
    requested = get_model_name()
    try:
        names = await list_model_names()
    except httpx.RequestError as exc:
        raise OllamaError(
            "Could not reach the local model through Ollama.",
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
    """Return whether Ollama is reachable and the selected model is installed."""
    requested = get_model_name()
    try:
        names = await list_model_names()
    except httpx.RequestError:
        return {
            "available": False,
            "model_found": False,
            "model": requested,
            "message": "Ollama is not running on this computer.",
        }
    except httpx.HTTPStatusError:
        return {
            "available": False,
            "model_found": False,
            "model": requested,
            "message": "Ollama responded with an unexpected error.",
        }

    resolved = pick_installed_model(requested, names)
    if resolved:
        message = f"Ollama is ready with {resolved}."
    else:
        message = f"Ollama is running, but the {requested} model is not installed."
    return {
        "available": True,
        "model_found": bool(resolved),
        "model": resolved or requested,
        "message": message,
    }


async def generate_json(prompt: str) -> dict[str, Any]:
    """Ask the local model for a JSON object. Never returns a fake example."""
    model = await resolve_model_name()
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are GreenBreak AI, a local outdoor-break coach. "
                    "Reply with one JSON object only. Do not include markdown or HTML."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.8},
    }

    try:
        async with httpx.AsyncClient(timeout=GENERATE_TIMEOUT) as client:
            response = await client.post(
                f"{get_ollama_url()}/api/chat",
                json=payload,
            )
    except httpx.RequestError as exc:
        raise OllamaError(
            "Could not reach the local model through Ollama.",
            hint=_connection_hint(),
        ) from exc

    if response.status_code == 404:
        raise OllamaError(
            f"The local model '{model}' was not found.",
            hint=f"Run `ollama pull {model}` and try again.",
        )
    if response.status_code >= 400:
        raise OllamaError(
            "Ollama could not generate a break plan right now.",
            hint="Check that Ollama is running and the model finished loading.",
        )

    try:
        data = response.json()
        content = data["message"]["content"]
        parsed = json.loads(content)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OllamaError(
            "The local model returned a response that was not valid JSON.",
            hint="Try generating again. If this continues, restart Ollama.",
        ) from exc

    if not isinstance(parsed, dict):
        raise OllamaError(
            "The local model returned JSON that was not a break plan.",
            hint="Try generating again with the same options.",
        )
    return parsed


async def generate_activity_plan(request: GenerateRequest) -> ActivityResponse:
    """Generate one break plan and accept it only if it matches ActivityResponse."""
    parsed = await generate_json(build_break_prompt(request))
    payload = dict(parsed)
    payload.pop("notice", None)
    payload["duration_minutes"] = request.duration_minutes
    payload["source"] = "model"
    payload["notice"] = None
    try:
        return ActivityResponse.model_validate(payload)
    except ValidationError as exc:
        raise OllamaError(
            "The local model returned a break plan that did not match the required format.",
            hint="A built-in template will be used instead.",
        ) from exc
