import logging
import asyncio
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class SmsService:
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        شماره تلفن را نرمال‌سازی می‌کند تا به فرمت معتبر ایران (09xxxxxxxxx) درآید.
        """
        p = phone.strip().replace(" ", "").replace("-", "")
        if p.startswith("+98"):
            p = "0" + p[3:]
        elif p.startswith("98"):
            p = "0" + p[2:]
        elif len(p) == 10 and p.startswith("9"):
            p = "0" + p
        return p

    @staticmethod
    def send_verification_code_sync(phone_number: str, code: str) -> Dict[str, Any]:
        """
        ارسال کد اعتبارسنجی با استفاده از الگوی خدماتی ملی‌پیامک (Direct REST API با Fallback به پکیج).
        """
        normalized_to = SmsService._normalize_phone(phone_number)
        username = settings.SMS_USERNAME
        password = settings.SMS_PASSWORD
        body_id = settings.VERIFICATION_BODY_ID

        if not username or not password:
            logger.warning("[SmsService] Melipayamak credentials are not configured.")
            return {"success": False, "error": "سامانه پیامک پیکربندی نشده است."}

        # 1. تلاش اولیه با استفاده از Direct REST endpoint با httpx (بدون وابستگی به پکیج خارجی در محیط سرور)
        try:
            import httpx
            with httpx.Client(timeout=8.0) as client:
                res = client.post(
                    "https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber",
                    json={
                        "username": username,
                        "password": password,
                        "text": str(code),
                        "to": normalized_to,
                        "bodyId": int(body_id)
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    logger.info(f"[SmsService-REST] Sent OTP to {normalized_to}. Response: {data}")
                    return {"success": True, "response": data}
        except Exception as rest_err:
            logger.warning(f"[SmsService] REST request failed, trying library fallback: {rest_err}")

        # 2. Fallback به پکیج melipayamak در صورت نیاز
        try:
            from melipayamak import Api
            api = Api(username, password)
            sms = api.sms()
            response = sms.send_by_base_number(str(code), normalized_to, int(body_id))
            logger.info(f"[SmsService] Sent OTP to {normalized_to} with bodyId {body_id}. Response: {response}")
            return {
                "success": True,
                "response": response
            }
        except Exception as e:
            logger.error(f"[SmsService] Failed to send OTP to {normalized_to}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


    @classmethod
    async def send_verification_code(cls, phone_number: str, code: str) -> Dict[str, Any]:
        """
        اجرای ناهمگام (Non-blocking) برای جلوگیری از مسدود شدن Event Loop در FastAPI.
        """
        return await asyncio.to_thread(cls.send_verification_code_sync, phone_number, code)
