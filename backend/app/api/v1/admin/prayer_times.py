import json
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.services.prayer_service import PrayerService

router = APIRouter()


class SingleCityPrayerRequest(BaseModel):
    city_id: Optional[str] = None
    city_name: str
    province: Optional[str] = None
    country: Optional[str] = "IR"
    fajr: str
    sunrise: str
    dhuhr: str
    asr: Optional[str] = None
    sunset: Optional[str] = None
    maghrib: str
    isha: Optional[str] = None
    midnight: Optional[str] = None
    calculation_method: Optional[str] = "مؤسسه ژئوفیزیک دانشگاه تهران"


class JsonUploadRequest(BaseModel):
    data: Optional[Union[Dict[str, Any], List[Any], str]] = None
    overwrite_existing: bool = True


@router.get("", summary="فهرست تمامی شهرهای ثبت‌شده به همراه اوقات شرعی")
async def list_prayer_times(
    q: Optional[str] = Query(None, description="جستجوی نام شهر یا استان"),
    db: AsyncSession = Depends(get_db)
):
    cities = await PrayerService.get_all_cities(db=db, search=q)
    return success_response(data={
        "total": len(cities),
        "items": [c.to_dict() for c in cities]
    })


@router.get("/export", summary="خروجی JSON کامل از اوقات شرعی تمام شهرها")
async def export_prayer_times_json(
    db: AsyncSession = Depends(get_db)
):
    cities = await PrayerService.get_all_cities(db=db)
    export_data = [c.to_dict() for c in cities]
    return success_response(data=export_data)


@router.post("/upload-json", summary="آپلود اوقات شرعی به صورت JSON (تک‌شهر، آرایه‌ای از شهرها، یا دیکشنری)")
async def upload_prayer_times_json(
    payload: Any = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    پشتیبانی از انواع فرمت‌های JSON:
    1. آرایه‌ای از آبجکت‌های شهرها
    2. یک شهر منفرد
    3. ساختار دیکشنری / کلید-مقدار شهرها
    """
    raw_json = payload
    if isinstance(payload, dict) and "data" in payload and payload["data"] is not None:
        raw_json = payload["data"]

    if isinstance(raw_json, str):
        try:
            raw_json = json.loads(raw_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"متن ورودی ساختار JSON معتبر ندارد: {str(e)}")

    try:
        result = await PrayerService.parse_and_upsert_json(
            db=db,
            raw_data=raw_json
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پردازش و ذخیره اوقات شرعی: {str(e)}")

    count = result.get("total_processed", 0)
    return success_response(
        data={
            "message": f"تعداد {count} شهر با موفقیت ذخیره/به‌روزرسانی شد.",
            "count": count,
            "created": result.get("created", 0),
            "updated": result.get("updated", 0),
            "cities": result.get("cities", [])
        }
    )


@router.post("/upload-file", summary="آپلود فایل .json اوقات شرعی شهرها")
async def upload_prayer_times_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        content = await file.read()
        raw_json = json.loads(content.decode("utf-8"))
        result = await PrayerService.parse_and_upsert_json(
            db=db,
            raw_data=raw_json
        )
    except json.JSONDecodeError as je:
        raise HTTPException(status_code=400, detail=f"فایل آپلود شده ساختار JSON معتبر ندارد: {str(je)}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {str(e)}")

    count = result.get("total_processed", 0)
    return success_response(
        data={
            "message": f"فایل «{file.filename}» با {count} شهر با موفقیت پردازش شد.",
            "count": count,
            "created": result.get("created", 0),
            "updated": result.get("updated", 0),
            "cities": result.get("cities", [])
        }
    )


@router.post("/reset-defaults", summary="بازنشانی اوقات شرعی به ۱۲ کلان‌شهر پیش‌فرض ایران")
async def reset_defaults(
    db: AsyncSession = Depends(get_db)
):
    count = await PrayerService.reset_defaults(db=db)
    cities = await PrayerService.get_all_cities(db=db)
    return success_response(
        data={
            "message": "اوقات شرعی با موفقیت به مقادیر پیش‌فرض بازنشانی شدند.",
            "count": count,
            "cities": [c.to_dict() for c in cities]
        }
    )


@router.post("", summary="ثبت یا ویرایش دستی اوقات شرعی یک شهر")
async def upsert_single_city(
    data: SingleCityPrayerRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        city = await PrayerService.upsert_city(
            db=db,
            city_data=data.model_dump(exclude_unset=True),
            source="admin_manual"
        )
        return success_response(
            data={
                "message": f"اوقات شرعی شهر «{city.city_name}» با موفقیت ثبت شد.",
                **city.to_dict()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{city_id}", summary="دریافت اوقات شرعی یک شهر مشخص")
async def get_city_prayer_time(
    city_id: str,
    db: AsyncSession = Depends(get_db)
):
    city = await PrayerService.get_city(db=db, city_id=city_id)
    if not city:
        raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد")
    return success_response(data=city.to_dict())


@router.delete("/{city_id}", summary="حذف اوقات شرعی یک شهر")
async def delete_city_prayer_time(
    city_id: str,
    db: AsyncSession = Depends(get_db)
):
    deleted = await PrayerService.delete_city(db=db, city_id=city_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد")
    return success_response(data={"message": "شهر با موفقیت حذف گردید"})
