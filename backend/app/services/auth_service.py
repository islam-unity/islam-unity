import uuid
import random
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, PersonaConfig
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, UpdateUserProfileRequest,
    AvailableInterestsAndPresetsResponse, InterestCategoryDTO, BotRolePresetDTO
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import AppException, UnauthorizedException
from app.services.sms_service import SmsService

# ذخیره‌سازی موقت کدهای تأیید در حافظه با تاریخ انقضا (TTL)
# ساختار: { "09xxxxxxxxx": {"code": "12345", "expires_at": timestamp} }
_OTP_CACHE: Dict[str, Dict[str, Any]] = {}


class AuthService:
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return SmsService._normalize_phone(phone)

    @classmethod
    async def request_otp(cls, phone_number: str) -> dict:
        phone = cls._normalize_phone(phone_number)
        if len(phone) < 11 or not phone.startswith("09"):
            raise AppException(
                code="INVALID_PHONE_NUMBER",
                message="شماره تلفن همراه معتبر نیست. لطفاً شماره را مانند 09123456789 وارد نمایید.",
                status_code=400
            )

        now = time.time()
        # بررسی محدودیت زمانی ارسال مجدد (حداقل ۲ دقیقه فاصله)
        if phone in _OTP_CACHE:
            existing = _OTP_CACHE[phone]
            # اگر هنوز بیش از ۳ دقیقه از اعتبار باقی مانده (از کل ۵ دقیقه)
            if existing.get("expires_at", 0) - now > 180:
                remaining_sec = int(existing["expires_at"] - now - 180)
                raise AppException(
                    code="OTP_TOO_FREQUENT",
                    message=f"لطفاً {remaining_sec} ثانیه دیگر جهت درخواست مجدد کد شکیبا باشید.",
                    status_code=429
                )

        code = str(random.randint(10000, 99999))
        expires_at = now + 300  # ۵ دقیقه اعتبار

        # ارسال پیامک با الگوی ملی‌پیامک
        send_res = await SmsService.send_verification_code(phone, code)
        if not send_res.get("success"):
            raise AppException(
                code="SMS_SEND_FAILED",
                message="ارسال پیامک با خطا مواجه شد. لطفاً دوباره تلاش نمایید.",
                status_code=502
            )

        _OTP_CACHE[phone] = {
            "code": code,
            "expires_at": expires_at
        }

        return {
            "message": "کد تأیید برای شماره شما پیامک شد.",
            "phoneNumber": phone,
            "expiresIn": 300
        }

    @classmethod
    async def verify_otp_and_login(cls, db: AsyncSession, phone_number: str, code: str) -> dict:
        phone = cls._normalize_phone(phone_number)
        now = time.time()

        cached = _OTP_CACHE.get(phone)
        if not cached or cached.get("expires_at", 0) < now:
            raise AppException(
                code="OTP_EXPIRED",
                message="کد تأیید منقضی شده یا درخواست نشده است. لطفاً کد جدید دریافت کنید.",
                status_code=400
            )

        if str(cached.get("code")).strip() != str(code).strip():
            raise AppException(
                code="INVALID_OTP",
                message="کد تأیید وارد شده اشتباه است.",
                status_code=400
            )

        # مصرف کد پس از تأیید موفق
        del _OTP_CACHE[phone]

        # بررسی وجود کاربر در دیتابیس؛ اگر نبود کاربر جدید ایجاد می‌شود (Auto-Register / Login)
        stmt = select(User).where(User.phone_number == phone)
        user = await db.scalar(stmt)

        if not user:
            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            user = User(
                id=user_id,
                phone_number=phone,
                full_name=f"کاربر {phone[-4:]}",
                hashed_password=hash_password(uuid.uuid4().hex),
                role="SEEKER",
                scholar_status="NONE",
                madhhab="شیعه اثناعشری",
                interests=[],
                knowledge_level="GENERAL"
            )
            db.add(user)

            persona = PersonaConfig(
                user_id=user_id,
                bot_name="دستیار معارفی اتحاد",
                bot_role_preset="GENERAL_ASSISTANT",
                tone="FRIENDLY_WARM",
                fiqh_approach="APPROXIMATION_UNITY",
                detail_level="STANDARD",
                include_ayah_address=True,
                include_hadith_references=True
            )
            db.add(persona)

            await db.commit()
            await db.refresh(user)

        token = create_access_token(
            subject=user.id,
            role=user.role,
            extra_claims={
                "name": user.full_name,
                "scholar_status": getattr(user, 'scholar_status', 'NONE')
            }
        )

        return {
            "access_token": token,
            "token_type": "Bearer",
            "user_id": user.id,
            "role": user.role,
            "full_name": user.full_name,
            "scholar_status": getattr(user, 'scholar_status', 'NONE'),
            "scholarStatus": getattr(user, 'scholar_status', 'NONE'),
            "mosque_name": getattr(user, 'mosque_name', None),
            "mosque_address": getattr(user, 'mosque_address', None),
            "isNewUser": bool(user.full_name.startswith("کاربر "))
        }

    @staticmethod
    async def register(db: AsyncSession, data: UserRegisterRequest) -> User:

        stmt = select(User).where(User.phone_number == data.phone_number)
        existing = await db.scalar(stmt)
        if existing:
            raise AppException(
                code="USER_ALREADY_EXISTS",
                message="این شماره تماس قبلاً در سامانه ثبت شده است.",
                status_code=400
            )

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        mosque_name = data.mosque_name or data.mosqueName
        mosque_address = data.mosque_address or data.mosqueAddress
        is_requesting_scholar = (data.role == "SCHOLAR" or data.scholar_status == "PENDING" or bool(mosque_name))

        # Initially SEEKER if requesting scholar until admin approval
        assigned_role = "SCHOLAR" if (data.role == "SCHOLAR" and data.scholar_status == "APPROVED") else "SEEKER"
        scholar_status = "PENDING" if is_requesting_scholar else (data.scholar_status or "NONE")

        user = User(
            id=user_id,
            phone_number=data.phone_number,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=assigned_role,
            scholar_status=scholar_status,
            mosque_name=mosque_name,
            mosque_address=mosque_address,
            madhhab=data.madhhab or "شیعه اثناعشری",
            age=data.age,
            gender=data.gender,
            education=data.education,
            interests=data.interests or [],
            knowledge_level=data.knowledge_level or "GENERAL",
            learning_goals=data.learning_goals,
            avatar=data.avatar
        )
        db.add(user)

        # Default persona configuration
        persona = PersonaConfig(
            user_id=user_id,
            bot_name="دستیار معارفی اتحاد",
            bot_role_preset="GENERAL_ASSISTANT",
            tone="FRIENDLY_WARM",
            fiqh_approach="APPROXIMATION_UNITY",
            detail_level="STANDARD",
            include_ayah_address=True,
            include_hadith_references=True
        )
        db.add(persona)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def login(db: AsyncSession, data: UserLoginRequest) -> dict:
        stmt = select(User).where(User.phone_number == data.phone_number)
        user = await db.scalar(stmt)
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException(
                message="شماره تلفن یا رمز عبور اشتباه است.",
                code="INVALID_CREDENTIALS"
            )

        token = create_access_token(
            subject=user.id, 
            role=user.role, 
            extra_claims={
                "name": user.full_name,
                "scholar_status": getattr(user, 'scholar_status', 'NONE')
            }
        )
        return {
            "access_token": token,
            "token_type": "Bearer",
            "user_id": user.id,
            "role": user.role,
            "full_name": user.full_name,
            "scholar_status": getattr(user, 'scholar_status', 'NONE'),
            "scholarStatus": getattr(user, 'scholar_status', 'NONE'),
            "mosque_name": getattr(user, 'mosque_name', None),
            "mosque_address": getattr(user, 'mosque_address', None)
        }

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return await db.scalar(stmt)

    @staticmethod
    def format_user_profile(user: User) -> dict:
        return {
            "id": user.id,
            "phoneNumber": user.phone_number,
            "fullName": user.full_name,
            "role": user.role,
            "scholarStatus": getattr(user, 'scholar_status', 'NONE'),
            "scholar_status": getattr(user, 'scholar_status', 'NONE'),
            "mosqueName": getattr(user, 'mosque_name', None),
            "mosque_name": getattr(user, 'mosque_name', None),
            "mosqueAddress": getattr(user, 'mosque_address', None),
            "mosque_address": getattr(user, 'mosque_address', None),
            "madhhab": user.madhhab,
            "age": user.age,
            "gender": user.gender,
            "education": user.education,
            "interests": user.interests or [],
            "knowledgeLevel": user.knowledge_level or "GENERAL",
            "learningGoals": user.learning_goals,
            "avatar": user.avatar
        }

    @staticmethod
    async def update_profile(db: AsyncSession, user_id: str, data: UpdateUserProfileRequest) -> User:
        user = await AuthService.get_by_id(db, user_id)
        if not user:
            raise AppException(
                code="USER_NOT_FOUND",
                message="کاربر مورد نظر یافت نشد.",
                status_code=404
            )

        if data.fullName is not None:
            user.full_name = data.fullName
        if data.madhhab is not None:
            user.madhhab = data.madhhab
        if data.age is not None:
            user.age = data.age
        if data.gender is not None:
            user.gender = data.gender
        if data.education is not None:
            user.education = data.education
        if data.interests is not None:
            user.interests = data.interests
        if data.knowledgeLevel is not None:
            user.knowledge_level = data.knowledgeLevel
        if data.learningGoals is not None:
            user.learning_goals = data.learningGoals
        if data.avatar is not None:
            user.avatar = data.avatar
        if data.role is not None:
            user.role = data.role
        if data.scholarStatus is not None:
            user.scholar_status = data.scholarStatus
        elif data.role == "SCHOLAR" and not getattr(user, 'scholar_status', None):
            user.scholar_status = "PENDING"
        if data.mosqueName is not None:
            user.mosque_name = data.mosqueName
        if data.mosqueAddress is not None:
            user.mosque_address = data.mosqueAddress

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def get_available_interests_and_presets() -> AvailableInterestsAndPresetsResponse:
        interests = [
            InterestCategoryDTO(
                id="TAFSIR",
                title="تفسیر و تدبر قرآنی",
                description="تأمل در آیات کلام‌الله، شأن نزول، مفاهیم عمیق و تفاسیر معتبر فریقین",
                iconName="menu_book",
                isPrimary=True
            ),
            InterestCategoryDTO(
                id="AKHLAQ",
                title="اخلاق، عرفان و خودسازی",
                description="تهذیب نفس، فضایل و رذایل اخلاقی، سیر و سلوک معنوی و نصایح اهل‌بیت (ع)",
                iconName="self_improvement",
                isPrimary=False
            ),
            InterestCategoryDTO(
                id="AHKAM",
                title="فقه و احکام شرعی",
                description="احکام عبادی، معاملات، احکام کاربردی بانوان و آقایان و استفتائات شرعی",
                iconName="gavel",
                isPrimary=False
            ),
            InterestCategoryDTO(
                id="KALAM",
                title="کلام و عقاید اسلامی",
                description="اصول دین، توحید، نبوت، امامت، معاد و پاسخ به شبهات فکری و اعتقادی معاصر",
                iconName="psychology",
                isPrimary=False
            ),
            InterestCategoryDTO(
                id="HISTORY",
                title="تاریخ و سیره نبوی و اهل‌بیت (ع)",
                description="زندگی‌نامه پیامبر اعظم و ائمه اطهار، تمدن اسلامی و تحلیل رویدادهای صدر اسلام",
                iconName="history_edu",
                isPrimary=False
            ),
            InterestCategoryDTO(
                id="LIFESTYLE",
                title="سبک زندگی، خانواده و تربیت دینی",
                description="آداب معاشرت اسلامی، همسرداری، آرامش خانوادگی و اصول تربیت معارفی فرزندان",
                iconName="family_restroom",
                isPrimary=False
            )
        ]

        knowledge_levels = [
            {
                "code": "GENERAL",
                "title": "عمومی و کاربردی",
                "description": "بیان ساده، روان، شیوا و قابل فهم برای عموم مخاطبان بدون اصطلاحات پیچیده"
            },
            {
                "code": "ACADEMIC",
                "title": "دانشگاهی و تحلیلی",
                "description": "رویکرد علمی، مستند، استدلالی با استناد به منابع معتبر دانشگاهی و حوزوی"
            },
            {
                "code": "SEMINARY",
                "title": "حوزوی و تخصصی",
                "description": "بررسی فنی ادله نقلی و عقلی، مصطلحات اصولی، فقهی، رجالی و تفسیری"
            }
        ]

        education_levels = [
            "زیر دیپلم",
            "دیپلم",
            "کاردانی",
            "کارشناسی",
            "کارشناسی ارشد",
            "دکتری",
            "سطح ۱ حوزه",
            "سطح ۲ حوزه",
            "سطح ۳ حوزه",
            "سطح ۴ و خارج فقه"
        ]

        genders = [
            {"code": "MALE", "title": "آقا"},
            {"code": "FEMALE", "title": "خانم"}
        ]

        bot_presets = [
            BotRolePresetDTO(
                key="TAFSIR_RESEARCHER",
                title="پژوهشگر تدبر و تفسیر قرآنی",
                description="تمرکز ویژه بر آیات، شأن نزول، مفردات قرآنی و استناد دقیق به تفاسیر",
                defaultTone="SCHOLARLY_FORMAL",
                defaultAvatar="/media/avatars/bot_tafsir.png",
                systemRoleDescription="پژوهشگر تخصصی تدبر و تفسیر قرآن کریم با استناد به آیات و تفاسیر فریقین"
            ),
            BotRolePresetDTO(
                key="ETHICS_MENTOR",
                title="مربی اخلاق و خودسازی",
                description="بیان دلگرم‌کننده، تهذیب نفس، فضایل معنوی و توصیه‌های انسان‌ساز",
                defaultTone="MYSTICAL_SPIRITUAL",
                defaultAvatar="/media/avatars/bot_ethics.png",
                systemRoleDescription="مربی اخلاق و معنویت با تأکید بر پالایش درون و سیره اخلاقی معصومین"
            ),
            BotRolePresetDTO(
                key="FIQH_ADVISOR",
                title="مشاور احکام شرعی و مسائل روز",
                description="پاسخ‌های صریح، منظم و مستند به فتاوا با رعایت تقریب و فقه مقارن",
                defaultTone="CONCISE_DIRECT",
                defaultAvatar="/media/avatars/bot_fiqh.png",
                systemRoleDescription="مشاور دقیق در احکام شرعی، تکالیف عملی و پاسخ به استفتائات"
            ),
            BotRolePresetDTO(
                key="FAMILY_LIFESTYLE",
                title="مشاور سبک زندگی و خانواده معارفی",
                description="راهنمایی‌های کاربردی بر اساس قرآن و سنت برای آرامش در خانه و خانواده",
                defaultTone="FRIENDLY_WARM",
                defaultAvatar="/media/avatars/bot_family.png",
                systemRoleDescription="مشاور امین در مسائل خانواده، آداب معاشرت و تربیت معارفی"
            ),
            BotRolePresetDTO(
                key="GENERAL_ASSISTANT",
                title="دستیار جامع معارف اسلامی",
                description="راهنمای همه‌جانبه و متوازن در تمامی حوزه‌های قرآنی، روایی، فقهی و تاریخی",
                defaultTone="FRIENDLY_WARM",
                defaultAvatar="/media/avatars/bot_general.png",
                systemRoleDescription="دستیار پیشرفته و جامع معارفی اتحاد برای پاسخ به تمام پرسش‌های اسلامی"
            ),
            BotRolePresetDTO(
                key="CUSTOM",
                title="نقش سفارشی کاربر",
                description="تعریف آزادانه هویت و دستورالعمل دلخواه توسط خود کاربر",
                defaultTone="FRIENDLY_WARM",
                defaultAvatar=None,
                systemRoleDescription="دستیار سفارشی کاربر مطابق با دستورات تنظیم‌شده"
            )
        ]

        return AvailableInterestsAndPresetsResponse(
            interestCategories=interests,
            knowledgeLevels=knowledge_levels,
            educationLevels=education_levels,
            genders=genders,
            botRolePresets=bot_presets
        )
