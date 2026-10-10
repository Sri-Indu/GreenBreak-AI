"""GreenBreak AI FastAPI app."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.activity_service import create_activity
from backend.schemas import (
    ActivityResponse,
    ErrorResponse,
    GenerateRequest,
    HealthResponse,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="GreenBreak AI",
    description="Generate outdoor breaks from local activity templates.",
    version="1.0.0",
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model="local-templates",
        ollama_available=False,
        message="Break plans are created on this computer from outdoor activity templates.",
    )


@app.post(
    "/api/generate",
    response_model=ActivityResponse,
    responses={422: {"model": ErrorResponse}},
)
async def generate_activity(request: GenerateRequest) -> ActivityResponse:
    return create_activity(request)


@app.get("/")
async def homepage() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html; charset=utf-8")


@app.get("/styles.css")
async def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css; charset=utf-8")


@app.get("/app.js")
async def script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="text/javascript; charset=utf-8")
