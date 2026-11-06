from datetime import datetime, timezone
from typing import Any, Optional, Dict
from fastapi.responses import JSONResponse


def get_current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": True,
        "data": data,
        "timestamp": get_current_utc_timestamp()
    }
    if meta is not None:
        payload["meta"] = meta
    return payload


def json_success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=success_response(data=data, meta=meta, status_code=status_code)
    )


def error_response(
    code: str,
    message: str,
    details: Optional[Any] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    err_obj: Dict[str, Any] = {
        "code": code,
        "message": message
    }
    if details is not None:
        err_obj["details"] = details

    return {
        "success": False,
        "error": err_obj,
        "timestamp": get_current_utc_timestamp()
    }


def json_error_response(
    code: str,
    message: str,
    details: Optional[Any] = None,
    status_code: int = 400
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_response(code=code, message=message, details=details, status_code=status_code)
    )
