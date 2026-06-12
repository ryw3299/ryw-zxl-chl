"""QA router (/api/v1/qa/*) — 4 endpoints.

Covered endpoints:
  POST /qa/interact, /qa/gamePayload
  POST /qa/voiceToText, /qa/voiceToTextUpload

External calls (LLM agent, ASR provider) are mocked via fixtures so each
test only exercises the request/response contract.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# /qa/interact
# ---------------------------------------------------------------------


def test_qa_interact_success_with_mocked_agent(client, mock_run_qa_interact):
    r = client.post(
        "/api/v1/qa/interact",
        json={
            "schoolId": "sch_test",
            "userId": "stu_test",
            "courseId": "cou_test",
            "lessonId": "lesson_test",
            "sessionId": "sess_test",
            "questionType": "text",
            "questionContent": "什么是惯性？",
            "currentSectionId": "sec1",
            "currentPage": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    data = body["data"]
    assert data["answerId"].startswith("ans")
    assert data["answerContent"]
    assert data["understandingLevel"] in {"none", "partial", "full"}
    # The new field added during refactor must surface in the response.
    assert "recommendedNarrationLevel" in data


def test_qa_interact_rejects_missing_question(client):
    r = client.post(
        "/api/v1/qa/interact",
        json={
            "schoolId": "sch_test",
            "userId": "stu_test",
            "courseId": "cou_test",
            "lessonId": "lesson_test",
            "sessionId": "sess_test",
            # questionContent missing
        },
    )
    assert r.status_code == 422


def test_qa_interact_creates_session_idempotently(client, db, mock_run_qa_interact):
    """Same sessionId hits ``get_or_create_session`` twice without dup-insert."""
    payload = {
        "schoolId": "sch_test",
        "userId": "stu_test",
        "courseId": "cou_test",
        "lessonId": "lesson_test",
        "sessionId": "sess_idempotent_001",
        "questionContent": "测试",
    }
    r1 = client.post("/api/v1/qa/interact", json=payload)
    r2 = client.post("/api/v1/qa/interact", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200

    from src.api.models.tables import QASession

    rows = db.query(QASession).filter(QASession.session_id == "sess_idempotent_001").all()
    assert len(rows) == 1


# ---------------------------------------------------------------------
# /qa/gamePayload
# ---------------------------------------------------------------------


def test_game_payload_returns_stub_when_lesson_missing(client):
    """Even with an unknown lesson the endpoint must still return 200."""
    r = client.post(
        "/api/v1/qa/gamePayload",
        json={
            "schoolId": "sch_test",
            "userId": "stu_test",
            "courseId": "cou_test",
            "lessonId": "lesson_missing",
            "sessionId": "sess_g1",
            "question": "什么是惯性？",
        },
    )
    assert r.status_code == 200
    body = r.json()
    # Schema must always be filled (router has fallback).
    assert body["data"]["gameType"] in {"multiple_choice", ""}
    assert "choices" in body["data"]


def test_game_payload_with_seeded_lesson(client, seeded_parse_task):
    r = client.post(
        "/api/v1/qa/gamePayload",
        json={
            "schoolId": "sch_test",
            "userId": "stu_test",
            "courseId": "cou_test",
            "lessonId": seeded_parse_task.parse_id,
            "sessionId": "sess_g2",
            "question": "什么是惯性？",
            "currentSectionId": "sec1",
            "currentPage": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["gameType"]
    assert isinstance(body["choices"], list)


def test_game_payload_rejects_missing_required(client):
    r = client.post("/api/v1/qa/gamePayload", json={"sessionId": "x"})
    assert r.status_code == 422


# ---------------------------------------------------------------------
# /qa/voiceToText
# ---------------------------------------------------------------------


def test_voice_to_text_returns_text(client, mock_voice_to_text):
    r = client.post(
        "/api/v1/qa/voiceToText",
        json={"voiceUrl": "/tmp/fake.wav", "language": "zh-CN"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["text"] == "这是一个测试语音转文字"
    assert data["confidence"] > 0
    assert "timestamp" in data


def test_voice_to_text_rejects_missing_url(client):
    r = client.post("/api/v1/qa/voiceToText", json={"language": "zh-CN"})
    assert r.status_code == 422


# ---------------------------------------------------------------------
# /qa/voiceToTextUpload
# ---------------------------------------------------------------------


def test_voice_to_text_upload_accepts_file(client, mock_voice_to_text, tmp_path):
    fake_wav = tmp_path / "voice.wav"
    fake_wav.write_bytes(b"RIFF....WAVEfmt ")  # nominal WAV header

    r = client.post(
        "/api/v1/qa/voiceToTextUpload",
        data={"language": "zh-CN"},
        files={"file": ("voice.wav", fake_wav.read_bytes(), "audio/wav")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["text"]
    assert data["confidence"] > 0
