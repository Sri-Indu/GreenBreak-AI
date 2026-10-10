"""Request and response models for GreenBreak AI."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_DURATIONS = (5, 10, 15, 30)
ALLOWED_ACTIVITIES = (
    "Walking",
    "Gardening",
    "Birdwatching",
    "Nature Exploration",
)
ALLOWED_DIFFICULTIES = ("Gentle", "Moderate", "Adventurous")

DurationMinutes = Literal[5, 10, 15, 30]
ActivityType = Literal["Walking", "Gardening", "Birdwatching", "Nature Exploration"]
DifficultyLevel = Literal["Gentle", "Moderate", "Adventurous"]


class GenerateRequest(BaseModel):
    duration_minutes: DurationMinutes
    activity_type: ActivityType
    difficulty: DifficultyLevel


class ActivityResponse(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=20, max_length=800)
    steps: list[str] = Field(min_length=3, max_length=5)
    duration_minutes: DurationMinutes
    tip: str = Field(min_length=8, max_length=280)

    @field_validator("title", "description", "tip")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Text cannot be empty.")
        return cleaned

    @field_validator("steps")
    @classmethod
    def clean_steps(cls, steps: list[str]) -> list[str]:
        cleaned = [" ".join(step.split()) for step in steps if step and step.strip()]
        if not 3 <= len(cleaned) <= 5:
            raise ValueError("An activity must include 3 to 5 steps.")
        for step in cleaned:
            if len(step) < 8:
                raise ValueError("Each step must be at least 8 characters.")
        return cleaned


class ErrorResponse(BaseModel):
    error: str
    hint: str | None = None


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama_available: bool
    message: str
