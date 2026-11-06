from typing import Optional, AsyncGenerator
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, AccessDeniedException
from app.db.models import User
from sqlalchemy import select

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            message="توکن احراز هویت الزامی است.",
            code="TOKEN_MISSING"
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise UnauthorizedException(
            message="نشست کاری شما منقضی شده است؛ لطفاً مجدداً وارد شوید.",
            code="TOKEN_EXPIRED"
        )

    user_id = payload["sub"]
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise UnauthorizedException(
            message="کاربر معتبر نیست.",
            code="USER_NOT_FOUND"
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    return await db.scalar(select(User).where(User.id == user_id))


async def require_scholar(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role not in ["SCHOLAR", "ADMIN"]:
        raise AccessDeniedException(message="دسترسی به این بخش نیازمند مجوز استاد/عالم است.")
    return current_user


async def get_developer_context(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    from app.services.developer_service import DeveloperService
    return await DeveloperService.authenticate_developer_request(db, x_api_key)

