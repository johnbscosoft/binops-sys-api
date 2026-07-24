from typing import Any

from fastapi.encoders import jsonable_encoder


SUCCESS_STATUS_CODE = 1000
ERROR_STATUS_CODE = 1002
SENSITIVE_RESPONSE_KEYS = {"hashed_password"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if key not in SENSITIVE_RESPONSE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _as_array(data: Any = None) -> list[Any]:
    if data is None:
        return []
    encoded = _sanitize(jsonable_encoder(data))
    return encoded if isinstance(encoded, list) else [encoded]


def success_response(
    data: Any = None,
    message: str = "Operation Successful",
) -> dict[str, Any]:
    return {
        "status": True,
        "status_code": SUCCESS_STATUS_CODE,
        "message": message,
        "data": _as_array(data),
    }


def error_response(
    message: str = "Operation Failed",
    data: Any = None,
) -> dict[str, Any]:
    return {
        "status": False,
        "status_code": ERROR_STATUS_CODE,
        "message": message,
        "data": _as_array(data),
    }
