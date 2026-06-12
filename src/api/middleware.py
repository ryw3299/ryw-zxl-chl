"""MD5 signature verification middleware per the 超星 API specification.

Signature algorithm:
    enc = MD5(sorted_params_concat + staticKey + time)

where sorted_params_concat concatenates all non-empty request params
(excluding `enc` and `time`) sorted by key in ASCII order.
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi import Request
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.api.config import settings


def _compute_signature(params: dict, static_key: str, time_str: str) -> str:
    sorted_keys = sorted(k for k in params if k not in ("enc", "time") and params[k])
    concat = "".join(f"{k}{params[k]}" for k in sorted_keys)
    raw = concat + static_key + time_str
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def verify_signature(params: dict, static_key: str, timeout_seconds: int = 300) -> bool:
    """Validate the MD5 signature header per the 超星 API spec.

    Returns ``True`` only when the signature, timestamp, and salted MD5
    hash match.  Returns ``False`` for any error so the dispatcher can
    short-circuit with an HTTP 401.
    """
    enc = params.get("enc")
    time_str = params.get("time")
    if not enc or not time_str:
        return False

    try:
        request_time = datetime.strptime(time_str, "%Y-%m-%d%H:%M:%S")
    except ValueError:
        try:
            request_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False

    if abs((datetime.now() - request_time).total_seconds()) > timeout_seconds:
        return False

    expected = _compute_signature(params, static_key, time_str)
    return enc.upper() == expected


def _build_receive(body: bytes):
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


async def _extract_request_params(request: Request, body: bytes) -> dict[str, Any]:
    if request.method not in ("POST", "PUT", "PATCH"):
        return dict(request.query_params)

    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form_request = Request(request.scope, _build_receive(body))
        form = await form_request.form()
        params = {}
        for key, value in form.multi_items():
            if isinstance(value, StarletteUploadFile):
                continue
            normalized = str(value).strip()
            if normalized:
                params[key] = normalized
        return params

    return {}


class SignatureVerifyMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/health"}
    SKIP_PREFIXES = ("/panel", "/internal", "/static")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or
            path in self.SKIP_PATHS
            or any(path.startswith(p) for p in self.SKIP_PREFIXES)
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        if settings.DEBUG:
            return await call_next(request)

        try:
            body = await request.body()
            params = await _extract_request_params(request, body)

            request = Request(request.scope, _build_receive(body))

            if not verify_signature(params, settings.STATIC_KEY, settings.SIGNATURE_TIMEOUT_SECONDS):
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": 403,
                        "msg": "签名验证失败",
                        "data": None,
                        "requestId": None,
                    },
                )
        except Exception:
            return JSONResponse(
                status_code=403,
                content={
                    "code": 403,
                    "msg": "签名验证异常",
                    "data": None,
                    "requestId": None,
                },
            )

        return await call_next(request)
