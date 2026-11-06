from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.schemas.dhikr import (
    DhikrCreate,
    DhikrUpdate,
    DhikrCategoryCreate,
    DhikrResponse,
    DhikrCategoryResponse
)
from app.services.dhikr_service import DhikrService

router = APIRouter()


@router.get("/categories", summary="فهرست دسته‌بندی‌های ادعیه و اذکار در پنل مدیریت")
async def list_admin_dhikr_categories(
    db: AsyncSession = Depends(get_db)
):
    categories = await DhikrService.get_categories(db=db)
    return success_response(data=[c.to_dict() for c in categories])


@router.post("/categories", summary="ایجاد یا ویرایش دسته‌بندی جدید برای ادعیه و اذکار")
async def create_or_update_dhikr_category(
    payload: DhikrCategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    cat = await DhikrService.create_category(
        db=db,
        payload=payload,
        is_system=True
    )
    return success_response(
        data=cat.to_dict(),
        meta={"message": "دسته‌بندی با موفقیت ذخیره شد."}
    )



@router.get("", summary="فهرست تمامی ادعیه و اذکار در پنل مدیریت")
async def list_admin_dhikrs(
    category: Optional[str] = Query(None, description="فیلتر بر اساس شناسه دسته‌بندی"),
    q: Optional[str] = Query(None, description="جستجو در عنوان یا متن ذکر"),
    is_system: Optional[bool] = Query(None, description="فیلتر اذکار سیستمی یا کاربر"),
    db: AsyncSession = Depends(get_db)
):
    dhikrs = await DhikrService.get_dhikrs(
        db=db,
        category=category,
        search=q,
        is_system=is_system
    )
    categories = await DhikrService.get_categories(db=db)
    return success_response(data={
        "total": len(dhikrs),
        "items": [d.to_dict() for d in dhikrs],
        "categories": [c.to_dict() for c in categories]
    })


@router.get("/{dhikr_id}", summary="دریافت جزئیات یک ذکر مشخص")
async def get_admin_dhikr(
    dhikr_id: str,
    db: AsyncSession = Depends(get_db)
):
    dhikr = await DhikrService.get_dhikr(db=db, dhikr_id=dhikr_id)
    if not dhikr:
        raise HTTPException(status_code=404, detail="ذکر مورد نظر یافت نشد.")
    return success_response(data=dhikr.to_dict())


@router.post("", summary="افزودن دعا یا ذکر جدید به دسته‌بندی مشخص در پنل ادمین")
async def create_admin_dhikr(
    payload: DhikrCreate,
    is_system: bool = Query(True, description="ذکر سیستمی و معتبر رسمی"),
    db: AsyncSession = Depends(get_db)
):
    dhikr = await DhikrService.create_dhikr(
        db=db,
        payload=payload,
        user_id=None,
        is_system=is_system
    )
    return success_response(
        data=dhikr.to_dict(),
        meta={"message": "دعا و ذکر جدید با موفقیت به بانک ادعیه اضافه شد."}
    )


@router.put("/{dhikr_id}", summary="ویرایش مشخصات دعا یا ذکر")
async def update_admin_dhikr(
    dhikr_id: str,
    payload: DhikrUpdate,
    db: AsyncSession = Depends(get_db)
):
    updated = await DhikrService.update_dhikr(
        db=db,
        dhikr_id=dhikr_id,
        payload=payload
    )
    if not updated:
        raise HTTPException(status_code=404, detail="ذکر مورد نظر یافت نشد.")
    return success_response(
        data=updated.to_dict(),
        meta={"message": "مشخصات ذکر با موفقیت به‌روزرسانی شد."}
    )


@router.delete("/{dhikr_id}", summary="حذف یک دعا یا ذکر توسط ادمین")
async def delete_admin_dhikr(
    dhikr_id: str,
    db: AsyncSession = Depends(get_db)
):
    deleted = await DhikrService.delete_dhikr(
        db=db,
        dhikr_id=dhikr_id,
        is_admin=True
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="ذکر مورد نظر یافت نشد یا قابل حذف نیست.")
    return success_response(
        data={"deleted": True},
        meta={"message": "دعا یا ذکر با موفقیت از سیستم حذف گردید."}
    )


@router.post("/seed", summary="بازنشانی و بازتولید اذکار و دسته‌بندی‌های پیش‌فرض")
async def seed_dhikrs_endpoint(
    db: AsyncSession = Depends(get_db)
):
    seeded = await DhikrService.seed_defaults(db=db)
    return success_response(
        data={"seeded": seeded},
        meta={"message": "اذکار و دسته‌بندی‌های معارفی استاندارد با موفقیت بارگذاری شدند."}
    )

