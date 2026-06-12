"""Platform router (/api/v1/platform/*) — 2 endpoints.

Covered endpoints:
  POST /platform/syncCourse — pull a course from the external platform
  POST /platform/syncUser   — pull a user (student/teacher) from the platform
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# /platform/syncCourse
# ---------------------------------------------------------------------


def test_sync_course_success(client):
    r = client.post(
        "/api/v1/platform/syncCourse",
        json={
            "platformId": "plat001",
            "courseInfo": {
                "courseId": "plat_cou001",
                "courseName": "材料力学",
                "schoolId": "sch_test",
                "credit": 3.0,
                "period": 48,
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    # Response must include the sync timestamp added by the router.
    assert "syncTime" in body["data"]


def test_sync_course_idempotent_on_same_id(client):
    """Calling syncCourse twice with the same courseId should not 500."""
    payload = {
        "platformId": "plat001",
        "courseInfo": {"courseId": "plat_idem", "courseName": "幂等课程"},
    }
    r1 = client.post("/api/v1/platform/syncCourse", json=payload)
    r2 = client.post("/api/v1/platform/syncCourse", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_sync_course_rejects_missing_required(client):
    r = client.post("/api/v1/platform/syncCourse", json={"platformId": "x"})
    assert r.status_code == 422


# ---------------------------------------------------------------------
# /platform/syncUser
# ---------------------------------------------------------------------


def test_sync_user_student(client):
    r = client.post(
        "/api/v1/platform/syncUser",
        json={
            "platformId": "plat001",
            "userInfo": {
                "userId": "plat_stu001",
                "userName": "李四",
                "role": "student",
                "schoolId": "sch_test",
                "relatedCourseIds": ["plat_cou001"],
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["code"] == 200


def test_sync_user_teacher(client):
    r = client.post(
        "/api/v1/platform/syncUser",
        json={
            "platformId": "plat001",
            "userInfo": {
                "userId": "plat_tea001",
                "userName": "张教授",
                "role": "teacher",
                "schoolId": "sch_test",
            },
        },
    )
    assert r.status_code == 200


def test_sync_user_idempotent(client):
    payload = {
        "platformId": "plat001",
        "userInfo": {"userId": "plat_idem_user", "userName": "幂等用户", "role": "student"},
    }
    r1 = client.post("/api/v1/platform/syncUser", json=payload)
    r2 = client.post("/api/v1/platform/syncUser", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_sync_user_rejects_missing_required(client):
    r = client.post("/api/v1/platform/syncUser", json={"platformId": "x"})
    assert r.status_code == 422
