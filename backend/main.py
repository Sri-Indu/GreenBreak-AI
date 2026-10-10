"""GreenBreak AI FastAPI app."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.activity_service import create_activity
from backend.ollama_client import (
    OllamaError,
    check_ollama,
    generate_activity_plan,
    get_model_name,
)
from backend.schemas import (
    ActivityResponse,
    ErrorResponse,
    GenerateRequest,
    HealthResponse,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="GreenBreak AI",
    description="Generate outdoor breaks with a local Ollama model. Templates are the fallback.",
    version="1.0.0",
)


def template_fallback(request: GenerateRequest, reason: str) -> ActivityResponse:
    """Return a predefined plan and say plainly that the model did not write it."""
    notice = (
        f"{reason} This plan came from the built-in templates, not from the local model."
    )
    return create_activity(request).model_copy(
        update={"source": "template-fallback", "notice": notice}
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    report = await check_ollama()
    model_name = report.get("model") or get_model_name()
    if report["available"] and report["model_found"]:
        return HealthResponse(
            status="ok",
            model=model_name,
            ollama_available=True,
            message=report["message"],
        )
    return HealthResponse(
        status="ok",
        model=model_name,
        ollama_available=False,
        message=(
            f"{report['message']} Break plans will use built-in templates "
            "until the local model is available."
        ),
    )


@app.post(
    "/api/generate",
    response_model=ActivityResponse,
    response_model_exclude_none=True,
    responses={422: {"model": ErrorResponse}},
)
async def generate_activity(request: GenerateRequest) -> ActivityResponse:
    try:
        return await generate_activity_plan(request)
    except OllamaError as exc:
        return template_fallback(request, exc.message)


@app.get("/")
async def homepage() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html; charset=utf-8")


@app.get("/styles.css")
async def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css; charset=utf-8")


@app.get("/app.js")
async def script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="text/javascript; charset=utf-8")
