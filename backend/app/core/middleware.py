from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class HeaderContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract global tracking and localization headers
        request.state.app_version = request.headers.get("x-app-version", "1.0.0")
        request.state.device_id = request.headers.get("x-device-id", "unknown-device")
        request.state.language = request.headers.get("accept-language", "fa-IR")

        response = await call_next(request)

        # Append standard API headers
        response.headers["X-App-Version"] = request.state.app_version
        response.headers["X-Device-Id"] = request.state.device_id
        return response
