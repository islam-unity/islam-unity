from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.db.models import User
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserProfileResponse,
    UpdateUserProfileRequest, SendOtpRequest, VerifyOtpRequest
)
from app.services.auth_service import AuthService
from app.core.response import success_response

router = APIRouter()


@router.post("/send-otp", summary="ارسال کد تأیید پیامکی (OTP) با سامانه ملی‌پیامک")
async def send_otp(
    data: SendOtpRequest
):
    result = await AuthService.request_otp(data.phone_number)
    return success_response(result)


@router.post("/verify-otp", summary="اعتبارسنجی کد تأیید پیامکی و ورود/ثبت‌نام مستقیم")
async def verify_otp(
    data: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db)
):
    token_data = await AuthService.verify_otp_and_login(db, data.phone_number, data.code)
    return success_response(token_data)



@router.post("/register", summary="ثبت‌نام کاربر جدید")
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await AuthService.register(db, data)
    return success_response({
        "userId": user.id,
        "phoneNumber": user.phone_number,
        "fullName": user.full_name,
        "role": user.role
    })


@router.post("/login", summary="ورود به سامانه و دریافت توکن JWT")
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    token_data = await AuthService.login(db, data)
    return success_response(token_data)


@router.get("/me", summary="دریافت پروفایل کاربر جاری شامل مشخصات فردی و علایق")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    profile_data = AuthService.format_user_profile(current_user)
    return success_response(profile_data)


@router.put("/profile", summary="ویرایش پروفایل، مشخصات فردی (سن، جنسیت، تحصیلات) و علایق معارفی کاربر")
async def update_profile(
    data: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated_user = await AuthService.update_profile(db, current_user.id, data)
    profile_data = AuthService.format_user_profile(updated_user)
    return success_response(profile_data)


@router.get("/interests-and-presets", summary="دریافت فهرست استاندارد علایق موضوعی، سطوح علمی، مقاطع تحصیلی و قالب‌های ربات")
async def get_interests_and_presets():
    res = AuthService.get_available_interests_and_presets()
    return success_response(res.model_dump())
