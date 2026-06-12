import uuid


def generate_request_id() -> str:
    return f"req{uuid.uuid4().hex[:16]}"


def generate_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"
