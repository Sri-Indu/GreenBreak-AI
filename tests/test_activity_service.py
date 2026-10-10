from backend.activity_service import PLANS, create_activity
from backend.ollama_client import pick_installed_model
from backend.schemas import ALLOWED_ACTIVITIES, ALLOWED_DIFFICULTIES, GenerateRequest


def test_every_choice_has_a_template():
    assert len(PLANS) == len(ALLOWED_ACTIVITIES) * len(ALLOWED_DIFFICULTIES)
    for activity in ALLOWED_ACTIVITIES:
        for difficulty in ALLOWED_DIFFICULTIES:
            assert (activity, difficulty) in PLANS


def test_create_activity_uses_selected_options():
    request = GenerateRequest(
        duration_minutes=10,
        activity_type="Birdwatching",
        difficulty="Gentle",
    )
    activity = create_activity(request)
    assert activity.duration_minutes == 10
    assert "10" in activity.title
    assert "bird" in activity.title.lower()
    assert len(activity.steps) >= 3
    assert activity.tip


def test_different_activities_get_different_plans():
    walking = create_activity(
        GenerateRequest(
            duration_minutes=15,
            activity_type="Walking",
            difficulty="Moderate",
        )
    )
    gardening = create_activity(
        GenerateRequest(
            duration_minutes=15,
            activity_type="Gardening",
            difficulty="Moderate",
        )
    )
    assert walking.title != gardening.title
    assert walking.steps != gardening.steps


def test_duration_changes_the_instructions():
    short = create_activity(
        GenerateRequest(
            duration_minutes=5,
            activity_type="Nature Exploration",
            difficulty="Adventurous",
        )
    )
    long = create_activity(
        GenerateRequest(
            duration_minutes=30,
            activity_type="Nature Exploration",
            difficulty="Adventurous",
        )
    )
    assert short.duration_minutes == 5
    assert long.duration_minutes == 30
    assert short.steps != long.steps


def test_pick_installed_model_resolves_gemma_tag():
    assert pick_installed_model("gemma2", ["gemma2:2b"]) == "gemma2:2b"
    assert pick_installed_model("gemma2:2b", ["gemma2:2b"]) == "gemma2:2b"
    assert pick_installed_model("gemma2", ["llama3"]) is None
