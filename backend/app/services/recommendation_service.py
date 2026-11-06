import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.scholar import Scholar
from app.db.models.library import Book

logger = logging.getLogger(__name__)


# Built-in scholar profiles as resilient fallback
FALLBACK_SCHOLARS = [
    {
        "id": "scholar_1",
        "name": "حجت‌الاسلام دکتر محمدرضا عابدی",
        "title": "استاد سطوح عالی حوزه علمیه و دکترای فقه و حقوق",
        "specialties": ["احکام شرعی و فقهی", "معاملات و بورس", "مسائل نوین پزشکی"],
        "keywords": ["بورس", "سهام", "معاملات", "ارز دیجیتال", "بیت کوین", "ارزدیجیتال", "خرید و فروش", "ربا", "بانک", "سود بانکی", "پزشکی", "سقط", "پیوند اعضا", "واکسن", "شبیه سازی", "خمس", "زکات", "وضو", "غسل", "نماز", "روزه", "کفاره", "شکیات", "طهارت", "نجاست", "مطهره", "ارث", "وصیت", "حلال", "حرام"],
        "match_reason": "با توجه به تخصص در فقه معاملات، احکام مستحدثه بورس و مسائل نوین پزشکی",
        "actionUrl": "scholar_chat.html?scholarId=scholar_1"
    },
    {
        "id": "scholar_2",
        "name": "ماموستا دکتر صلاح‌الدین محمدی",
        "title": "مدرس دارالافتاء و استاد فقه شافعی دانشگاه مذاهب",
        "specialties": ["احکام شرعی و فقهی", "مشاوره و خانواده", "تفسیر و معارف قرآن"],
        "keywords": ["خانواده", "ازدواج", "همسر", "شوهر", "زن", "طلاق", "مهریه", "نفقه", "خواستگاری", "حضانت", "شافعی", "ماموستا", "اهل سنت", "کردستان", "تسنن", "تقریب", "وحدت"],
        "match_reason": "با توجه به تخصص در فقه شافعی دانشگاه مذاهب و مشاوره مسائل خانواده",
        "actionUrl": "scholar_chat.html?scholarId=scholar_2"
    },
    {
        "id": "scholar_3",
        "name": "مولوی عبدالکریم آخوند گرگانی",
        "title": "مدیر حوزه علمیه و مفتی اهل سنت (حنفی)",
        "specialties": ["احکام شرعی و فقهی", "اعتقادی و کلامی", "اخلاق و سیر و سلوک"],
        "keywords": ["حنفی", "ابوحنیفه", "مولوی", "ترکمن", "سیستان", "بلوچستان", "گلستان", "سنت", "فتوا", "مفتی", "فقه حنفی"],
        "match_reason": "به عنوان مفتی ارشد اهل سنت (حنفی) با تسلط بر فتاوای فقهی و سیر و سلوک اخلاقی",
        "actionUrl": "scholar_chat.html?scholarId=scholar_3"
    },
    {
        "id": "scholar_4",
        "name": "آیت‌الله سید مرتضی علوی حسینی",
        "title": "استاد درس خارج فقه و اصول و عضو مجمع عالی حکمت",
        "specialties": ["اعتقادی و کلامی", "اخلاق و سیر و سلوک", "تفسیر و معارف قرآن"],
        "keywords": ["خدا", "اثبات صانع", "توحید", "امامت", "معاد", "نبوت", "کلام", "فلسفه", "حکمت", "عقل", "برهان", "علت و معلول", "شرور", "قضا و قدر", "شبهه", "تطبیق", "غدیر", "عصمت", "ولایت", "اصول دین"],
        "match_reason": "با توجه به عضویت در مجمع عالی حکمت و تبحر در مبانی کلامی و فلسفه برهانی",
        "actionUrl": "scholar_chat.html?scholarId=scholar_4"
    },
    {
        "id": "scholar_5",
        "name": "حجت‌الاسلام دکتر علیرضا پناهی",
        "title": "دکترای روانشناسی اسلامی و مشاور ارشد فقه تربیتی",
        "specialties": ["مشاوره و خانواده", "اخلاق و سیر و سلوک"],
        "keywords": ["روانشناسی", "افسردگی", "اضطراب", "استرس", "وسواس", "تربیت", "فرزند", "کودک", "نوجوان", "مشاوره", "آرامش", "صبر", "خشم", "حسد", "کبر", "غرور", "تهذیب نفس", "سیر و سلوک", "اخلاق"],
        "match_reason": "به عنوان متخصص روانشناسی اسلامی و مشاور ارشد فقه تربیتی در زمینه پرسش شما",
        "actionUrl": "scholar_chat.html?scholarId=scholar_5"
    },
    {
        "id": "scholar_6",
        "name": "شیخ احمد عبدالملکی",
        "title": "مدرس علوم قرآن و حدیث دارالعلم شیراز",
        "specialties": ["تفسیر و معارف قرآن", "اعتقادی و کلامی"],
        "keywords": ["قرآن", "تفسیر", "آیه", "سوره", "شان نزول", "شأن نزول", "تدبر", "مصحف", "تجوید", "قرائت", "قصص قرآن", "حدیث", "روایت", "رجال", "صحاح", "اصول کافی"],
        "match_reason": "با توجه به تخصص در تفسیر ترتیبی و موضوعی قرآن کریم و سنن روایی فریقین",
        "actionUrl": "scholar_chat.html?scholarId=scholar_6"
    }
]

# Built-in books matching theological topics
FALLBACK_BOOKS = [
    {
        "id": "tafsir_mizan",
        "title": "تفسیر المیزان فی تفسیر القرآن",
        "author": "علامه سید محمدحسین طباطبایی",
        "categoryTitle": "تفسیر و علوم قرآن",
        "keywords": ["قرآن", "تفسیر", "آیه", "سوره", "سید محمدحسین طباطبایی", "علامه", "قرآن به قرآن", "فلسفی", "اجتماعی"],
        "match_reason": "مرجع جامع تفسیر قرآن به قرآن و تبیین عقلانی آیات متناسب با پرسش قرآنی شما",
        "actionUrl": "book-reader.html?book=tafsir_mizan"
    },
    {
        "id": "kashf_al_murad",
        "title": "کشف المراد فی شرح تجرید الاعتقاد",
        "author": "علامه حلی / خواجه نصیرالدین طوسی",
        "categoryTitle": "کلام و عقاید اسلامی",
        "keywords": ["اثبات صانع", "توحید", "صفات خدا", "امامت", "معاد", "نبوت", "کلام", "فلسفه", "عقل", "برهان", "شبهه"],
        "match_reason": "بررسی براهین متقن عقلی و کلامی پیرامون مبانی توحید و اعتقادات در پاسخ به پرسش",
        "actionUrl": "book-reader.html?book=kashf_al_murad"
    },
    {
        "id": "nahj_al_balaghah",
        "title": "نهج‌البلاغه (نسخه تحقیقی جامع)",
        "author": "امیرالمؤمنین علی بن ابی‌طالب (ع) / سید رضی",
        "categoryTitle": "حدیث و حکمت علوی",
        "keywords": ["عدالت", "حکومت", "سیاست", "حقوق مردم", "مالک اشتر", "خطبه", "نامه", "حکمت", "پرهیزگاران", "همام", "تقوا", "وحدت"],
        "match_reason": "تبیین منشور حکمرانی عادلانه، تقوا و مکارم اخلاقی در کلام امیرالمؤمنین (ع)",
        "actionUrl": "book-reader.html?book=nahj_al_balaghah"
    },
    {
        "id": "book_forty_hadith",
        "title": "چهل حدیث اخلاقی و معنوی",
        "author": "محدث نوری و جمعی از پژوهشگران",
        "categoryTitle": "اخلاق و سیر و سلوک",
        "keywords": ["اخلاق", "تربیت", "روانشناسی", "وسواس", "تهذیب نفس", "کبر", "ریا", "صبر", "اخلاص", "آرامش", "برادری"],
        "match_reason": "راهکارهای عملی تهذیب نفس، برادری دینی و اصلاح رذایل اخلاقی متناسب با سوال",
        "actionUrl": "book-reader.html?book=book_forty_hadith"
    },
    {
        "id": "al_fiqh_ala_madhahib",
        "title": "الفقه علی المذاهب الخمسة",
        "author": "شیخ محمدجواد مغنیه",
        "categoryTitle": "فقه و احکام مقارن",
        "keywords": ["فقه", "احکام", "مذاهب", "معاملات", "بورس", "خمس", "زکات", "نماز", "روزه", "طهارت", "حلال", "حرام", "شافعی", "حنفی", "جعفری"],
        "match_reason": "بررسی مقایسه‌ای فتاوا و احکام فقهی مذاهب خمسه اسلامی پیرامون این موضوع",
        "actionUrl": "book-reader.html?book=al_fiqh_ala_madhahib"
    },
    {
        "id": "tafsir_munir",
        "title": "التفسیر المنیر فی العقیدة و الشریعة و المنهج",
        "author": "دکتر وهبه بن مصطفی الزحیلی",
        "categoryTitle": "تفسیر و فقه مقارن",
        "keywords": ["خانواده", "ازدواج", "طلاق", "حقوق زن", "مهریه", "تربیت", "اهل سنت", "شافعی", "شریعت"],
        "match_reason": "تبیین احکام شریعت و نظام خانواده اسلامی با رویکرد معاصر و تقریبی",
        "actionUrl": "book-reader.html?book=tafsir_munir"
    },
    {
        "id": "sahih_bukhari",
        "title": "صحیح البخاری (الجامع المسند الصحیح)",
        "author": "امام محمد بن اسماعیل بخاری",
        "categoryTitle": "حدیث و روایات فریقین",
        "keywords": ["سنت", "روایت", "حدیث نبوی", "پیامبر", "صحابه", "سیره", "اهل سنت"],
        "match_reason": "مهم‌ترین مرجع روایی اهل سنت متضمن احادیث صحیح نبوی پیرامون موضوع سوال",
        "actionUrl": "book-reader.html?book=sahih_bukhari"
    },
    {
        "id": "mafatih_al_jinan",
        "title": "مفاتیح الجنان و ادعیه معتبر فریقین",
        "author": "شیخ عباس قمی",
        "categoryTitle": "ادعیه و مناجات معارفی",
        "keywords": ["دعا", "ذکر", "مناجات", "زیارت", "تسبیح", "استجابت", "توسل", "ارتباط با خدا", "صلوات"],
        "match_reason": "جامع‌ترین کتاب ادعیه و مناجات‌های مأثور برای استجابت و آرامش روحی",
        "actionUrl": "book-reader.html?book=mafatih_al_jinan"
    },
    {
        "id": "bk_misc_adhkar",
        "title": "الأذكار المنتخبة من كلام سيد الأبرار",
        "author": "الإمام يحيى بن شرف النووي",
        "categoryTitle": "اخلاق، ادعیه و اذکار نبوی",
        "keywords": ["دعا", "ذکر", "اذکار", "ادعیه", "آرامش", "استرس", "اضطراب", "صبح", "شب", "نووی", "حدیث", "روایت", "سنت نبوی", "پناه بردن", "حفظ و امان", "ذکر روزمره", "کتاب دعا", "کتاب دعای معتبر", "کتاب برای اضطراب", "کتاب روایی"],
        "match_reason": "جامع‌ترین کتاب مأثور اذکار و ادعیه روزمره پیامبر اکرم (ص) برای دفع اضطراب و کسب آرامش روحی",
        "actionUrl": "book-reader.html?book=bk_misc_adhkar"
    },
    {
        "id": "bk_fiqh_bidayat",
        "title": "بداية المجتهد ونهاية المقتصد (فقه مقارن)",
        "author": "ابن رشد الحفيد (محمد بن أحمد القرطبي)",
        "categoryTitle": "فقه مقارن و تطبیقی",
        "keywords": ["اختلاف", "مذاهب", "فقه مقارن", "ابن رشد", "تفاوت نظر", "اصول فقه", "ادله", "فقه تطبیقی", "چرا اختلاف", "علت اختلاف", "دانشمندان فقهی", "ادله احکام", "کتاب فقه مقارن", "کتاب علمی و مقایسه‌ای", "تفاوت برداشت"],
        "match_reason": "شاهکار فقه مقارن و تطبیقی جهان اسلام برای فهم علمی، مستند و بی‌طرفانه ریشه‌های تفاوت فتاوا میان مذاهب",
        "actionUrl": "book-reader.html?book=bk_fiqh_bidayat"
    },
    {
        "id": "bk_tafsir_jalalayn",
        "title": "تفسير الجلالين",
        "author": "جلال الدين المحلي وجلال الدين السيوطي",
        "categoryTitle": "تفسیر و علوم قرآن",
        "keywords": ["تفسیر", "تفسیر خلاصه", "تفسیر روان", "آیه به آیه", "کلمه به کلمه", "جلالین", "سیوطی", "قرآن", "تفسیر دم دست", "تفسیر کوتاه", "معنی سوره", "تفسیر سوره به سوره", "تفسیر فشرده"],
        "match_reason": "معروف‌ترین و معتبرترین تفسیر فشرده، دقیق، واژگانی و سطر به سطر آیات قرآن کریم",
        "actionUrl": "book-reader.html?book=bk_tafsir_jalalayn"
    },
    {
        "id": "bk_hadith_nawawi40",
        "title": "الأربعون النووية في الأحاديث الصحيحة النبوية",
        "author": "الإمام يحيى بن شرف النووي",
        "categoryTitle": "حدیث و سنت نبوی",
        "keywords": ["اربعین", "چهل حدیث", "نیت", "اخلاص", "نووی", "حدیث نبوی", "ارکان دین", "احسان", "حدیث جبرائیل", "مبانی اسلام", "شریعت"],
        "match_reason": "چهل حدیث برگزیده و بنیادین از رسول اکرم (ص) پیرامون نیت، ارکان ایمان و اخلاق",
        "actionUrl": "book-reader.html?book=bk_hadith_nawawi40"
    },
    {
        "id": "bk_hadith_riyad",
        "title": "رياض الصالحين من حديث سيد المرسلين",
        "author": "الإمام يحيى بن شرف النووي",
        "categoryTitle": "اخلاق و سیر و سلوک",
        "keywords": ["ریاض الصالحین", "صبر", "شکر", "تقوا", "حسن خلق", "تربیت نفس", "معاشرت", "اخلاق اسلامی", "سلوک", "توسری خوری", "انفعال"],
        "match_reason": "مرجع کاربردی تهذیب نفس، صبر جمیل، شکر و آداب معاشرت نیکو با مردم بر اساس احادیث نبوی",
        "actionUrl": "book-reader.html?book=bk_hadith_riyad"
    },
    {
        "id": "bk_fiqh_quduri",
        "title": "مختصر القدوري في الفقه الحنفي",
        "author": "أبو الحسين أحمد بن محمد القدوري",
        "categoryTitle": "فقه و احکام حنفی",
        "keywords": ["حنفی", "ابوحنیفه", "قدوری", "مختصر القدوری", "طهارت", "وضو حنفی", "نماز حنفی", "احکام اهل سنت", "فقه حنفی", "الکتاب", "مسح سر حنفی"],
        "match_reason": "متن درسی و کتاب معیار فقه احناف در تبیین فتاوای مذهب ابوحنیفه",
        "actionUrl": "book-reader.html?book=bk_fiqh_quduri"
    },
    {
        "id": "bk_fiqh_sharai",
        "title": "شرائع الإسلام في مسائل الحلال والحرام",
        "author": "المحقق الحلي (جعفر بن الحسن)",
        "categoryTitle": "فقه و احکام جعفری",
        "keywords": ["جعفری", "شیعه", "امامیه", "محقق حلی", "شرائع الاسلام", "قضاوت", "قاضی", "دادگاه", "احکام امامیه", "روزه", "صوم", "صفات قاضی"],
        "match_reason": "دقیق‌ترین مرجع فقه استدلالی و فتوایی شیعه امامیه در ابواب قضاوت، عبادات و معاملات",
        "actionUrl": "book-reader.html?book=bk_fiqh_sharai"
    },
    {
        "id": "bk_tafsir_saddi",
        "title": "تيسير الكريم الرحمن في تفسير كلام المنان (تفسير السعدي)",
        "author": "الشيخ عبد الرحمن بن ناصر السعدي",
        "categoryTitle": "تفسیر و معارف قرآن",
        "keywords": ["سعدی", "تفسیر سعدی", "اخوت", "برادری", "صمد", "حجرات", "اخلاق قرآنی", "توحید", "تربیت قرآنی", "مسلمون واقعی", "نیش زبان"],
        "match_reason": "تفسیری شیوا و تربیتی با محوریت برادری ایمانی، توحید ناب و مکارم اخلاقی قرآن",
        "actionUrl": "book-reader.html?book=bk_tafsir_saddi"
    }
]


class RecommendationService:
    """
    Intelligent Contextual Recommender & Intent Router:
    Analyzes user queries to determine whether:
    1. AI is fully capable and self-sufficient (direct conversational / educational answer)
    2. Escalation / referral to an Islamic Scholar (عالم دینی / مشاور فقهی) is truly needed
    3. Reference Library Book (کتاب مرجع معارفی) should be introduced for further reading
    4. Or both / neither are required.
    """

    GREETINGS_PATTERN = re.compile(
        r"^(سلام|درود|سلام\s*علیکم|سلام\s*علیک|وقت\s*بخیر|صبح\s*بخیر|عصر\s*بخیر|شب\s*بخیر|روز\s*بخیر|"
        r"خوبی|چطوری|حالت\s*چطوره|اوضاعت\s*چطوره|چه\s*خبر|احوال\s*شما|خوش\s*آمدی|"
        r"ممنون|متشکرم|تشکر|دستت\s*درد\s*نکنه|سپاس|سپاسگزارم|مرسی|خیلی\s*ممنون|"
        r"خداحافظ|خداحافظی|فعلا|بای|التماس\s*دعا|یا\s*علی|"
        r"تو\s*کی\s*هستی|اسمت\s*چیه|چه\s*کاری\s*بلدی|وظیفت\s*چیه|خودتو\s*معرفی\s*کن|دستیار)",
        re.IGNORECASE
    )

    EXPLICIT_SCHOLAR_WORDS = [
        "عالم", "استاد", "شیخ", "ماموستا", "مولوی", "آیت‌الله", "آیت الله", "روحانی",
        "مشاور", "مشاوره", "مشورت", "استفتاء", "استفتا", "فتوا", "فتوای", "مقلد", "تقلید",
        "مرجع تقلید", "فقیه", "مفتی", "مسئله شرعی", "به عالم وصل کن", "وصل به عالم",
        "ارتباط با کارشناس", "ارتباط با مشاور", "معرفی استاد", "معرفی عالم"
    ]

    COMPLEX_FIQH_CRITICAL_WORDS = [
        "بیت کوین", "ارز دیجیتال", "ارزدیجیتال", "رمزارز", "اتریوم", "بورس", "فارکس",
        "معاملات آتی", "اهرم", "سود بانکی", "ربا", "سپرده بانکی", "سقط جنین", "تغییر جنسیت",
        "شبیه سازی", "پیوند اعضا", "اهدای عضو", "مرگ مغزی", "ارث", "طلاق", "جدایی",
        "خیانت", "حضانت", "وسواس شدید", "اختلال وسواس", "شبهه الحادی", "شبهه کلامی",
        "طلاق گرفتیم", "صیغه طلاق", "باطل شده", "وسواس فکری", "وسواس عملی", "مهریه", "حضانت فرزند"
    ]

    EXPLICIT_BOOK_WORDS = [
        "کتاب", "کتب", "کتابخانه", "کتابخوان", "تفسیر", "کتابی", "منبع", "منابع",
        "مأخذ", "مراجع", "مطالعه بیشتر", "رفرنس", "کتاب معرفی کن", "چه کتابی", "کتابهای",
        "کدام کتاب", "مطالعه کنم", "فهرست منابع", "کتاب معتبر",
        "یه کتاب", "یک کتاب", "کتابی برای", "منبعی برای", "کتاب دعای", "کتاب روایی", "کتابی هست", "تفسیر خلاصه", "تفسیر روان", "کتاب فقه"
    ]

    ROUTINE_EDUCATIONAL_WORDS = [
        "معنی", "مفهوم", "تعریف", "ارکان نماز", "واجبات نماز", "شمار رکعات", "اصول دین",
        "فروع دین", "پیامبران اولوالعزم", "چهارده معصوم", "سوره های قرآن", "ترجمه آیه",
        "وضو چگونه است", "ترتیب غسل", "آیه الکرسی", "معنی تقوا"
    ]

    @staticmethod
    def _matches_phrase(phrase: str, text: str) -> bool:
        """
        Safe phrase/keyword matcher preventing substring collisions
        (e.g. 'ربا' inside 'درباره').
        """
        p = phrase.strip().lower()
        if not p:
            return False
        if " " not in p:
            pattern = rf"(?:^|[^\w\u0600-\u06FF]){re.escape(p)}(?:$|[^\w\u0600-\u06FF])"
            return bool(re.search(pattern, text))
        return p in text

    @classmethod
    def assess_intent_and_routing_needs(
        cls,
        query: str,
        target_scholar_id: Optional[str] = None,
        target_book_id: Optional[str] = None,
        force_scholar_escalation: bool = False,
        rag_sufficient: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Determines if the query genuinely requires a human scholar or book reference,
        or if AI is fully competent to provide a direct self-contained response.
        """
        q = (query or "").strip().lower()
        words = q.split()
        word_count = len(words)

        # 1. Manual User Overrides
        if target_scholar_id or force_scholar_escalation:
            needs_scholar = True
            scholar_reason = "هدایت صریح به انتخاب کاربر / ارجاع مستقیم به استاد"
        else:
            needs_scholar = False
            scholar_reason = ""

        if target_book_id:
            needs_book = True
            book_reason = "هدایت صریح به انتخاب کاربر / ارجاع مستقیم به کتاب"
        else:
            needs_book = False
            book_reason = ""

        # 2. Conversational / Greeting Detection
        is_greeting = bool(cls.GREETINGS_PATTERN.search(q))
        if is_greeting and word_count <= 8 and not target_scholar_id and not target_book_id and not force_scholar_escalation:
            return {
                "needs_scholar": False,
                "needs_book": False,
                "can_ai_handle_directly": True,
                "ai_capability_status": "SELF_SUFFICIENT",
                "reasoning": "احوالپرسی و مکالمه عمومی — پاسخ مستقل و مستقیم هوش مصنوعی بدون نیاز به عالم یا کتاب",
                "domain": "CONVERSATIONAL"
            }

        # 3. Explicit Scholar Requests & Complex Fiqh / Crisis Escalation
        has_explicit_scholar = any(cls._matches_phrase(sw, q) for sw in cls.EXPLICIT_SCHOLAR_WORDS)
        has_complex_issue = any(cls._matches_phrase(cw, q) for cw in cls.COMPLEX_FIQH_CRITICAL_WORDS)

        if not needs_scholar:
            if has_explicit_scholar:
                needs_scholar = True
                scholar_reason = "درخواست صریح کاربر جهت مشورت با استاد یا فتوای فقهی"
            elif has_complex_issue:
                needs_scholar = True
                scholar_reason = "مسئله مستحدثه، مالی پیچیده یا موضوع نیازمند نظر اجتهادی اساتید"
            elif rag_sufficient is False and any(cls._matches_phrase(kw, q) for kw in ["حکم", "شرعی", "فتوا", "جایز", "حلال", "حرام"]):
                needs_scholar = True
                scholar_reason = "عدم قطعیت منبع کتب و ضرورت استعلام از اساتید فقهی"

        # 4. Explicit Book & Source Requests
        has_explicit_book = any(cls._matches_phrase(bw, q) for bw in cls.EXPLICIT_BOOK_WORDS)

        if not needs_book:
            if has_explicit_book:
                needs_book = True
                book_reason = "درخواست صریح منبع، تفسیر یا کتاب مطالعاتی توسط کاربر"
            elif any(cls._matches_phrase(tw, q) for tw in ["تفسیر المیزان", "نهج‌البلاغه", "صحیح بخاری", "اصول کافی", "کشف المراد"]):
                needs_book = True
                book_reason = "اشاره مستقیم به یکی از کتب مرجع پایگاه دانش"

        # 5. Routine self-contained questions check
        has_routine_edu = any(cls._matches_phrase(rw, q) for rw in cls.ROUTINE_EDUCATIONAL_WORDS)
        if has_routine_edu and not has_explicit_scholar and not has_explicit_book and not target_scholar_id and not target_book_id and not force_scholar_escalation:
            needs_scholar = False
            needs_book = False

        # 6. Overall AI Capability Status
        can_ai_handle = not needs_scholar
        if needs_scholar and needs_book:
            status = "COMPREHENSIVE"
            reasoning = "موضوع نیازمند بررسی تخصصی استاد و مطالعه کتاب مرجع مربوطه"
        elif needs_scholar:
            status = "SCHOLAR_ESCALATED"
            reasoning = scholar_reason or "ارجاع به استاد/عالم متخصص جهت مشاوره یا بررسی فقهی"
        elif needs_book:
            status = "BOOK_RECOMMENDED"
            reasoning = book_reason or "معرفی کتاب مرجع از کتابخانه جهت مطالعه تفصیلی"
        else:
            status = "SELF_SUFFICIENT"
            reasoning = "هوش مصنوعی کاملاً توانایی پاسخگویی مستقل به این پرسش را دارد (بدون نیاز به عالم یا کتاب)"

        return {
            "needs_scholar": needs_scholar,
            "needs_book": needs_book,
            "can_ai_handle_directly": can_ai_handle,
            "ai_capability_status": status,
            "reasoning": reasoning,
            "domain": "FIQH" if has_complex_issue else ("BOOK_RESEARCH" if has_explicit_book else "GENERAL")
        }

    @classmethod
    async def recommend_scholar_and_book(
        cls,
        query: str,
        db: Optional[AsyncSession] = None,
        target_scholar_id: Optional[str] = None,
        target_book_id: Optional[str] = None,
        force_scholar_escalation: bool = False,
        rag_sufficient: Optional[bool] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if not query and not target_scholar_id and not target_book_id:
            return None, None

        # Step 0: Intelligent Intent & Capability Assessment
        assessment = cls.assess_intent_and_routing_needs(
            query=query,
            target_scholar_id=target_scholar_id,
            target_book_id=target_book_id,
            force_scholar_escalation=force_scholar_escalation,
            rag_sufficient=rag_sufficient
        )

        q_clean = (query or "").lower().replace("؟", "").strip()

        # -------------------------------------------------------------
        # 1. Match Scholar ONLY IF assessment requires scholar or targeted
        # -------------------------------------------------------------
        best_scholar = None
        best_scholar_score = -1
        match_reason_scholar = ""

        if assessment["needs_scholar"] or target_scholar_id:
            db_scholars = []
            if db is not None:
                try:
                    res = await db.execute(select(Scholar))
                    db_scholars = res.scalars().all()
                except Exception as e:
                    logger.debug(f"Could not load scholars from db: {e}")

            # If explicit scholar requested, prioritize direct routing
            if target_scholar_id:
                if db_scholars:
                    target_s = next((s for s in db_scholars if s.id == target_scholar_id), None)
                    if target_s:
                        best_scholar = {
                            "id": target_s.id,
                            "name": target_s.name,
                            "title": target_s.title,
                            "specialties": target_s.specialties or [],
                            "rating": target_s.rating or 4.95,
                            "avatarUrl": target_s.avatar_url or f"https://api.dicebear.com/7.x/personas/svg?seed={target_s.name}",
                            "matchReason": f"هدایت اختصاصی به استاد/عالم منتخب: {target_s.name} ({target_s.title})",
                            "actionUrl": f"scholar_chat.html?scholarId={target_s.id}"
                        }
                if not best_scholar:
                    target_fb = next((fb for fb in FALLBACK_SCHOLARS if fb["id"] == target_scholar_id), None)
                    if target_fb:
                        best_scholar = {
                            "id": target_fb["id"],
                            "name": target_fb["name"],
                            "title": target_fb["title"],
                            "specialties": target_fb["specialties"],
                            "rating": 4.95,
                            "avatarUrl": f"https://api.dicebear.com/7.x/personas/svg?seed={target_fb['name']}",
                            "matchReason": f"هدایت اختصاصی به استاد/عالم منتخب: {target_fb['name']} ({target_fb['title']})",
                            "actionUrl": target_fb["actionUrl"]
                        }
                if not best_scholar and db is not None:
                    try:
                        direct_s = await db.scalar(select(Scholar).where(Scholar.id == target_scholar_id))
                        if direct_s:
                            best_scholar = {
                                "id": direct_s.id,
                                "name": direct_s.name,
                                "title": direct_s.title,
                                "specialties": direct_s.specialties or [],
                                "rating": direct_s.rating or 4.95,
                                "avatarUrl": direct_s.avatar_url or f"https://api.dicebear.com/7.x/personas/svg?seed={direct_s.name}",
                                "matchReason": f"هدایت اختصاصی به استاد/عالم منتخب: {direct_s.name} ({direct_s.title})",
                                "actionUrl": f"scholar_chat.html?scholarId={direct_s.id}"
                            }
                    except Exception:
                        pass
                if not best_scholar:
                    best_scholar = {
                        "id": target_scholar_id,
                        "name": f"استاد منتخب ({target_scholar_id})",
                        "title": "کارشناس و مشاور معارفی",
                        "specialties": ["مشاوره و معارف اسلامی"],
                        "rating": 4.95,
                        "avatarUrl": f"https://api.dicebear.com/7.x/personas/svg?seed={target_scholar_id}",
                        "matchReason": f"هدایت اختصاصی به استاد/عالم منتخب: {target_scholar_id}",
                        "actionUrl": f"scholar_chat.html?scholarId={target_scholar_id}"
                    }

            if not best_scholar and db_scholars:
                for s in db_scholars:
                    score = 0
                    specs = s.specialties or []
                    title_text = (s.title or "").lower()
                    bio_text = (s.bio or "").lower()

                    for fallback in FALLBACK_SCHOLARS:
                        if fallback["id"] == s.id or fallback["name"] in s.name:
                            for kw in fallback.get("keywords", []):
                                if cls._matches_phrase(kw, q_clean):
                                    score += 3

                    for spec in specs:
                        spec_words = [w for w in spec.split() if len(w) > 2]
                        for sw in spec_words:
                            if cls._matches_phrase(sw, q_clean):
                                score += 4

                    if s.madhhab:
                        for mkw in ["حنفی", "شافعی", "شیعه", "سنی", "اهل سنت", "جعفری", "امامی"]:
                            if cls._matches_phrase(mkw, q_clean) and mkw in s.madhhab:
                                score += 12

                    if score > best_scholar_score:
                        best_scholar_score = score
                        matched_specs = [spec for spec in specs if any(w in q_clean for w in spec.split() if len(w) > 2)]
                        if matched_specs:
                            match_reason_scholar = f"با توجه به تخصص علمی در «{' و '.join(matched_specs[:2])}» متناسب با موضوع سوال شما"
                        else:
                            match_reason_scholar = f"با توجه به سوابق و تخصص در {s.title}"

                        best_scholar = {
                            "id": s.id,
                            "name": s.name,
                            "title": s.title,
                            "specialties": specs,
                            "rating": s.rating,
                            "avatarUrl": s.avatar_url or f"https://api.dicebear.com/7.x/personas/svg?seed={s.name}",
                            "matchReason": match_reason_scholar,
                            "actionUrl": f"scholar_chat.html?scholarId={s.id}"
                        }

            # If no DB scholar matched well enough, match against built-in fallback scholars
            if not best_scholar or best_scholar_score < 4:
                best_fb_score = -1
                best_fb = None
                for fb in FALLBACK_SCHOLARS:
                    score = 0
                    for kw in fb["keywords"]:
                        if cls._matches_phrase(kw, q_clean):
                            score += 2
                    for spec in fb["specialties"]:
                        if any(cls._matches_phrase(w, q_clean) for w in spec.split() if len(w) > 2):
                            score += 3
                    if score > best_fb_score and score >= 2:
                        best_fb_score = score
                        best_fb = fb

                if best_fb:
                    best_scholar = {
                        "id": best_fb["id"],
                        "name": best_fb["name"],
                        "title": best_fb["title"],
                        "specialties": best_fb["specialties"],
                        "rating": 4.95,
                        "avatarUrl": f"https://api.dicebear.com/7.x/personas/svg?seed={best_fb['name']}",
                        "matchReason": best_fb["match_reason"],
                        "actionUrl": best_fb["actionUrl"]
                    }
                elif force_scholar_escalation or assessment["needs_scholar"]:
                    # When scholar escalation is strictly required, choose best domain fallback
                    best_fb = FALLBACK_SCHOLARS[0]
                    best_scholar = {
                        "id": best_fb["id"],
                        "name": best_fb["name"],
                        "title": best_fb["title"],
                        "specialties": best_fb["specialties"],
                        "rating": 4.95,
                        "avatarUrl": f"https://api.dicebear.com/7.x/personas/svg?seed={best_fb['name']}",
                        "matchReason": "ارجاع به استاد معارفی برتر جهت بررسی دقیق فقهی",
                        "actionUrl": best_fb["actionUrl"]
                    }

        # -------------------------------------------------------------
        # 2. Match Book ONLY IF assessment requires book or targeted
        # -------------------------------------------------------------
        best_book = None
        best_book_score = -1
        match_reason_book = ""

        if assessment["needs_book"] or target_book_id:
            db_books = []
            if db is not None:
                try:
                    res = await db.execute(select(Book))
                    db_books = res.scalars().all()
                except Exception as e:
                    logger.debug(f"Could not load books from db: {e}")

            # If explicit target book requested, prioritize direct routing
            if target_book_id:
                if db_books:
                    target_b = next((b for b in db_books if b.id == target_book_id), None)
                    if target_b:
                        best_book = {
                            "id": target_b.id,
                            "title": target_b.title,
                            "author": target_b.author or "علمای اسلام",
                            "categoryTitle": target_b.category_id or "معارف اسلامی",
                            "matchReason": f"هدایت اختصاصی به کتاب مرجع منتخب: «{target_b.title}»",
                            "actionUrl": f"book-reader.html?book={target_b.id}"
                        }
                if not best_book:
                    target_fb_b = next((fb for fb in FALLBACK_BOOKS if fb["id"] == target_book_id), None)
                    if target_fb_b:
                        best_book = {
                            "id": target_fb_b["id"],
                            "title": target_fb_b["title"],
                            "author": target_fb_b["author"],
                            "categoryTitle": target_fb_b["categoryTitle"],
                            "matchReason": f"هدایت اختصاصی به کتاب مرجع منتخب: «{target_fb_b['title']}»",
                            "actionUrl": target_fb_b["actionUrl"]
                        }
                if not best_book and db is not None:
                    try:
                        direct_b = await db.scalar(select(Book).where(Book.id == target_book_id))
                        if direct_b:
                            best_book = {
                                "id": direct_b.id,
                                "title": direct_b.title,
                                "author": direct_b.author or "علمای اسلام",
                                "categoryTitle": direct_b.category_id or "معارف اسلامی",
                                "matchReason": f"هدایت اختصاصی به کتاب مرجع منتخب: «{direct_b.title}»",
                                "actionUrl": f"book-reader.html?book={direct_b.id}"
                            }
                    except Exception:
                        pass
                if not best_book:
                    best_book = {
                        "id": target_book_id,
                        "title": f"کتاب منتخب ({target_book_id})",
                        "author": "کتابخانه معارفی",
                        "categoryTitle": "معارف اسلامی",
                        "matchReason": f"هدایت اختصاصی به کتاب مرجع منتخب: {target_book_id}",
                        "actionUrl": f"book-reader.html?book={target_book_id}"
                    }

            if not best_book and db_books:
                for b in db_books:
                    score = 0
                    topics = b.topics or []
                    tags = b.tags or []
                    combined_meta = f"{b.title} {b.author or ''} {' '.join(topics)} {' '.join(tags)} {b.description or ''}".lower()

                    for fallback_b in FALLBACK_BOOKS:
                        if fallback_b["id"] == b.id or fallback_b["title"] in b.title:
                            for kw in fallback_b.get("keywords", []):
                                if cls._matches_phrase(kw, q_clean):
                                    score += 3

                    for topic in topics:
                        for tw in topic.split():
                            if len(tw) > 2 and cls._matches_phrase(tw, q_clean):
                                score += 4

                    for mkw in ["حنفی", "شافعی", "شیعه", "سنی", "اهل سنت", "جعفری", "امامی", "مقارن"]:
                        if cls._matches_phrase(mkw, q_clean) and mkw in combined_meta:
                            score += 8

                    if score > best_book_score:
                        best_book_score = score
                        matched_topics = [t for t in topics if any(w in q_clean for w in t.split() if len(w) > 2)]
                        if matched_topics:
                            match_reason_book = f"شامل فصول و نصوص مستند در محور «{' و '.join(matched_topics[:2])}»"
                        else:
                            match_reason_book = f"منبع معتبر معارفی پیرامون موضوع «{b.title}»"

                        best_book = {
                            "id": b.id,
                            "title": b.title,
                            "author": b.author,
                            "categoryTitle": b.category_id or "معارف اسلامی",
                            "matchReason": match_reason_book,
                            "actionUrl": f"book-reader.html?book={b.id}"
                        }

            # If no DB book matched well enough, match against built-in fallback books
            if not best_book or best_book_score < 4:
                best_fb_b_score = -1
                best_fb_b = None
                for fb_b in FALLBACK_BOOKS:
                    score = 0
                    for kw in fb_b["keywords"]:
                        if cls._matches_phrase(kw, q_clean):
                            score += 2
                    if score > best_fb_b_score and score >= 2:
                        best_fb_b_score = score
                        best_fb_b = fb_b

                if best_fb_b:
                    best_book = {
                        "id": best_fb_b["id"],
                        "title": best_fb_b["title"],
                        "author": best_fb_b["author"],
                        "categoryTitle": best_fb_b["categoryTitle"],
                        "matchReason": best_fb_b["match_reason"],
                        "actionUrl": fb_b["actionUrl"]
                    }
                elif assessment["needs_book"]:
                    # If book was explicitly demanded but no exact keyword matched, introduce general reference
                    best_fb_b = FALLBACK_BOOKS[0]
                    best_book = {
                        "id": best_fb_b["id"],
                        "title": best_fb_b["title"],
                        "author": best_fb_b["author"],
                        "categoryTitle": best_fb_b["categoryTitle"],
                        "matchReason": "منبع معتبر قرآنی و معارفی جهت مطالعه بیشتر",
                        "actionUrl": best_fb_b["actionUrl"]
                    }

        return best_scholar, best_book

    @classmethod
    async def get_routing_verdict(
        cls,
        query: str,
        db: Optional[AsyncSession] = None,
        target_scholar_id: Optional[str] = None,
        target_book_id: Optional[str] = None,
        force_scholar_escalation: bool = False,
        rag_sufficient: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Returns full detailed assessment along with recommended scholar and book objects.
        """
        assessment = cls.assess_intent_and_routing_needs(
            query=query,
            target_scholar_id=target_scholar_id,
            target_book_id=target_book_id,
            force_scholar_escalation=force_scholar_escalation,
            rag_sufficient=rag_sufficient
        )

        rec_s, rec_b = await cls.recommend_scholar_and_book(
            query=query,
            db=db,
            target_scholar_id=target_scholar_id,
            target_book_id=target_book_id,
            force_scholar_escalation=force_scholar_escalation,
            rag_sufficient=rag_sufficient
        )

        return {
            **assessment,
            "suggestScholarEscalation": assessment.get("needs_scholar", False) or force_scholar_escalation,
            "recommendedScholar": rec_s,
            "recommendedBook": rec_b
        }
