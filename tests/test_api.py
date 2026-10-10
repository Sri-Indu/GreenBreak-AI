import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ALLOWED_ACTIVITIES, ALLOWED_DIFFICULTIES

client = TestClient(app)


class FakeOllamaResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://127.0.0.1:11434/api/tags")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "bad status", request=request, response=response
            )


def install_ollama(monkeypatch, handler):
    """Replace Ollama's HTTP client. Tests never open a real connection."""

    class Client:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return handler("GET", url, None)

        async def post(self, url, json=None):
            return handler("POST", url, json)

    monkeypatch.setattr("backend.ollama_client.httpx.AsyncClient", Client)


def ollama_down(method, url, body):
    raise httpx.ConnectError("connection refused")


def installed_gemma(method, url, body):
    return FakeOllamaResponse(200, {"models": [{"name": "gemma2:2b"}]})


def chat_payload(content):
    return FakeOllamaResponse(200, {"message": {"content": content}})


VALID_MODEL_PLAN = {
    "title": "<b>Creek-edge listening walk</b>",
    "description": "A short outdoor walk along the nearest green edge you can reach on foot.",
    "steps": [
        "Step outside and leave the screen indoors.",
        "Walk toward the nearest trees at an easy pace.",
        "Turn around with enough time to come back.",
    ],
    "tip": "Keep the route close enough to reverse easily.",
    "duration_minutes": 99,
}


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
    assert "gemma2:2b" in response.text


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
def test_generate_uses_templates_when_ollama_is_unavailable(
    duration, activity, difficulty, monkeypatch
):
    install_ollama(monkeypatch, ollama_down)
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
    assert body["source"] == "template-fallback"
    assert "templates" in body["notice"]
    assert body["duration_minutes"] == duration
    assert body["title"]
    assert body["description"]
    assert body["tip"]
    assert 3 <= len(body["steps"]) <= 5


def test_health_reports_ready_local_model(monkeypatch):
    install_ollama(monkeypatch, installed_gemma)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "gemma2:2b"
    assert body["ollama_available"] is True
    assert "gemma2:2b" in body["message"]


def test_health_reports_template_fallback_when_ollama_is_down(monkeypatch):
    install_ollama(monkeypatch, ollama_down)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "gemma2:2b"
    assert body["ollama_available"] is False
    assert "templates" in body["message"]


def test_generate_accepts_a_valid_model_response(monkeypatch):
    sent = []

    def handler(method, url, body):
        if method == "GET":
            return installed_gemma(method, url, body)
        sent.append(body)
        return chat_payload(json.dumps(VALID_MODEL_PLAN))

    install_ollama(monkeypatch, handler)
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": 15,
            "activity_type": "Walking",
            "difficulty": "Gentle",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "model"
    assert "notice" not in body
    assert body["title"] == "<b>Creek-edge listening walk</b>"
    assert body["duration_minutes"] == 15
    assert sent[0]["model"] == "gemma2:2b"
    assert sent[0]["stream"] is False
    assert sent[0]["format"] == "json"
    assert "Walking" in sent[0]["messages"][1]["content"]
    assert "15" in sent[0]["messages"][1]["content"]
    assert response.headers["content-type"].startswith("application/json")


def test_generate_falls_back_when_model_json_is_malformed(monkeypatch):
    def handler(method, url, body):
        if method == "GET":
            return installed_gemma(method, url, body)
        return chat_payload("this is not json")

    install_ollama(monkeypatch, handler)
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": 10,
            "activity_type": "Gardening",
            "difficulty": "Moderate",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "template-fallback"
    assert "not from the local model" in body["notice"]
    assert body["duration_minutes"] == 10
    assert "Garden" in body["title"]


def test_generate_falls_back_when_model_plan_fails_validation(monkeypatch):
    invalid = {
        "title": "Nope",
        "description": "Too short.",
        "steps": ["Only one"],
        "tip": "Short",
    }

    def handler(method, url, body):
        if method == "GET":
            return installed_gemma(method, url, body)
        return chat_payload(json.dumps(invalid))

    install_ollama(monkeypatch, handler)
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": 5,
            "activity_type": "Walking",
            "difficulty": "Gentle",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "template-fallback"
    assert body["title"] == "5-Minute Gentle Neighborhood Walk"
    assert "required format" in body["notice"]


def test_generate_falls_back_when_ollama_connection_fails(monkeypatch):
    install_ollama(monkeypatch, ollama_down)
    response = client.post(
        "/api/generate",
        json={
            "duration_minutes": 30,
            "activity_type": "Birdwatching",
            "difficulty": "Adventurous",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "template-fallback"
    assert "Could not reach the local model" in body["notice"]
    assert "templates" in body["notice"]
    assert body["duration_minutes"] == 30
    assert 3 <= len(body["steps"]) <= 5
