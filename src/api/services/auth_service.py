"""Local username/password authentication service."""

import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from src.api.models.tables import User

_PBKDF2_ITERATIONS = 210_000
_LOCAL_PLATFORM_ID = "local"
_DEFAULT_TEACHER_USER_ID = "admin"
_DEFAULT_TEACHER_PASSWORD = "123456"
_DEFAULT_TEACHER_NAME = "教师管理员"


class AuthConflictError(ValueError):
    """Raised when a local account already exists."""


class AuthInvalidError(ValueError):
    """Raised when credentials, roles, or tokens are invalid."""


def _normalize_user_id(value: str) -> str:
    return str(value or "").strip()


def _normalize_role(value: str) -> str:
    role = str(value or "student").strip().lower()
    return role if role in {"student", "teacher"} else "student"


def _normalize_expected_role(value: str | None) -> str | None:
    role = str(value or "").strip().lower()
    return role if role in {"student", "teacher"} else None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not password or not stored_hash:
        return False

    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (TypeError, ValueError):
        return False


def _public_user_payload(user: User) -> dict:
    return {
        "userId": user.user_id,
        "userName": user.user_name or user.user_id,
        "role": user.role or "student",
        "schoolId": user.school_id or "",
    }


def _issue_token(user: User) -> str:
    token = secrets.token_urlsafe(64)
    user.auth_token = token
    return token


def _is_default_teacher_user_id(user_id: str) -> bool:
    return user_id.lower() == _DEFAULT_TEACHER_USER_ID


def _ensure_default_teacher_user(db: Session) -> User:
    user = db.query(User).filter(User.user_id == _DEFAULT_TEACHER_USER_ID).first()
    if not user:
        user = User(
            user_id=_DEFAULT_TEACHER_USER_ID,
            platform_user_id=_DEFAULT_TEACHER_USER_ID,
            platform_id=_LOCAL_PLATFORM_ID,
            user_name=_DEFAULT_TEACHER_NAME,
            role="teacher",
            school_id=None,
            password_hash=hash_password(_DEFAULT_TEACHER_PASSWORD),
            related_course_ids="[]",
        )
        db.add(user)
        db.flush()
        return user

    user.platform_user_id = user.platform_user_id or _DEFAULT_TEACHER_USER_ID
    user.platform_id = _LOCAL_PLATFORM_ID
    user.user_name = user.user_name or _DEFAULT_TEACHER_NAME
    user.role = "teacher"
    if not verify_password(_DEFAULT_TEACHER_PASSWORD, user.password_hash):
        user.password_hash = hash_password(_DEFAULT_TEACHER_PASSWORD)
    db.flush()
    return user


def register_user(
    db: Session,
    *,
    user_id: str,
    password: str,
    role: str = "student",
    user_name: str = "",
    school_id: str = "",
) -> dict:
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id or len(str(password or "")) < 6:
        raise AuthInvalidError("账号和密码不符合要求")

    if _normalize_role(role) == "teacher":
        raise AuthInvalidError("教师账号不支持注册，请联系管理员获取教师账号")

    if _is_default_teacher_user_id(normalized_user_id):
        raise AuthConflictError("该账号已被系统保留，学生注册请更换账号")

    existing = db.query(User).filter(User.user_id == normalized_user_id).first()
    if existing:
        raise AuthConflictError("账号已存在")

    user = User(
        user_id=normalized_user_id,
        platform_user_id=normalized_user_id,
        platform_id=_LOCAL_PLATFORM_ID,
        user_name=str(user_name or normalized_user_id).strip() or normalized_user_id,
        role="student",
        school_id=str(school_id or "").strip() or None,
        password_hash=hash_password(password),
        related_course_ids="[]",
    )
    token = _issue_token(user)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "authToken": token,
        "userInfo": _public_user_payload(user),
    }


def login_user(db: Session, *, user_id: str, password: str, role: str | None = None) -> dict:
    normalized_user_id = _normalize_user_id(user_id)
    if _is_default_teacher_user_id(normalized_user_id):
        user = _ensure_default_teacher_user(db)
    else:
        user = db.query(User).filter(User.user_id == normalized_user_id).first()

    if not user or not verify_password(password, user.password_hash):
        raise AuthInvalidError("账号或密码错误")

    expected_role = _normalize_expected_role(role)
    if expected_role and (user.role or "student") != expected_role:
        raise AuthInvalidError("账号身份与登录入口不匹配")

    token = _issue_token(user)
    db.commit()
    db.refresh(user)
    return {
        "authToken": token,
        "userInfo": _public_user_payload(user),
    }


def get_user_by_token(db: Session, token: str) -> dict:
    normalized_token = str(token or "").strip()
    if not normalized_token:
        raise AuthInvalidError("未登录")

    user = db.query(User).filter(User.auth_token == normalized_token).first()
    if not user:
        raise AuthInvalidError("登录状态已失效")

    return {
        "authToken": normalized_token,
        "userInfo": _public_user_payload(user),
    }
