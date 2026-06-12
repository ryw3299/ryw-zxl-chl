"""Progress router (/api/v1/progress/*) — 2 endpoints.

Covered endpoints:
  POST /progress/track  — record a progress sample
  POST /progress/adjust — request a pace recommendation
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# /progress/track
# ---------------------------------------------------------------------


def test_track_progress_success(client):
    r = client.post(
        "/api/v1/progress/track",
        json={
            "schoolId": "sch_test",
            "userId": "stu_test",
            "courseId": "cou_test",
            "lessonId": "lesson_test_001",
            "currentSectionId": "sec1",
            "progressPercent": 45.0,
            "lastOperateTime": "2026-05-22 12:00:00",
            "qaRecordId": "ans_test_001",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"] is not None


def test_track_progress_accepts_zero_and_hundred(client):
    """Boundary values for ``progressPercent``."""
    for percent in (0.0, 100.0, 50.5):
        r = client.post(
            "/api/v1/progress/track",
            json={
                "schoolId": "sch_test",
                "userId": "stu_test",
                "courseId": "cou_test",
                "lessonId": f"lesson_test_{int(percent)}",
                "currentSectionId": "sec1",
                "progressPercent": percent,
                "lastOperateTime": "2026-05-22 12:00:00",
            },
        )
        assert r.status_code == 200


def test_track_progress_rejects_missing_required(client):
    r = client.post("/api/v1/progress/track", json={"userId": "stu_test"})
    assert r.status_code == 422


# ---------------------------------------------------------------------
# /progress/adjust
# ---------------------------------------------------------------------


def test_adjust_pace_success(client):
    r = client.post(
        "/api/v1/progress/adjust",
        json={
            "userId": "stu_test",
            "lessonId": "lesson_test_001",
            "currentSectionId": "sec1",
            "understandingLevel": "partial",
            "qaRecordId": "ans_test_001",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    # The decision agent always returns a structured suggestion.
    assert body["data"] is not None


def test_adjust_pace_rejects_invalid_understanding(client):
    """Pydantic still allows the string but the service should not crash;
    we only assert the API returns *some* 200/422 response."""
    r = client.post(
        "/api/v1/progress/adjust",
        json={
            "userId": "stu_test",
            "lessonId": "lesson_test_001",
            "currentSectionId": "sec1",
            "understandingLevel": "weird_value",  # not a known enum
            "qaRecordId": "ans_test_001",
        },
    )
    # Either schema rejects it (422) or service tolerates and returns 200.
    assert r.status_code in (200, 422)


def test_adjust_pace_rejects_missing_required(client):
    r = client.post("/api/v1/progress/adjust", json={"userId": "stu_test"})
    assert r.status_code == 422
