import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dhikr import Dhikr, DhikrCategory
from app.schemas.dhikr import DhikrCreate, DhikrUpdate, DhikrCategoryCreate


DEFAULT_CATEGORIES = [
    {
        "id": "daily",
        "title": "اذکار ایام هفته",
        "description": "ذکرهای ویژه هر یک از ایام هفته برای کسب برکت و گشایش",
        "icon": "calendar_month",
        "display_order": 1,
        "is_system": True
    },
    {
        "id": "taqibat",
        "title": "تعقیبات نماز و تسبیحات",
        "description": "تسبیحات حضرت فاطمه زهرا (س)، تسبیحات اربعه و تعقیبات پس از نمازهای یومیه",
        "icon": "mosque",
        "display_order": 2,
        "is_system": True
    },
    {
        "id": "hajat",
        "title": "حاجات و گشایش امور",
        "description": "اذکار مجرب برای رفع گرفتاری، وسعت رزق و استجابت دعا",
        "icon": "key",
        "display_order": 3,
        "is_system": True
    },
    {
        "id": "munajat",
        "title": "مناجات، سکینه و آرامش",
        "description": "اذکار دفع اضطراب، ایجاد آرامش باطنی و توکل بر خداوند متعال",
        "icon": "spa",
        "display_order": 4,
        "is_system": True
    },
    {
        "id": "ziyarat",
        "title": "ادعیه، زیارات و مهدویت",
        "description": "فرازهای منتخب دعایی، دعای فرج و توسلات معارفی",
        "icon": "auto_stories",
        "display_order": 5,
        "is_system": True
    },
    {
        "id": "custom",
        "title": "اذکار و دعاهای شخصی من",
        "description": "اذکار و دعاهایی که مستقیماً توسط خود کاربر افزوده شده است",
        "icon": "bookmark",
        "display_order": 6,
        "is_system": False
    }
]

DEFAULT_DHIKRS = [
    # 1. ایام هفته
    {
        "id": "dhikr_sat",
        "title": "ذکر روز شنبه",
        "arabic_text": "یَا رَبَّ الْعَالَمِینَ",
        "translation": "«ای پروردگار جهانیان»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب بی‌نیازی و فزونی مال و نعمت در سراسر هفته",
        "source": "مفاتیح الجنان و کتب ادعیه",
        "is_system": True
    },
    {
        "id": "dhikr_sun",
        "title": "ذکر روز یکشنبه",
        "arabic_text": "یَا ذَا الْجَلَالِ وَ الْإِکْرَامِ",
        "translation": "«ای صاحب شکوه و بزرگواری و کرامت»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب فتح و نصرت و جلب محبت قلوب",
        "source": "مفاتیح الجنان",
        "is_system": True
    },
    {
        "id": "dhikr_mon",
        "title": "ذکر روز دوشنبه",
        "arabic_text": "یَا قَاضِیَ الْحَاجَاتِ",
        "translation": "«ای برآورنده حاجات و نیازمندی‌ها»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب فزونی مال و گشایش در کارهای فرو بسته",
        "source": "مفاتیح الجنان",
        "is_system": True
    },
    {
        "id": "dhikr_tue",
        "title": "ذکر روز سه‌شنبه",
        "arabic_text": "یَا أَرْحَمَ الرَّاحِمِینَ",
        "translation": "«ای مهربان‌ترین مهربانان»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب جلب رحمت واسعه الهی و آمرزش گناهان",
        "source": "مفاتیح الجنان",
        "is_system": True
    },
    {
        "id": "dhikr_wed",
        "title": "ذکر روز چهارشنبه",
        "arabic_text": "یَا حَیُّ یَا قَیُّومُ",
        "translation": "«ای زنده همیشگی و برپادارنده هستی»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب عزت، شکوه و بیداری باطن",
        "source": "مفاتیح الجنان",
        "is_system": True
    },
    {
        "id": "dhikr_thu",
        "title": "ذکر روز پنج‌شنبه",
        "arabic_text": "لَا إِلٰهَ إِلَّا اللهُ الْمَلِکُ الْحَقُّ الْمُبِینُ",
        "translation": "«معبودی جز خدای یگانه نیست که پادشاه حق و آشکار است»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "موجب بی‌نیازی از خلق، ایمنی از وحشت قبر و درهای بهشت",
        "source": "خصال شیخ صدوق و مفاتیح الجنان",
        "is_system": True
    },
    {
        "id": "dhikr_fri",
        "title": "ذکر روز جمعه",
        "arabic_text": "اَللّٰهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ وَآلِ مُحَمَّدٍ وَعَجِّلْ فَرَجَهُمْ",
        "translation": "«بار خدایا بر محمد و آل محمد درود فرست و در فرج آنان تعجیل فرما»",
        "category": "daily",
        "category_title": "اذکار ایام هفته",
        "target_count": 100,
        "virtue": "محبوب‌ترین عمل در روز جمعه و کفاره گناهان",
        "source": "کافی شریف و روایات فریقین",
        "is_system": True
    },

    # 2. تعقیبات نماز و تسبیحات
    {
        "id": "dhikr_zahra",
        "title": "تسبیحات حضرت فاطمه زهرا (س)",
        "arabic_text": "اَللهُ اَکْبَرُ (۳۴) • اَلْحَمْدُ لِلَّهِ (۳۳) • سُبْحَانَ اللَّهِ (۳۳)",
        "translation": "«خدا بزرگ‌تر از وصف است • ستایش مخصوص خداست • منزه است پروردگار»",
        "category": "taqibat",
        "category_title": "تعقیبات نماز و تسبیحات",
        "target_count": 100,
        "virtue": "امام صادق (ع): تسبیح فاطمه زهرا (س) بعد از هر نماز نزد من از هزار رکعت نماز مستحبی محبوب‌تر است.",
        "source": "کافی شریف، ج ۳، ص ۳۴۳",
        "is_system": True
    },
    {
        "id": "dhikr_tasbihat_arba",
        "title": "تسبیحات اربعه",
        "arabic_text": "سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ وَلَا إِلٰهَ إِلَّا اللَّهُ وَاللَّهُ أَکْبَرُ",
        "translation": "«پاک و منزه است خداوند و سپاس ویژه اوست و خدایی جز او نیست و خدا برتر از وصف است»",
        "category": "taqibat",
        "category_title": "تعقیبات نماز و تسبیحات",
        "target_count": 30,
        "virtue": "کفاره گناهان و باقیات صالحات ذکر شده در قرآن کریم",
        "source": "بحارالانوار و سنن ترمذی",
        "is_system": True
    },
    {
        "id": "dhikr_ayat_al_kursi",
        "title": "آیة الکرسی شریف",
        "arabic_text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ...",
        "translation": "«خداست که معبودی جز او نیست؛ زنده و برپادارنده است؛ نه خوابی سبک او را فرو می‌گیرد و نه خوابی گران...»",
        "category": "taqibat",
        "category_title": "تعقیبات نماز و تسبیحات",
        "target_count": 1,
        "virtue": "پیامبر اکرم (ص): هر کس بعد از هر نماز واجب آیة الکرسی بخواند، چیزی جز مرگ مانع بهشت رفتن او نیست.",
        "source": "سوره بقره، آیات ۲۵۵ تا ۲۵۷",
        "is_system": True
    },

    # 3. حاجات و گشایش امور
    {
        "id": "dhikr_younisiyeh",
        "title": "ذکر شریف یونسیه",
        "arabic_text": "لَّا إِلَٰهَ إِلَّا أَنتَ سُبْحَانَكَ إِنِّي كُنتُ مِنَ الظَّالِمِينَ",
        "translation": "«هیچ معبودی جز تو نیست، پاک و منزه‌ای تو؛ به راستی که من از ستمکاران بر خود بودم»",
        "category": "hajat",
        "category_title": "حاجات و گشایش امور",
        "target_count": 400,
        "virtue": "قرآن کریم: و این‌گونه مؤمنان را از اندوه و غم نجات می‌بخشیم (سوره انبیاء)",
        "source": "سوره انبیاء، آیه ۸۷",
        "is_system": True
    },
    {
        "id": "dhikr_istighfar",
        "title": "استغفار و طلب آمرزش",
        "arabic_text": "أَسْتَغْفِرُ اللَّهَ رَبِّي وَأَتُوبُ إِلَيْهِ",
        "translation": "«از خداوند که پروردگار من است آمرزش می‌طلبم و به سوی او بازمی‌گردم»",
        "category": "hajat",
        "category_title": "حاجات و گشایش امور",
        "target_count": 70,
        "virtue": "موجب وسعت رزق، تولد فرزندان صالح، پاکی دل و باران رحمت",
        "source": "سوره نوح و روایات نبوی",
        "is_system": True
    },
    {
        "id": "dhikr_salawat_kabir",
        "title": "صلوات جامع و ابراهیمی",
        "arabic_text": "اَللّٰهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ وَعَلَىٰ آلِ مُحَمَّدٍ كَمَا صَلَّيْتَ عَلَىٰ إِبْرَاهِيمَ وَعَلَىٰ آلِ إِبْرَاهِيمَ إِنَّكَ حَمِيدٌ مَجِيدٌ",
        "translation": "«خدایا درود فرست بر محمد و آل محمد چنان که بر ابراهیم و آل ابراهیم درود فرستادی، همانا تو ستوده‌ای و بزرگواری»",
        "category": "hajat",
        "category_title": "حاجات و گشایش امور",
        "target_count": 100,
        "virtue": "صیغه اجماعی صلوات میان فریقین شیعه و اهل سنت و کلید برآورده شدن جمیع حاجات",
        "source": "صحیح بخاری و کافی شریف",
        "is_system": True
    },

    # 4. مناجات و آرامش
    {
        "id": "dhikr_hawqala",
        "title": "حوقله (لا حول ولا قوة الا بالله)",
        "arabic_text": "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ الْعَلِیِّ الْعَظِیمِ",
        "translation": "«هیچ نیرو و توانی نیست مگر از جانب خدای والامقام و بزرگ‌مرتبه»",
        "category": "munajat",
        "category_title": "مناجات، سکینه و آرامش",
        "target_count": 100,
        "virtue": "دفع هفتاد نوع بلا که کمترین آن غم و اندوه است؛ گنجی از گنج‌های بهشت",
        "source": "امالی شیخ طوسی و صحاح اهل سنت",
        "is_system": True
    },
    {
        "id": "dhikr_hasbuna",
        "title": "ذکر توکل و ایمنی",
        "arabic_text": "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ نِعْمَ الْمَوْلَىٰ وَنِعْمَ النَّصِيرُ",
        "translation": "«خدا ما را بس است و او بهترین کارساز و چه نیکو سرپرست و چه نیکو یاوری است»",
        "category": "munajat",
        "category_title": "مناجات، سکینه و آرامش",
        "target_count": 100,
        "virtue": "دفع ترس، اضطراب و توطئه دشمنان (سیره حضرت ابراهیم و پیامبر خاتم)",
        "source": "سوره آل‌عمران، آیه ۱۷۳",
        "is_system": True
    },

    # 5. ادعیه و مهدویت
    {
        "id": "dhikr_faraj",
        "title": "دعای شریف فرج (الهی عظم البلاء)",
        "arabic_text": "إِلَهِي عَظُمَ الْبَلاءُ وَ بَرِحَ الْخَفَاءُ وَ انْكَشَفَ الْغِطَاءُ وَ انْقَطَعَ الرَّجَاءُ...",
        "translation": "«خدایا بلا و گرفتاری بزرگ شد و پوشیده آشکار گشت و پرده برافتاد و امیدها بریده شد...»",
        "category": "ziyarat",
        "category_title": "ادعیه، زیارات و مهدویت",
        "target_count": 1,
        "virtue": "تعلیم داده شده توسط امام عصر (عج) به محمد بن احمد بن ابی لیث در مسجد کوفه برای نجات از مهلکه",
        "source": "جمال الاسبوع سید بن طاووس",
        "is_system": True
    }
]


class DhikrService:

    @classmethod
    async def seed_defaults(cls, db: AsyncSession):
        # 1. Seed categories
        for cat_data in DEFAULT_CATEGORIES:
            existing = await db.get(DhikrCategory, cat_data["id"])
            if not existing:
                cat = DhikrCategory(**cat_data)
                db.add(cat)

        # 2. Seed dhikrs
        for d_data in DEFAULT_DHIKRS:
            existing = await db.get(Dhikr, d_data["id"])
            if not existing:
                dhikr = Dhikr(**d_data)
                db.add(dhikr)

        await db.commit()

    @classmethod
    async def get_categories(cls, db: AsyncSession) -> List[DhikrCategory]:
        # Ensure default categories seeded
        cat_count = (await db.execute(select(DhikrCategory))).scalars().all()
        if not cat_count:
            await cls.seed_defaults(db)

        stmt = select(DhikrCategory).order_by(DhikrCategory.display_order.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def create_category(
        cls,
        db: AsyncSession,
        payload: DhikrCategoryCreate,
        is_system: bool = True
    ) -> DhikrCategory:
        cat_id = payload.id.strip().lower() if payload.id else f"cat_{uuid.uuid4().hex[:8]}"
        existing = await db.get(DhikrCategory, cat_id)
        if existing:
            existing.title = payload.title
            existing.description = payload.description
            existing.icon = payload.icon or existing.icon
            existing.display_order = payload.display_order or existing.display_order
            await db.commit()
            await db.refresh(existing)
            return existing

        new_cat = DhikrCategory(
            id=cat_id,
            title=payload.title,
            description=payload.description or "",
            icon=payload.icon or "counter_3",
            display_order=payload.display_order or 0,
            is_system=is_system
        )
        db.add(new_cat)
        await db.commit()
        await db.refresh(new_cat)
        return new_cat


    @classmethod
    async def get_dhikrs(
        cls,
        db: AsyncSession,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        is_system: Optional[bool] = None
    ) -> List[Dhikr]:
        # Ensure seed data exists
        count = (await db.execute(select(Dhikr))).scalars().all()
        if not count:
            await cls.seed_defaults(db)

        stmt = select(Dhikr)

        conditions = []
        if category and category != "all":
            conditions.append(Dhikr.category == category)

        if is_system is not None:
            conditions.append(Dhikr.is_system == is_system)
        else:
            # By default return all system dhikrs + current user's custom dhikrs
            if user_id:
                conditions.append(or_(Dhikr.is_system == True, Dhikr.user_id == user_id))
            else:
                conditions.append(or_(Dhikr.is_system == True, Dhikr.user_id != None))

        if search:
            s = f"%{search.strip().lower()}%"
            conditions.append(or_(
                Dhikr.title.ilike(s),
                Dhikr.arabic_text.ilike(s),
                Dhikr.translation.ilike(s),
                Dhikr.category_title.ilike(s)
            ))

        if conditions:
            stmt = stmt.where(*conditions)

        stmt = stmt.order_by(Dhikr.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_dhikr(cls, db: AsyncSession, dhikr_id: str) -> Optional[Dhikr]:
        return await db.get(Dhikr, dhikr_id)

    @classmethod
    async def create_dhikr(
        cls,
        db: AsyncSession,
        payload: DhikrCreate,
        user_id: Optional[str] = None,
        is_system: bool = False
    ) -> Dhikr:
        # Resolve category title
        category_title = payload.category_title
        if not category_title:
            cat = await db.get(DhikrCategory, payload.category)
            category_title = cat.title if cat else "اذکار و ادعیه"

        # If category does not exist, create it automatically
        cat_obj = await db.get(DhikrCategory, payload.category)
        if not cat_obj:
            cat_obj = DhikrCategory(
                id=payload.category,
                title=category_title,
                icon="counter_3",
                display_order=99,
                is_system=is_system
            )
            db.add(cat_obj)

        dhikr = Dhikr(
            id=f"dhikr_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            arabic_text=payload.arabic_text,
            translation=payload.translation or "",
            category=payload.category,
            category_title=category_title,
            target_count=payload.target_count or 100,
            virtue=payload.virtue or "",
            source=payload.source or ("افزوده شده توسط کاربر" if not is_system else "مأخذ روایی"),
            is_system=is_system,
            user_id=user_id
        )
        db.add(dhikr)
        await db.commit()
        await db.refresh(dhikr)
        return dhikr

    @classmethod
    async def update_dhikr(
        cls,
        db: AsyncSession,
        dhikr_id: str,
        payload: DhikrUpdate
    ) -> Optional[Dhikr]:
        dhikr = await db.get(Dhikr, dhikr_id)
        if not dhikr:
            return None

        if payload.title is not None:
            dhikr.title = payload.title
        if payload.arabic_text is not None:
            dhikr.arabic_text = payload.arabic_text
        if payload.translation is not None:
            dhikr.translation = payload.translation
        if payload.category is not None:
            dhikr.category = payload.category
        if payload.category_title is not None:
            dhikr.category_title = payload.category_title
        if payload.target_count is not None:
            dhikr.target_count = payload.target_count
        if payload.virtue is not None:
            dhikr.virtue = payload.virtue
        if payload.source is not None:
            dhikr.source = payload.source

        await db.commit()
        await db.refresh(dhikr)
        return dhikr

    @classmethod
    async def delete_dhikr(
        cls,
        db: AsyncSession,
        dhikr_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        dhikr = await db.get(Dhikr, dhikr_id)
        if not dhikr:
            return False

        # If not admin, user can only delete their own custom dhikrs
        if not is_admin and dhikr.is_system:
            return False
        if not is_admin and user_id and dhikr.user_id != user_id:
            return False

        await db.delete(dhikr)
        await db.commit()
        return True
