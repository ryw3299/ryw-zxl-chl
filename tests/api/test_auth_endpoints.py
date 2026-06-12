"""Auth router contract tests."""

from __future__ import annotations


def test_student_register_login_and_me(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "userId": "student_auth_001",
            "userName": "测试学生",
            "password": "secret123",
            "role": "student",
        },
    )
    assert register_response.status_code == 200
    register_body = register_response.json()
    assert register_body["code"] == 200
    assert register_body["data"]["authToken"]
    assert register_body["data"]["userInfo"]["role"] == "student"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"userId": "student_auth_001", "password": "secret123", "role": "student"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["data"]["authToken"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_body['data']['authToken']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["userInfo"]["userId"] == "student_auth_001"


def test_default_teacher_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"userId": "admin", "password": "123456", "role": "teacher"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["authToken"]
    assert body["data"]["userInfo"]["userId"] == "admin"
    assert body["data"]["userInfo"]["role"] == "teacher"


def test_register_rejects_teacher_account(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"userId": "teacher_auth_001", "password": "secret123", "role": "teacher"},
    )
    assert response.status_code == 400


def test_register_rejects_reserved_teacher_user_id(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"userId": "admin", "password": "secret123", "role": "student"},
    )
    assert response.status_code == 409


def test_login_rejects_role_mismatch(client):
    client.post(
        "/api/v1/auth/register",
        json={"userId": "student_auth_role", "password": "secret123", "role": "student"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"userId": "student_auth_role", "password": "secret123", "role": "teacher"},
    )
    assert response.status_code == 401

    admin_response = client.post(
        "/api/v1/auth/login",
        json={"userId": "admin", "password": "123456", "role": "student"},
    )
    assert admin_response.status_code == 401


def test_register_rejects_duplicate_account(client):
    payload = {
        "userId": "student_auth_dup",
        "password": "secret123",
        "role": "student",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"userId": "student_auth_wrong", "password": "secret123", "role": "student"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"userId": "student_auth_wrong", "password": "badpass", "role": "student"},
    )
    assert response.status_code == 401
