from typing import Any, Optional
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.response import json_error_response


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationException(AppException):
    def __init__(self, message: str = "اطلاعات ورودی ناقص است یا فرمت درستی ندارد.", details: Optional[Any] = None):
        super().__init__(code="VALIDATION_FAILED", message=message, status_code=400, details=details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "نشست کاری شما منقضی شده است؛ لطفاً مجدداً وارد شوید.", code: str = "TOKEN_EXPIRED"):
        super().__init__(code=code, message=message, status_code=401)


class AccessDeniedException(AppException):
    def __init__(self, message: str = "شما دسترسی به این پرونده مشاوره یا پیام خصوصی را ندارید."):
        super().__init__(code="ACCESS_DENIED", message=message, status_code=403)


class ThreadNotFoundException(AppException):
    def __init__(self, message: str = "پرسش یا گفتگوی مورد نظر یافت نشد."):
        super().__init__(code="THREAD_NOT_FOUND", message=message, status_code=404)


class SurahNotFoundException(AppException):
    def __init__(self, message: str = "سوره مورد نظر معتبر نیست."):
        super().__init__(code="SURAH_NOT_FOUND", message=message, status_code=404)


class AyahNotFoundException(AppException):
    def __init__(self, message: str = "آیه مورد نظر یافت نشد."):
        super().__init__(code="AYAH_NOT_FOUND", message=message, status_code=404)



class BookNotFoundException(AppException):
    def __init__(self, message: str = "کتاب مورد نظر در کتابخانه موجود نیست."):
        super().__init__(code="BOOK_NOT_FOUND", message=message, status_code=404)


class AttachmentOversizeException(AppException):
    def __init__(
        self,
        message: str = "حجم فایل ارسالی بیش از سقف مجاز (۲۵ مگابایت) است.",
        details: Optional[Any] = None
    ):
        super().__init__(
            code="ATTACHMENT_OVERSIZE",
            message=message,
            status_code=413,
            details=details
        )


class AIRateLimitException(AppException):
    def __init__(self, message: str = "تعداد پرسش‌های هوش مصنوعی بیش از سقف مجاز است؛ لطفاً کمی تأمل کنید."):
        super().__init__(code="AI_RATE_LIMIT", message=message, status_code=429)


class ApiKeyInvalidException(AppException):
    def __init__(self, message: str = "کلید API ارائه‌شده نامعتبر است یا منقضی شده است."):
        super().__init__(code="API_KEY_INVALID", message=message, status_code=401)


class DeveloperQuotaExceededException(AppException):
    def __init__(self, message: str = "سهمیه توکن ماهانه حساب توسعه‌دهنده به اتمام رسیده است."):
        super().__init__(code="QUOTA_EXCEEDED", message=message, status_code=429)


class DeveloperRateLimitException(AppException):
    def __init__(self, message: str = "تعداد درخواست‌های ارسالی بیش از سقف مجاز بر دقیقه (Rate Limit) است."):
        super().__init__(code="RATE_LIMIT_EXCEEDED", message=message, status_code=429)


async def app_exception_handler(request: Request, exc: AppException):
    return json_error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg")
        })
    return json_error_response(
        code="VALIDATION_FAILED",
        message="اطلاعات ورودی ناقص است یا فرمت درستی ندارد.",
        details=errors,
        status_code=400
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        401: ("TOKEN_EXPIRED", "نشست کاری شما منقضی شده است؛ لطفاً مجدداً وارد شوید."),
        403: ("ACCESS_DENIED", "شما دسترسی به این بخش را ندارید."),
        404: ("NOT_FOUND", "منبع درخواستی یافت نشد."),
        413: ("ATTACHMENT_OVERSIZE", "حجم داده ارسالی بیش از سقف مجاز است."),
        429: ("AI_RATE_LIMIT", "تعداد درخواست‌ها بیش از سقف مجاز است."),
    }
    code, default_msg = code_map.get(exc.status_code, ("INTERNAL_SERVER_ERROR", "خطایی در پردازش رخ داد."))
    detail_msg = exc.detail if exc.detail and isinstance(exc.detail, str) else default_msg
    return json_error_response(
        code=code,
        message=detail_msg,
        status_code=exc.status_code
    )


async def global_exception_handler(request: Request, exc: Exception):
    return json_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="خطایی در سرور رخ داد؛ تیم فنی در حال بررسی است.",
        details=str(exc) if str(exc) else None,
        status_code=500
    )
