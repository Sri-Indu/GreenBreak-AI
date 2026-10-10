import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ALLOWED_ACTIVITIES, ALLOWED_DIFFICULTIES

client = TestClient(app)


def test_homepage_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Less scrolling. More living." in response.text
    assert "Generate My Break Plan" in response.text
    assert "10 minutes" in response.text
    assert "Gentle" in response.text
    assert "Exploring nearby nature" in response.text
    assert 'href="#planner"' in response.text
    assert 'href="#mission"' in response.text
    assert 'href="#progress"' in response.text
    assert 'href="#about"' in response.text
    assert response.text.index('id="planner"') < response.text.index('id="activity"')
    assert response.text.index('id="activity"') < response.text.index('id="progress"')
    assert "Plan your outdoor break" in response.text
    assert "Complete Mission" in response.text
    assert "Start another mission" in response.text
    assert 'href="#progress"' in response.text
    assert "Mark Break Complete" in response.text
    assert "Missions completed" in response.text
    assert "Breaks completed" in response.text
    assert "Nothing completed yet." in response.text


def test_generate_rejects_invalid_input():
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": 45,
            "activity_type": "Walking",
            "difficulty": "Gentle",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("duration", [5, 10, 15, 30])
@pytest.mark.parametrize("activity", ALLOWED_ACTIVITIES)
@pytest.mark.parametrize("difficulty", ALLOWED_DIFFICULTIES)
def test_generate_returns_a_local_template_plan(duration, activity, difficulty):
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": duration,
            "activity_type": activity,
            "difficulty": difficulty,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["duration_minutes"] == duration
    assert body["title"]
    assert body["description"]
    assert body["tip"]
    assert 3 <= len(body["steps"]) <= 5


def test_health_reports_local_planner():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "local-templates"
    assert "templates" in body["message"]
