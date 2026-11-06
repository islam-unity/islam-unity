from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.schemas.dhikr import DhikrCreate, DhikrResponse
from app.services.dhikr_service import DhikrService

router = APIRouter()


@router.get("/categories", summary="فهرست دسته‌بندی‌های ادعیه و اذکار")
async def get_dhikr_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    دریافت دسته‌بندی‌های ادعیه و اذکار (ایام هفته، تعقیبات، حاجات، مناجات، اذکار من و ...)
    """
    categories = await DhikrService.get_categories(db=db)
    return success_response(data=[c.to_dict() for c in categories])


@router.get("", summary="فهرست ادعیه و اذکار با امکان فیلتر بر اساس دسته‌بندی و جستجو")
async def get_dhikrs(
    category: Optional[str] = Query(None, description="شناسه دسته (daily, taqibat, hajat, munajat, custom, ...)"),
    q: Optional[str] = Query(None, description="جستجو در عنوان یا متن عربی یا ترجمه ذکر"),
    user_id: Optional[str] = Query(None, description="شناسه کاربر برای دریافت اذکار شخصی"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID", description="شناسه کاربر از هدر"),
    db: AsyncSession = Depends(get_db)
):
    """
    دریافت فهرست ادعیه و اذکار.
    در صورتی که کاربر شناسه خود را ارسال کند، اذکار عمومی + اذکار شخصی خودش بازگردانده می‌شوند.
    """
    effective_user_id = user_id or x_user_id
    dhikrs = await DhikrService.get_dhikrs(
        db=db,
        category=category,
        user_id=effective_user_id,
        search=q
    )
    return success_response(data={
        "total": len(dhikrs),
        "category": category or "all",
        "items": [d.to_dict() for d in dhikrs]
    })


@router.get("/{dhikr_id}", summary="دریافت جزئیات کامل یک دعا یا ذکر مشخص")
async def get_single_dhikr(
    dhikr_id: str,
    db: AsyncSession = Depends(get_db)
):
    dhikr = await DhikrService.get_dhikr(db=db, dhikr_id=dhikr_id)
    if not dhikr:
        raise HTTPException(status_code=404, detail="ذکر یا دعای مورد نظر یافت نشد.")
    return success_response(data=dhikr.to_dict())


@router.post("", summary="ثبت و افزودن دعا یا ذکر دلخواه توسط خود کاربر")
async def create_user_dhikr(
    payload: DhikrCreate,
    user_id: Optional[str] = Query(None, description="شناسه کاربر"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    افزودن دعا یا ذکر دلخواه توسط کاربر با متن عربی، ترجمه، هدف شمارش و فضیلت اختیاری.
    """
    effective_user_id = user_id or x_user_id or "user_guest"
    # User-added dhikrs are not system by default
    dhikr = await DhikrService.create_dhikr(
        db=db,
        payload=payload,
        user_id=effective_user_id,
        is_system=False
    )
    return success_response(
        data=dhikr.to_dict(),
        meta={"message": "دعای دلخواه شما با موفقیت به شمارنده اذکار اضافه شد."}
    )


@router.delete("/{dhikr_id}", summary="حذف ذکر شخصی توسط کاربر")
async def delete_user_dhikr(
    dhikr_id: str,
    user_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    effective_user_id = user_id or x_user_id
    deleted = await DhikrService.delete_dhikr(
        db=db,
        dhikr_id=dhikr_id,
        user_id=effective_user_id,
        is_admin=False
    )
    if not deleted:
        raise HTTPException(
            status_code=403,
            detail="امکان حذف این ذکر وجود ندارد (فقط ذکرهای شخصی ایجاد شده توسط خود کاربر قابل حذف هستند)."
        )
    return success_response(
        data={"deleted": True},
        meta={"message": "ذکر دلخواه با موفقیت حذف شد."}
    )

