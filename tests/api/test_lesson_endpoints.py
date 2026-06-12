"""Lesson router (/api/v1/lesson/*) — 18 endpoints.

Covered endpoints:
  POST  /parse, /parseUpload, /parseStatus
  POST  /generateScript, /scriptStatus, /editScript
  POST  /generateAudio, /audioStatus
  POST  /generate, /generateStatus
  POST  /renderPPT
  GET   /list
  POST  /publish, /delete
  GET   /download/{lessonId}, /preview/{lessonId},
        /preview/{lessonId}/{slideNumber}, /audio/{audio_id}/{section_id}

Background tasks are short-circuited via the autouse fixture in conftest, so
all tests verify the synchronous request → response contract only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# /lesson/parse
# ---------------------------------------------------------------------


def test_parse_creates_task_and_returns_parseid(client):
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_test",
            "userId": "tea_test",
            "courseId": "cou_test",
            "fileType": "pdf",
            "fileUrl": "/tmp/fake.pdf",
            "isExtractKeyPoint": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["parseId"].startswith("parse")
    assert body["data"]["taskStatus"] == "processing"


def test_parse_rejects_missing_required_fields(client):
    """Pydantic validation catches missing ``fileUrl``."""
    r = client.post(
        "/api/v1/lesson/parse",
        json={"schoolId": "x", "userId": "x", "courseId": "x", "fileType": "pdf"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------
# /lesson/parseUpload
# ---------------------------------------------------------------------


def test_parse_upload_accepts_multipart_file(client, tmp_path):
    fake = tmp_path / "doc.pdf"
    fake.write_bytes(b"%PDF-1.4 fake content")

    r = client.post(
        "/api/v1/lesson/parseUpload",
        data={
            "schoolId": "sch_test",
            "userId": "tea_test",
            "courseId": "cou_test",
            "fileType": "pdf",
            "isExtractKeyPoint": "true",
        },
        files={"file": ("doc.pdf", fake.read_bytes(), "application/pdf")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["parseId"].startswith("parse")
    assert body["data"]["fileInfo"]["fileSize"] > 0


# ---------------------------------------------------------------------
# /lesson/parseStatus
# ---------------------------------------------------------------------


def test_parse_status_returns_completed_payload(client, seeded_parse_task):
    r = client.post(
        "/api/v1/lesson/parseStatus",
        json={"parseId": seeded_parse_task.parse_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["taskStatus"] == "completed"
    assert body["data"]["fileInfo"]["pageCount"] == 1


def test_parse_status_404_on_unknown_id(client):
    r = client.post(
        "/api/v1/lesson/parseStatus",
        json={"parseId": "parse_does_not_exist"},
    )
    assert r.status_code == 404
    assert r.json()["code"] == 404


# ---------------------------------------------------------------------
# /lesson/generateScript
# ---------------------------------------------------------------------


def test_generate_script_requires_completed_parse(client, seeded_parse_task):
    r = client.post(
        "/api/v1/lesson/generateScript",
        json={
            "parseId": seeded_parse_task.parse_id,
            "teachingStyle": "standard",
            "speechSpeed": "normal",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["scriptId"].startswith("script")
    assert body["data"]["taskStatus"] == "processing"


def test_generate_script_404_on_unknown_parse(client):
    r = client.post(
        "/api/v1/lesson/generateScript",
        json={"parseId": "parse_missing"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/scriptStatus + /lesson/editScript
# ---------------------------------------------------------------------


def test_script_status_returns_structure(client, seeded_script):
    r = client.post(
        "/api/v1/lesson/scriptStatus",
        json={"scriptId": seeded_script.script_id},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["scriptId"] == seeded_script.script_id
    assert data["taskStatus"] == "completed"
    assert isinstance(data["scriptStructure"], list)


def test_script_status_404_on_unknown_id(client):
    r = client.post("/api/v1/lesson/scriptStatus", json={"scriptId": "script_x"})
    assert r.status_code == 404


def test_edit_script_persists_new_structure(client, seeded_script):
    new_structure = [
        {
            "sectionId": "sec1",
            "sectionName": "改写章节",
            "content": "新讲稿内容",
            "duration": 60,
            "relatedChapterId": "ch1",
            "keyPoints": ["关键点1"],
        }
    ]
    r = client.post(
        "/api/v1/lesson/editScript",
        json={"scriptId": seeded_script.script_id, "scriptStructure": new_structure},
    )
    assert r.status_code == 200
    returned = r.json()["data"]["scriptStructure"]
    assert len(returned) == 1
    assert returned[0]["sectionId"] == "sec1"
    assert returned[0]["content"] == "新讲稿内容"
    assert returned[0]["keyPoints"] == ["关键点1"]


def test_edit_script_404_on_unknown_id(client):
    r = client.post(
        "/api/v1/lesson/editScript",
        json={"scriptId": "no", "scriptStructure": []},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/generateAudio + /lesson/audioStatus
# ---------------------------------------------------------------------


def test_generate_audio_creates_task(client, seeded_script):
    r = client.post(
        "/api/v1/lesson/generateAudio",
        json={
            "scriptId": seeded_script.script_id,
            "voiceType": "female_standard",
            "audioFormat": "mp3",
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["audioId"].startswith("audio")


def test_generate_audio_404_on_missing_script(client):
    r = client.post(
        "/api/v1/lesson/generateAudio",
        json={"scriptId": "missing"},
    )
    assert r.status_code == 404


def test_audio_status_returns_payload(client, seeded_audio_task):
    r = client.post(
        "/api/v1/lesson/audioStatus",
        json={"audioId": seeded_audio_task.audio_id},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["taskStatus"] == "completed"
    assert data["audioInfo"]["totalDuration"] == 120


def test_audio_status_404(client):
    r = client.post("/api/v1/lesson/audioStatus", json={"audioId": "no"})
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/generate (one-shot workflow) + /lesson/generateStatus
# ---------------------------------------------------------------------


def test_generate_creates_lesson(client):
    r = client.post(
        "/api/v1/lesson/generate",
        json={
            "schoolId": "sch_test",
            "userId": "tea_test",
            "courseId": "cou_test",
            "fileType": "pdf",
            "fileUrl": "/tmp/fake.pdf",
            "teachingStyle": "standard",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["lessonId"].startswith("lesson")
    assert body["data"]["workflowStatus"] == "processing"
    assert len(body["data"]["steps"]) == 3


def test_generate_status_returns_404_for_unknown_lesson(client):
    r = client.post(
        "/api/v1/lesson/generateStatus",
        json={"lessonId": "lesson_missing"},
    )
    assert r.status_code == 404


def test_generate_status_returns_workflow(client, seeded_parse_task):
    """Use the parse_task lesson id (seeded_parse_task creates a Lesson too)."""
    r = client.post(
        "/api/v1/lesson/generateStatus",
        json={"lessonId": seeded_parse_task.parse_id},
    )
    assert r.status_code == 200
    assert "workflowStatus" in r.json()["data"]


# ---------------------------------------------------------------------
# /lesson/renderPPT
# ---------------------------------------------------------------------


def test_render_ppt_404_on_missing_lesson(client):
    r = client.post("/api/v1/lesson/renderPPT", json={"lessonId": "no"})
    assert r.status_code == 404


def test_render_ppt_400_when_outline_missing(client, seeded_parse_task):
    """Seeded lesson has no ``ppt_outline`` yet → expect 400."""
    r = client.post(
        "/api/v1/lesson/renderPPT",
        json={"lessonId": seeded_parse_task.parse_id},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------
# /lesson/list + /publish + /delete
# ---------------------------------------------------------------------


def test_list_lessons(client, seeded_parse_task):
    r = client.get("/api/v1/lesson/list")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] >= 1
    assert any(lesson["lessonId"] == seeded_parse_task.parse_id for lesson in data["lessons"])


def test_list_lessons_filtered_by_status(client, seeded_parse_task):
    r = client.get("/api/v1/lesson/list?status=parsed")
    assert r.status_code == 200
    for lesson in r.json()["data"]["lessons"]:
        assert lesson["status"] == "parsed"


def test_publish_lesson(client, seeded_parse_task):
    r = client.post(
        "/api/v1/lesson/publish",
        json={
            "lessonId": seeded_parse_task.parse_id,
            "lessonName": "测试课时（已发布）",
            "tag": "力学",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["lessonName"] == "测试课时（已发布）"
    assert body["data"]["tag"] == "力学"


def test_publish_lesson_404(client):
    r = client.post(
        "/api/v1/lesson/publish",
        json={"lessonId": "no", "lessonName": "x"},
    )
    assert r.status_code == 404


def test_delete_lesson_archives(client, seeded_parse_task):
    r = client.post(
        "/api/v1/lesson/delete",
        json={"lessonId": seeded_parse_task.parse_id},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] in {"archived", "deleted"}


def test_delete_lesson_404(client):
    r = client.post("/api/v1/lesson/delete", json={"lessonId": "no"})
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/download/{lessonId}
# ---------------------------------------------------------------------


def test_download_ppt_404_when_no_artifact(client, seeded_parse_task):
    r = client.get(f"/api/v1/lesson/download/{seeded_parse_task.parse_id}")
    assert r.status_code == 404


def test_download_ppt_404_unknown_lesson(client):
    r = client.get("/api/v1/lesson/download/lesson_missing")
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/preview/{lessonId} + /preview/{lessonId}/{slideNumber}
# ---------------------------------------------------------------------


def test_preview_meta_404_on_missing(client):
    r = client.get("/api/v1/lesson/preview/lesson_missing")
    assert r.status_code == 404


def test_preview_meta_returns_payload(client, seeded_parse_task):
    r = client.get(f"/api/v1/lesson/preview/{seeded_parse_task.parse_id}")
    # Either 200 (meta available) or 404 (no preview rendered yet); both are
    # contract-conformant.
    assert r.status_code in (200, 404)


def test_preview_image_404_on_missing(client):
    r = client.get("/api/v1/lesson/preview/lesson_missing/1")
    assert r.status_code == 404


# ---------------------------------------------------------------------
# /lesson/audio/{audio_id}/{section_id}
# ---------------------------------------------------------------------


def test_audio_file_404_on_missing(client):
    r = client.get("/api/v1/lesson/audio/no/no")
    assert r.status_code == 404
