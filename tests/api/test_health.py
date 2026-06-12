"""Health and root-level endpoints."""

from __future__ import annotations


def test_health_returns_ok(client):
    """``/health`` returns ``{status: ok}`` plus a paths snapshot."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "paths" in body
    # Critical paths must be exposed for ops debugging.
    for key in ("uploads_dir", "audio_dir", "render_dir", "session_db", "history_db"):
        assert key in body["paths"]


def test_root_serves_panel_or_redirect(client):
    """``/`` returns 200 with HTML (the test panel) or JSON landing info."""
    r = client.get("/")
    assert r.status_code == 200


def test_panel_static_mount(client):
    """``/panel/`` should serve the test panel ``index.html``."""
    r = client.get("/panel/")
    # Either 200 with HTML (mounted) or 404 if test_panel folder is missing.
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert "html" in r.headers.get("content-type", "").lower()
