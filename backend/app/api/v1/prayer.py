from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.services.prayer_service import PrayerService

router = APIRouter()


@router.get("", summary="دریافت فهرست اوقات شرعی تمامی شهرها برای کلاینت")
async def get_all_prayer_times(
    q: Optional[str] = Query(None, description="جستجوی نام شهر"),
    db: AsyncSession = Depends(get_db)
):
    """
    دریافت اوقات شرعی شهرهای ثبت‌شده در پایگاه داده.
    اگر پایگاه داده خالی باشد، شهرهای پیش‌فرض مقداردهی اولیه می‌شوند.
    """
    cities = await PrayerService.get_all_cities(db=db, search=q)
    if not cities:
        # Seed defaults if empty
        await PrayerService.seed_default_cities(db=db)
        cities = await PrayerService.get_all_cities(db=db, search=q)

    return success_response(data={
        "total": len(cities),
        "cities": [c.to_dict() for c in cities]
    })


@router.get("/{city_id}", summary="دریافت اوقات شرعی یک شهر مشخص")
async def get_single_city_prayer_time(
    city_id: str,
    db: AsyncSession = Depends(get_db)
):
    city = await PrayerService.get_city(db=db, city_id=city_id)
    if not city:
        raise HTTPException(status_code=404, detail="اطلاعات اوقات شرعی شهر مورد نظر یافت نشد")
    return success_response(data=city.to_dict())
