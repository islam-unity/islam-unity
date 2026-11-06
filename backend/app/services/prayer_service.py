import json
import re
from typing import Dict, Any, List, Union, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, or_
from app.db.models.prayer_times import CityPrayerTime

DEFAULT_IRAN_CITIES = [
    { "city_id": "tehran", "city_name": "تهران (پایتخت)", "province": "تهران", "fajr": "04:48", "sunrise": "06:12", "dhuhr": "11:52", "asr": "15:08", "sunset": "17:31", "maghrib": "17:49", "isha": "18:41", "midnight": "23:10" },
    { "city_id": "mashhad", "city_name": "مشهد مقدس", "province": "خراسان رضوی", "fajr": "04:25", "sunrise": "05:49", "dhuhr": "11:29", "asr": "14:45", "sunset": "17:08", "maghrib": "17:26", "isha": "18:18", "midnight": "22:47" },
    { "city_id": "qom", "city_name": "قم المقدسة", "province": "قم", "fajr": "04:50", "sunrise": "06:13", "dhuhr": "11:53", "asr": "15:10", "sunset": "17:33", "maghrib": "17:51", "isha": "18:43", "midnight": "23:12" },
    { "city_id": "isfahan", "city_name": "اصفهان", "province": "اصفهان", "fajr": "04:49", "sunrise": "06:11", "dhuhr": "11:51", "asr": "15:09", "sunset": "17:32", "maghrib": "17:50", "isha": "18:41", "midnight": "23:11" },
    { "city_id": "shiraz", "city_name": "شیراز", "province": "فارس", "fajr": "04:46", "sunrise": "06:06", "dhuhr": "11:47", "asr": "15:07", "sunset": "17:29", "maghrib": "17:46", "isha": "18:36", "midnight": "23:07" },
    { "city_id": "tabriz", "city_name": "تبریز", "province": "آذربایجان شرقی", "fajr": "05:08", "sunrise": "06:34", "dhuhr": "12:13", "asr": "15:27", "sunset": "17:51", "maghrib": "18:10", "isha": "19:03", "midnight": "23:30" },
    { "city_id": "ahvaz", "city_name": "اهواز", "province": "خوزستان", "fajr": "05:01", "sunrise": "06:22", "dhuhr": "12:03", "asr": "15:23", "sunset": "17:45", "maghrib": "18:02", "isha": "18:52", "midnight": "23:22" },
    { "city_id": "kermanshah", "city_name": "کرمانشاه", "province": "کرمانشاه", "fajr": "05:06", "sunrise": "06:29", "dhuhr": "12:09", "asr": "15:26", "sunset": "17:48", "maghrib": "18:06", "isha": "18:57", "midnight": "23:27" },
    { "city_id": "sanandaj", "city_name": "سنندج", "province": "کردستان", "fajr": "05:06", "sunrise": "06:30", "dhuhr": "12:09", "asr": "15:25", "sunset": "17:48", "maghrib": "18:06", "isha": "18:58", "midnight": "23:27" },
    { "city_id": "zahedan", "city_name": "زاهدان", "province": "سیستان و بلوچستان", "fajr": "04:14", "sunrise": "05:33", "dhuhr": "11:15", "asr": "14:36", "sunset": "16:57", "maghrib": "17:14", "isha": "18:04", "midnight": "22:35" },
    { "city_id": "gorgan", "city_name": "گرگان", "province": "گلستان", "fajr": "04:41", "sunrise": "06:06", "dhuhr": "11:45", "asr": "15:00", "sunset": "17:24", "maghrib": "17:43", "isha": "18:36", "midnight": "23:03" },
    { "city_id": "urmia", "city_name": "ارومیه", "province": "آذربایجان غربی", "fajr": "05:12", "sunrise": "06:38", "dhuhr": "12:17", "asr": "15:31", "sunset": "17:55", "maghrib": "18:14", "isha": "19:07", "midnight": "23:34" }
]

def normalize_time_str(val: Any, default: str = "12:00") -> str:
    """Ensure time format is HH:MM (e.g. 4:48 -> 04:48)"""
    if val is None:
        return default
    s = str(val).strip()
    # Normalize Persian digits to English
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    for p, e in zip(persian_digits, english_digits):
        s = s.replace(p, e)
    
    parts = re.split(r'[:.]', s)
    if len(parts) >= 2:
        try:
            h = int(parts[0].strip())
            m = int(parts[1].strip()[:2])
            return f"{h:02d}:{m:02d}"
        except ValueError:
            pass
    return default

def slugify_city(name: str) -> str:
    """Generate safe identifier for city"""
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[-\s]+', '_', s)
    return s or "city_" + str(abs(hash(name)) % 10000)

class PrayerService:
    @staticmethod
    async def seed_default_cities(db: AsyncSession) -> int:
        """Seed 12 standard cities if table is empty"""
        stmt = select(func.count()).select_from(CityPrayerTime)
        result = await db.execute(stmt)
        count = result.scalar() or 0
        if count > 0:
            return count

        for item in DEFAULT_IRAN_CITIES:
            city = CityPrayerTime(
                city_id=item["city_id"],
                city_name=item["city_name"],
                province=item.get("province", ""),
                country="IR",
                fajr=item["fajr"],
                sunrise=item["sunrise"],
                dhuhr=item["dhuhr"],
                asr=item["asr"],
                sunset=item["sunset"],
                maghrib=item["maghrib"],
                isha=item["isha"],
                midnight=item["midnight"],
                source="default_seed"
            )
            db.add(city)
        await db.commit()
        return len(DEFAULT_IRAN_CITIES)

    @staticmethod
    async def get_all_cities(db: AsyncSession, search: Optional[str] = None, active_only: bool = True) -> List[CityPrayerTime]:
        query = select(CityPrayerTime)
        if active_only:
            query = query.where(CityPrayerTime.is_active == True)
        if search:
            s = f"%{search.strip()}%"
            query = query.where((CityPrayerTime.city_name.ilike(s)) | (CityPrayerTime.city_id.ilike(s)))
        query = query.order_by(CityPrayerTime.city_name)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_city(db: AsyncSession, city_id: str) -> Optional[CityPrayerTime]:
        result = await db.execute(select(CityPrayerTime).where(CityPrayerTime.city_id == city_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert_city(db: AsyncSession, city_data: Dict[str, Any], source: str = "manual") -> CityPrayerTime:
        c_id = city_data.get("city_id") or slugify_city(city_data.get("city_name", ""))
        existing = await PrayerService.get_city(db, c_id)
        if existing:
            for k, v in city_data.items():
                if hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            existing.source = source
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            new_city = CityPrayerTime(
                city_id=c_id,
                city_name=city_data.get("city_name", ""),
                province=city_data.get("province", ""),
                country=city_data.get("country", "IR"),
                fajr=normalize_time_str(city_data.get("fajr")),
                sunrise=normalize_time_str(city_data.get("sunrise")),
                dhuhr=normalize_time_str(city_data.get("dhuhr")),
                asr=normalize_time_str(city_data.get("asr")),
                sunset=normalize_time_str(city_data.get("sunset")),
                maghrib=normalize_time_str(city_data.get("maghrib")),
                isha=normalize_time_str(city_data.get("isha")),
                midnight=normalize_time_str(city_data.get("midnight")),
                calculation_method=city_data.get("calculation_method", "مؤسسه ژئوفیزیک دانشگاه تهران"),
                source=source,
                is_active=True
            )
            db.add(new_city)
            await db.commit()
            await db.refresh(new_city)
            return new_city

    @staticmethod
    async def delete_city(db: AsyncSession, city_id: str) -> bool:
        city = await PrayerService.get_city(db, city_id)
        if not city:
            return False
        await db.delete(city)
        await db.commit()
        return True

    @staticmethod
    async def reset_defaults(db: AsyncSession) -> int:
        """Clear and re-seed defaults"""
        await db.execute(delete(CityPrayerTime))
        for item in DEFAULT_IRAN_CITIES:
            city = CityPrayerTime(
                city_id=item["city_id"],
                city_name=item["city_name"],
                province=item.get("province", ""),
                country="IR",
                fajr=item["fajr"],
                sunrise=item["sunrise"],
                dhuhr=item["dhuhr"],
                asr=item["asr"],
                sunset=item["sunset"],
                maghrib=item["maghrib"],
                isha=item["isha"],
                midnight=item["midnight"],
                source="default_seed"
            )
            db.add(city)
        await db.commit()
        return len(DEFAULT_IRAN_CITIES)

    @staticmethod
    async def parse_and_upsert_json(db: AsyncSession, raw_data: Union[str, dict, list]) -> Dict[str, Any]:
        """
        Parses single or multi-city JSON payload. Supports:
        1. Array of city objects: [ {"city_id": "...", "fajr": "...", ...}, ... ]
        2. Dictionary of cities: { "tehran": { ... }, "mashhad": { ... } }
        3. Single city object: { "city_id": "...", ... }
        Handles Persian & English field aliases automatically.
        """
        if isinstance(raw_data, str):
            raw_data = raw_data.strip()
            if not raw_data:
                raise ValueError("محتوای JSON خالی است.")
            try:
                parsed = json.loads(raw_data)
            except json.JSONDecodeError as err:
                raise ValueError(f"خطا در ساختار JSON: {err.msg} در سطر {err.lineno}")
        else:
            parsed = raw_data

        # Normalize parsed into a list of city item dicts
        items_to_process = []
        if isinstance(parsed, list):
            items_to_process = parsed
        elif isinstance(parsed, dict):
            # Check if this is a single city object or a dictionary of cities
            has_prayer_keys = any(k in parsed for k in ["fajr", "dhuhr", "maghrib", "اذان صبح", "ظهر", "times"])
            if has_prayer_keys and ("city_id" in parsed or "city_name" in parsed or "name" in parsed):
                items_to_process = [parsed]
            else:
                # Key-value dictionary of cities: { "tehran": { ... }, "isfahan": { ... } }
                for k, v in parsed.items():
                    if isinstance(v, dict):
                        city_copy = dict(v)
                        if "city_id" not in city_copy:
                            city_copy["city_id"] = k
                        if "city_name" not in city_copy and "name" not in city_copy:
                            city_copy["city_name"] = k
                        items_to_process.append(city_copy)
                    elif isinstance(v, str):
                        # Simple format fallback
                        pass
        else:
            raise ValueError("فرمت JSON نامعتبر است؛ باید یک آبجکت یا آرایه از شهرها باشد.")

        if not items_to_process:
            raise ValueError("هیچ شهری در داده‌های ارسالی شناسایی نشد.")

        created_count = 0
        updated_count = 0
        processed_cities = []

        for raw_item in items_to_process:
            if not isinstance(raw_item, dict):
                continue

            # Extract sub-dictionary if nested under "times" or "prayers"
            times_dict = raw_item.get("times") or raw_item.get("prayers") or raw_item

            # Field extractors with Persian and English aliases
            def get_val(*keys, default=""):
                for k in keys:
                    if k in raw_item and raw_item[k] is not None:
                        return raw_item[k]
                    if k in times_dict and times_dict[k] is not None:
                        return times_dict[k]
                return default

            c_name = get_val("city_name", "city", "name", "شهر", "نام شهر", default="")
            c_id = get_val("city_id", "id", "slug", "شناسه", default="")

            if not c_name and not c_id:
                continue
            if not c_name and c_id:
                c_name = c_id.capitalize()
            if not c_id and c_name:
                c_id = slugify_city(c_name)

            fajr = normalize_time_str(get_val("fajr", "اذان صبح", "صبح", "imsak", default="04:45"))
            sunrise = normalize_time_str(get_val("sunrise", "طلوع آفتاب", "طلوع", default="06:10"))
            dhuhr = normalize_time_str(get_val("dhuhr", "noon", "اذان ظهر", "ظهر", default="11:50"))
            asr = normalize_time_str(get_val("asr", "اذان عصر", "عصر", default="15:05"))
            sunset = normalize_time_str(get_val("sunset", "غروب آفتاب", "غروب", default="17:30"))
            maghrib = normalize_time_str(get_val("maghrib", "اذان مغرب", "مغرب", default="17:48"))
            isha = normalize_time_str(get_val("isha", "اذان عشاء", "عشاء", default="18:40"))
            midnight = normalize_time_str(get_val("midnight", "نیمه شب", "نیمه‌شب شرعی", "نیمه‌شب", default="23:10"))

            province = get_val("province", "استان", default="")
            country = get_val("country", "کشور", default="IR")
            method = get_val("calculation_method", "method", "مبنا", default="مؤسسه ژئوفیزیک دانشگاه تهران")

            # Check if city already exists in DB
            existing = await PrayerService.get_city(db, c_id)
            if existing:
                existing.city_name = c_name
                existing.province = province or existing.province
                existing.country = country or existing.country
                existing.fajr = fajr
                existing.sunrise = sunrise
                existing.dhuhr = dhuhr
                existing.asr = asr
                existing.sunset = sunset
                existing.maghrib = maghrib
                existing.isha = isha
                existing.midnight = midnight
                existing.calculation_method = method
                existing.source = "admin_json"
                updated_count += 1
                processed_cities.append(existing.to_dict())
            else:
                new_city = CityPrayerTime(
                    city_id=c_id,
                    city_name=c_name,
                    province=province,
                    country=country,
                    fajr=fajr,
                    sunrise=sunrise,
                    dhuhr=dhuhr,
                    asr=asr,
                    sunset=sunset,
                    maghrib=maghrib,
                    isha=isha,
                    midnight=midnight,
                    calculation_method=method,
                    source="admin_json",
                    is_active=True
                )
                db.add(new_city)
                created_count += 1
                processed_cities.append(new_city.to_dict())

        await db.commit()

        return {
            "success": True,
            "total_processed": len(processed_cities),
            "created": created_count,
            "updated": updated_count,
            "cities": processed_cities
        }
