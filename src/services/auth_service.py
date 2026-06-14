"""认证服务：注册、登录、获取当前用户。"""

from sqlalchemy.orm import Session

from src.core.security import create_access_token, hash_password, verify_password
from src.models.user import User


class AuthError(Exception):
    pass


def register_user(
    db: Session, *, username: str, password: str, email: str = ""
) -> dict:
    if not username or len(username) < 2:
        raise AuthError("用户名至少 2 个字符")
    if len(password) < 6:
        raise AuthError("密码至少 6 个字符")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise AuthError("用户名已被注册")

    user = User(
        username=username,
        email=email or None,
        password_hash=hash_password(password),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(sub=str(user.id), role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_info": {"id": user.id, "username": user.username, "role": user.role},
    }


def login_user(db: Session, *, username: str, password: str) -> dict:
    if not username or not password:
        raise AuthError("请输入用户名和密码")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")

    token = create_access_token(sub=str(user.id), role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_info": {"id": user.id, "username": user.username, "role": user.role},
    }


def get_user_info(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "role": user.role,
        "created_at": str(user.created_at),
    }


def seed_admin(db: Session) -> None:
    """创建默认管理员账号。"""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            email="admin@zhixue.com",
        )
        db.add(admin)
        db.commit()
