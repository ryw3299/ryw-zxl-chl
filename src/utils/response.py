"""统一响应格式。"""

from src.core.deps import generate_request_id


def success(data=None, msg: str = "操作成功") -> dict:
    return {"code": 200, "msg": msg, "data": data, "requestId": generate_request_id()}


def error(code: int = 400, msg: str = "请求失败") -> dict:
    return {"code": code, "msg": msg, "data": None, "requestId": generate_request_id()}
