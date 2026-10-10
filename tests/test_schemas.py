import pytest
from pydantic import ValidationError

from backend.schemas import ActivityResponse, GenerateRequest


def test_generate_request_accepts_allowed_values():
    request = GenerateRequest(
        duration_minutes=15,
        activity_type="Birdwatching",
        difficulty="Gentle",
    )
    assert request.duration_minutes == 15


@pytest.mark.parametrize(
    "payload",
    [
        {"duration_minutes": 20, "activity_type": "Walking", "difficulty": "Gentle"},
        {
            "duration_minutes": 5,
            "activity_type": "Running",
            "difficulty": "Gentle",
        },
        {
            "duration_minutes": 5,
            "activity_type": "Walking",
            "difficulty": "Hard",
        },
    ],
)
def test_generate_request_rejects_invalid_values(payload):
    with pytest.raises(ValidationError):
        GenerateRequest(**payload)


def test_activity_response_requires_three_to_five_steps():
    with pytest.raises(ValidationError):
        ActivityResponse(
            title="Park pause",
            description="Step outside and notice the air, light, and nearby plants.",
            steps=["Look up", "Breathe"],
            duration_minutes=5,
            tip="Stay with one small spot.",
        )


def test_activity_response_cleans_whitespace():
    activity = ActivityResponse(
        title="  Quiet  garden  reset  ",
        description="  Leave the screen.  Feel the soil.  Notice one living thing.  ",
        steps=[
            "  Step outside and feel the air  ",
            "Water one plant slowly",
            "Look closely at a leaf",
        ],
        duration_minutes=10,
        tip="  One pot is enough for a short reset.  ",
    )
    assert activity.title == "Quiet garden reset"
    assert activity.tip == "One pot is enough for a short reset."
    assert activity.duration_minutes == 10
    assert len(activity.steps) == 3
