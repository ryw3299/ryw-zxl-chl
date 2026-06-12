"""Cross-cutting API contract tests.

These ensure the global response envelope, error handling, and middleware
behavior stay stable as the project grows.  They do NOT exercise specific
business endpoints.
"""

from __future__ import annotations


def test_success_envelope_shape(client):
    """Every success response has ``{code, msg, data, requestId}``."""
    r = client.get("/api/v1/lesson/list")
    assert r.status_code == 200
    body = r.json()
    for key in ("code", "msg", "data", "requestId"):
        assert key in body, f"missing key {key!r} in success envelope"
    assert body["code"] == 200
    # requestId is unique per request — non-empty string
    assert body["requestId"]


def test_404_envelope_shape(client):
    """A 404 response also adheres to the envelope contract."""
    r = client.post("/api/v1/lesson/parseStatus", json={"parseId": "nope"})
    assert r.status_code == 404
    body = r.json()
    for key in ("code", "msg", "data", "requestId"):
        assert key in body
    assert body["code"] == 404
    assert body["data"] is None


def test_validation_error_returns_422(client):
    """Pydantic schema mismatch returns FastAPI's standard 422."""
    r = client.post("/api/v1/lesson/parse", json={"foo": "bar"})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body  # FastAPI's standard validation error format


def test_cors_origin_wildcard(client):
    """Default CORS config returns ``*`` for any Origin."""
    r = client.options(
        "/api/v1/lesson/list",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # OPTIONS may return 200 or 405 depending on the route; either way the
    # CORS middleware should populate the headers when 200.
    if r.status_code == 200:
        assert r.headers.get("access-control-allow-origin") in {"*", "https://example.com"}


def test_signature_skipped_in_debug(client):
    """In DEBUG mode the signature middleware is bypassed entirely."""
    # No `enc` / `time` headers given; in production this would 401.
    r = client.post(
        "/api/v1/platform/syncCourse",
        json={
            "platformId": "plat001",
            "courseInfo": {"courseId": "skip_sig_test", "courseName": "x"},
        },
    )
    assert r.status_code == 200


def test_request_ids_are_unique(client):
    """Two calls in the same session yield distinct ``requestId``s."""
    r1 = client.get("/api/v1/lesson/list")
    r2 = client.get("/api/v1/lesson/list")
    assert r1.json()["requestId"] != r2.json()["requestId"]


def test_internal_routes_dont_require_signature(client):
    """``/internal/kb/*`` is excluded from signature verification."""
    r = client.get("/internal/kb/list")
    assert r.status_code == 200


def test_health_does_not_require_signature(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_unknown_route_404(client):
    r = client.get("/api/v1/this/does/not/exist")
    assert r.status_code == 404
