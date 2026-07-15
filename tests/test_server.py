"""FastAPI server adapter tests."""
from __future__ import annotations

import importlib.util
import json
import time

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None,
    reason="FastAPI optional dependency is not installed",
)


if importlib.util.find_spec("fastapi") is not None:
    from fastapi.testclient import TestClient

    from anviksha.server import create_app


def test_server_health_ready_capabilities_and_metrics() -> None:
    client = TestClient(create_app())

    health = client.get("/healthz")
    assert health.json()["status"] == "ok"
    assert health.headers["x-request-id"]
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["capabilities"] >= 1
    capabilities = client.get("/capabilities").json()
    assert any(cap["id"] == "builtin.calculator" for cap in capabilities)
    assert "anviksha_requests_total" in client.get("/metrics").text


def test_server_execute_offline_goal_with_scope_and_session() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/execute",
        headers={
            "x-request-id": "req-1",
            "x-anviksha-tenant": "tenant-a",
            "x-anviksha-project": "project-a",
            "x-anviksha-session-id": "session-a",
        },
        json={"goal": "2 + 3 * 4", "constraints": {"offline_only": True}},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-1"
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["output"] == 14.0
    assert payload["request_id"] == "req-1"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["project_id"] == "project-a"
    assert payload["session_id"] == "session-a"
    assert "builtin.calculator" in payload["diagnostics"][0]

    session = client.get(
        "/sessions/session-a",
        headers={"x-anviksha-tenant": "tenant-a", "x-anviksha-project": "project-a"},
    ).json()
    assert payload["execution_id"] in session["execution_ids"]


def test_server_execute_returns_cached_response_for_idempotency_key() -> None:
    client = TestClient(create_app())
    headers = {"idempotency-key": "same-request"}
    body = {"goal": "2 + 2"}

    first = client.post("/execute", headers=headers, json=body)
    second = client.post("/execute", headers=headers, json=body)

    assert first.status_code == 200
    assert first.headers["x-anviksha-cache"] == "stored"
    assert second.status_code == 200
    assert second.headers["x-anviksha-cache"] == "hit"
    assert second.json()["cached"] is True
    assert first.json()["execution_id"] == second.json()["execution_id"]


def test_server_execute_returns_validation_error_for_unplannable_goal() -> None:
    client = TestClient(create_app())

    response = client.post("/execute", json={"goal": "write a poem"})

    assert response.status_code == 422
    assert "no capability registered" in response.json()["detail"]


def test_server_streams_ndjson_chunks_with_request_id() -> None:
    client = TestClient(create_app())

    with client.stream(
        "POST",
        "/stream",
        headers={"x-request-id": "stream-1"},
        json={"goal": "2 + 2"},
    ) as response:
        assert response.status_code == 200
        lines = [json.loads(line) for line in response.iter_lines() if line]

    assert lines[0] == {"type": "chunk", "request_id": "stream-1", "output": 4.0}
    assert lines[-1] == {"type": "completed", "request_id": "stream-1"}


def test_server_jobs_and_sessions() -> None:
    client = TestClient(create_app())
    headers = {
        "x-request-id": "job-req",
        "x-anviksha-tenant": "tenant-jobs",
        "x-anviksha-project": "project-jobs",
        "x-anviksha-session-id": "session-jobs",
    }

    accepted = client.post("/jobs", headers=headers, json={"goal": "2 + 5"})

    assert accepted.status_code == 202
    accepted_payload = accepted.json()
    assert accepted_payload["status"] == "queued"
    job_id = accepted_payload["job_id"]

    job = None
    for _ in range(20):
        job = client.get(f"/jobs/{job_id}", headers=headers).json()
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.05)

    assert job is not None
    assert job["status"] == "succeeded"
    assert job["response"]["output"] == 7.0
    session = client.get("/sessions/session-jobs", headers=headers).json()
    assert job_id in session["job_ids"]
    assert job["execution_id"] in session["execution_ids"]


def test_server_optional_api_key_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANVIKSHA_SERVER_API_KEY", "secret")
    client = TestClient(create_app())

    assert client.get("/healthz").status_code == 401
    assert client.get("/healthz", headers={"x-api-key": "secret"}).status_code == 200


def test_server_optional_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANVIKSHA_SERVER_RATE_LIMIT_PER_MINUTE", "1")
    client = TestClient(create_app())

    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 429
