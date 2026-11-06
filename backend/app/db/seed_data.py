import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.core.security import hash_password
from app.db.base import utc_now
from app.db.models import (
    User, PersonaConfig, Scholar, ConsultationThread, ConsultationMessage,
    ScholarQuickReply, LibraryCategory, LibraryPoster, Book, BookChapter,
    Surah, Ayah, AyahTadabburData, Reciter, AudioSegment, PromptSuggestion,
    AISectionConfig,
    Post, PostMedia, PostComment, PostLike, PostBookmark, PostCommentLike, PostReport,
    ThematicSurah, ThematicAyah
)

async def seed_section_configs_if_needed(db: AsyncSession):
    default_sections = [
        AISectionConfig(
            section_key="chat",
            section_name_fa="گفتگوی هوشمند معارفی (AI Chat)",
            description_fa="پاسخ به سوالات معارفی، احکام و استنادات قرآنی/روایی و استریم پاسخ",
            model_name=settings.AI_CHAT_MODEL or settings.GEMINI_MODEL,
            base_url=settings.AI_CHAT_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_CHAT_API_KEY,
            provider=settings.AI_CHAT_PROVIDER or "gemini",
            is_active=True,
            extra_params={"temperature": 0.7, "maxTokens": 2048}
        ),
        AISectionConfig(
            section_key="embedding",
            section_name_fa="تعبیه برداری و جستجوی معنایی (Vector Embeddings)",
            description_fa="تولید بردار ۷۶۸ بعدی جهت جستجوی معنایی و پایگاه داده کیودرانت (Qdrant)",
            model_name=settings.AI_EMBEDDING_MODEL or settings.GEMINI_EMBEDDING_MODEL,
            base_url=settings.AI_EMBEDDING_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_EMBEDDING_API_KEY,
            provider=settings.AI_EMBEDDING_PROVIDER or "gemini",
            is_active=True,
            extra_params={"dimension": 768}
        ),
        AISectionConfig(
            section_key="agentic_rag",
            section_name_fa="موتور عامل هوشمند RAG (Agentic RAG Engine)",
            description_fa="تحلیل قصد کاربر، تجزیه کوئری به چند پرسش، برنامه‌ریزی جستجوی ترکیبی و بازنویسی کوئری",
            model_name=settings.AI_AGENTIC_RAG_MODEL or settings.GEMINI_MODEL,
            base_url=settings.AI_AGENTIC_RAG_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_AGENTIC_RAG_API_KEY,
            provider=settings.AI_AGENTIC_RAG_PROVIDER or "gemini",
            is_active=True,
            extra_params={"maxIterations": 2, "temperature": 0.3}
        ),
        AISectionConfig(
            section_key="jev",
            section_name_fa="موتور تصمیم‌گیری سامانه یک JEV (Decision Engine)",
            description_fa="تصمیم‌گیری سریع غیرتولیدی، انتخاب فصل کتاب و ارزیابی کالیبره‌شده کفایت شواهد",
            model_name=settings.JEV_MODEL or "systemone-v1",
            base_url=settings.JEV_BASE_URL or settings.JEV_API_URL,
            api_key=settings.JEV_API_KEY,
            provider=settings.JEV_PROVIDER or "jev_systemone",
            is_active=True,
            extra_params={"timeoutSeconds": 4.0}
        ),
        AISectionConfig(
            section_key="library",
            section_name_fa="هوش مصنوعی کتابخانه و کتب (Library AI)",
            description_fa="چت تخصصی با محتوای کتب اسلامی و تحلیل عمیق، خلاصه‌سازی و اصطلاح‌شناسی فصول",
            model_name=settings.AI_LIBRARY_MODEL or settings.GEMINI_MODEL,
            base_url=settings.AI_LIBRARY_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_LIBRARY_API_KEY,
            provider=settings.AI_LIBRARY_PROVIDER or "gemini",
            is_active=True,
            extra_params={"temperature": 0.5}
        ),
        AISectionConfig(
            section_key="quran",
            section_name_fa="تدبر و تحلیل هوشمند آیات (Quran Tadabbur AI)",
            description_fa="استخراج نکات تدبری، پیوندهای مفهومی و تحلیل ادبی آیات سوره",
            model_name=settings.AI_QURAN_MODEL or settings.GEMINI_MODEL,
            base_url=settings.AI_QURAN_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_QURAN_API_KEY,
            provider=settings.AI_QURAN_PROVIDER or "gemini",
            is_active=True,
            extra_params={"temperature": 0.6}
        ),
        AISectionConfig(
            section_key="consultation",
            section_name_fa="دستیار هوشمند مشاوران و علما (Consultation AI)",
            description_fa="تریاژ خودکار سوالات، پیشنهاد پیش‌نویس پاسخ برای اساتید و دسته‌بندی استفتائات",
            model_name=settings.AI_CONSULTATION_MODEL or settings.GEMINI_MODEL,
            base_url=settings.AI_CONSULTATION_BASE_URL or settings.GEMINI_BASE_URL,
            api_key=settings.AI_CONSULTATION_API_KEY,
            provider=settings.AI_CONSULTATION_PROVIDER or "gemini",
            is_active=True,
            extra_params={"temperature": 0.4}
        ),
        AISectionConfig(
            section_key="agent_planner",
            section_name_fa="طراح استدلال و نقشه راه ایجنت (Agent Planner)",
            description_fa="استخراج اهداف، تحلیل پیش‌زمینه و پرسونا، تفکیک سوال به زیرمسائل و تدوین نقشه ساختاریافته",
            model_name=settings.AI_AGENT_PLANNER_MODEL or "deepseek-flash",
            base_url=settings.AI_AGENT_PLANNER_BASE_URL or "https://api.deepseek.com",
            api_key=settings.AI_AGENT_PLANNER_API_KEY,
            provider=settings.AI_AGENT_PLANNER_PROVIDER or "openai_compatible",
            is_active=True,
            extra_params={"temperature": 0.2, "max_tokens": 1000}
        ),
        AISectionConfig(
            section_key="agent_executor",
            section_name_fa="مجری چرخه ابزار و تحلیل شواهد (Agent ReAct Executor)",
            description_fa="فراخوانی ابزارهای تخصصی کتابخانه، قرآن و مقایسه مذاهب با تصمیم‌گیری ReAct",
            model_name=settings.AI_AGENT_EXECUTOR_MODEL or "deepseek-flash",
            base_url=settings.AI_AGENT_EXECUTOR_BASE_URL or "https://api.deepseek.com",
            api_key=settings.AI_AGENT_EXECUTOR_API_KEY,
            provider=settings.AI_AGENT_EXECUTOR_PROVIDER or "openai_compatible",
            is_active=True,
            extra_params={"temperature": 0.3, "max_tool_iterations": 6, "timeout_seconds": 45}
        ),
        AISectionConfig(
            section_key="agent_verifier",
            section_name_fa="ارزیاب و اعتبارسنج احکام و ارجاعات (Agent Verifier)",
            description_fa="بررسی تطابق فتواها و نظرات فقهی با متن مستندات و اصالت ارجاعات",
            model_name=settings.AI_AGENT_VERIFIER_MODEL or "deepseek-flash",
            base_url=settings.AI_AGENT_VERIFIER_BASE_URL or "https://api.deepseek.com",
            api_key=settings.AI_AGENT_VERIFIER_API_KEY,
            provider=settings.AI_AGENT_VERIFIER_PROVIDER or "openai_compatible",
            is_active=True,
            extra_params={"temperature": 0.1, "max_correction_rounds": 1}
        ),
        AISectionConfig(
            section_key="agent_memory",
            section_name_fa="استخراج‌گر و پالاینده حافظه بلندمدت (Agent Memory Extractor)",
            description_fa="استخراج امن ترجیحات فقهی، علایق و سوالات بی‌پاسخ بدون ذخیره اطلاعات حساس",
            model_name=settings.AI_AGENT_MEMORY_MODEL or "deepseek-flash",
            base_url=settings.AI_AGENT_MEMORY_BASE_URL or "https://api.deepseek.com",
            api_key=settings.AI_AGENT_MEMORY_API_KEY,
            provider=settings.AI_AGENT_MEMORY_PROVIDER or "openai_compatible",
            is_active=True,
            extra_params={"temperature": 0.1}
        ),
        AISectionConfig(
            section_key="chunk_representation",
            section_name_fa="پردازش چانک‌ها و تولید نماینده‌ها (Chunk Representation AI)",
            description_fa="پردازش پس‌زمینه بدون وقفه، خلاصه‌سازی فشرده، تولید سوالات فرضی و استخراج مفاهیم با مدل‌های انویدیا (NVIDIA NIM)",
            model_name=settings.AI_CHUNK_REPRESENTATION_MODEL or settings.NVIDIA_DEFAULT_MODEL,
            base_url=settings.AI_CHUNK_REPRESENTATION_BASE_URL or settings.NVIDIA_BASE_URL,
            api_key=settings.AI_CHUNK_REPRESENTATION_API_KEY or settings.NVIDIA_API_KEY,
            provider=settings.AI_CHUNK_REPRESENTATION_PROVIDER or "openai_compatible",
            is_active=True,
            extra_params={
                "temperature": 0.1,
                "rpm_limit": settings.NVIDIA_RPM_LIMIT,
                "fallback_models": settings.NVIDIA_FALLBACK_MODELS,
                "available_models": [
                    "nvidia/nemotron-3.5-bolt-e4b",
                    "nvidia/nemotron-3.5-super-vl-120b-a12b",
                    "mistralai/mistral-large-4-1t-a52b"
                ]
            }
        )
    ]
    for sec in default_sections:
        existing = await db.scalar(select(AISectionConfig).where(AISectionConfig.section_key == sec.section_key))
        if not existing:
            db.add(sec)
    await db.commit()


async def seed_feed_if_needed(db: AsyncSession):
    existing_post = await db.scalar(select(Post).limit(1))
    if existing_post:
        return

    # 1. Ensure user accounts exist for all feed authors, commenters, and likers
    feed_users = [
        User(
            id="usr_seeker_1",
            phone_number="09121111111",
            full_name="علی رضایی",
            hashed_password=hash_password("123456"),
            role="SEEKER",
            madhhab="شیعه اثناعشری",
            age=28,
            gender="MALE",
            education="کارشناسی ارشد مهندسی نرم‌افزار",
            interests=["TAFSIR", "AKHLAQ"],
            knowledge_level="ACADEMIC",
            learning_goals="آشنایی عمیق‌تر با مفاهیم تدبر در قرآن کریم و فضایل اخلاقی در نهج‌البلاغه",
            avatar="/media/avatars/user_1.png",
            created_at=utc_now()
        ),
        User(
            id="usr_scholar_1",
            phone_number="09122222222",
            full_name="حجت‌الاسلام دکتر محمدرضا عابدی",
            hashed_password=hash_password("123456"),
            role="SCHOLAR",
            madhhab="شیعه اثناعشری",
            age=45,
            gender="MALE",
            education="دکتری مبانی فقه و حقوق اسلامی و سطح ۴ حوزه",
            interests=["FIQH", "KALAM", "TAFSIR"],
            knowledge_level="SEMINARY",
            learning_goals="پژوهش و پاسخگویی به شبهات فقهی و کلامی معاصر",
            avatar="/media/avatars/scholar_1.png",
            created_at=utc_now()
        ),
        User(
            id="usr_scholar_2",
            phone_number="09123333333",
            full_name="ماموستا دکتر صلاح‌الدین محمدی",
            hashed_password=hash_password("123456"),
            role="SCHOLAR",
            madhhab="اهل سنت (شافعی)",
            age=52,
            gender="MALE",
            education="دکتری فقه مقارن و مدرس دارالافتاء",
            interests=["FIQH", "FAMILY", "TAFSIR"],
            knowledge_level="SEMINARY",
            learning_goals="تقریب بین مذاهب و هدایت جوانان",
            avatar="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=80",
            created_at=utc_now()
        ),
        User(
            id="usr_scholar_3",
            phone_number="09124444444",
            full_name="مولوی عبدالکریم آخوند گرگانی",
            hashed_password=hash_password("123456"),
            role="SCHOLAR",
            madhhab="اهل سنت (حنفی)",
            age=48,
            gender="MALE",
            education="مفتی حنفی و مدیر حوزه علمیه اهل سنت",
            interests=["FIQH", "AKHLAQ"],
            knowledge_level="SEMINARY",
            learning_goals="آموزش فقه و سیره نبوی",
            avatar="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&q=80",
            created_at=utc_now()
        ),
        User(
            id="usr_scholar_4",
            phone_number="09125555555",
            full_name="آیت‌الله سید مرتضی علوی حسینی",
            hashed_password=hash_password("123456"),
            role="SCHOLAR",
            madhhab="شیعه اثناعشری",
            age=58,
            gender="MALE",
            education="استاد درس خارج فقه و عضو مجمع عالی حکمت",
            interests=["AQAED", "AKHLAQ", "TAFSIR"],
            knowledge_level="SEMINARY",
            learning_goals="تدریس حکمت و عرفان اسلامی",
            avatar="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&q=80",
            created_at=utc_now()
        ),
        User(
            id="usr_seeker_2",
            phone_number="09126666666",
            full_name="زهرا طاهری",
            hashed_password=hash_password("123456"),
            role="SEEKER",
            madhhab="شیعه اثناعشری",
            age=24,
            gender="FEMALE",
            education="دانشجوی کارشناسی ارشد علوم قرآن و حدیث",
            interests=["TAFSIR", "QURAN_MEMORIZATION"],
            knowledge_level="ACADEMIC",
            learning_goals="حفظ کل قرآن کریم و مطالعه تفاسیر معتبر",
            avatar="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&q=80",
            created_at=utc_now()
        )
    ]

    for u in feed_users:
        chk = await db.scalar(select(User).where(User.id == u.id))
        if not chk:
            db.add(u)
    await db.flush()

    # Ensure scholar profiles exist and are linked to user_ids for FK integrity
    scholar_definitions = [
        ("scholar_1", "usr_scholar_1", "حجت‌الاسلام دکتر محمدرضا عابدی", "شیعه اثناعشری", "قم"),
        ("scholar_2", "usr_scholar_2", "ماموستا دکتر صلاح‌الدین محمدی", "اهل سنت (شافعی)", "سنندج"),
        ("scholar_3", "usr_scholar_3", "مولوی عبدالکریم آخوند گرگانی", "اهل سنت (حنفی)", "گرگان"),
        ("scholar_4", "usr_scholar_4", "آیت‌الله سید مرتضی علوی حسینی", "شیعه اثناعشری", "مشهد"),
    ]
    for s_id, u_id, s_name, s_madhhab, s_city in scholar_definitions:
        s = await db.scalar(select(Scholar).where(Scholar.id == s_id))
        if not s:
            s = Scholar(
                id=s_id,
                user_id=u_id,
                name=s_name,
                title="استاد معارف اسلامی",
                madhhab=s_madhhab,
                city=s_city,
                mosque="مسجد جامع",
                bio="پاسخگوی مسائل دینی و فقهی",
                is_verified=True
            )
            db.add(s)
        elif not s.user_id:
            s.user_id = u_id
    await db.flush()

    # 2. Seed Posts
    # Post 1: Video by Scholar Abedi (Fiqh Crypto)
    p1 = Post(
        id="post_fiqh_crypto_01",
        user_id="usr_scholar_1",
        scholar_id="scholar_1",
        is_scholar_post=True,
        title="حکم معاملات رمزارزها و دارایی‌های دیجیتال از منظر فقه معاصر",
        content="امروزه یکی از پربسامدترین پرسش‌های جوانان و فعالان بازار سرمایه، موضوع رمزارزها و توکن‌های دیجیتال است. بر اساس مبانی فقه معاملات و اصول کلی شریعت در باب مالیت و غرر، معاملات ارزهای دیجیتال در صورتی که واجد ارزش مبادله‌ای عقلایی بوده و ابزاری برای اکل مال به باطل یا قمار نباشد، با رعایت شرایط عامه صحت بیع نافذ است.\n\nدر این ویدیو به ۵ شرط اساسی حلیت این معاملات و دیدگاه مراجع عظام پرداخته‌ام.",
        content_type="VIDEO",
        category="FIQH",
        madhhab="مشترک",
        quran_references=[{
            "surah": "النساء",
            "ayah": 29,
            "text": "يَا أَيُّهَا الَّذِينَ آمَنُوا لَا تَأْكُلُوا أَمْوَالَكُم بَيْنَكُم بِالْبَاطِلِ إِلَّا أَن تَكُونَ تِجَارَةً عَن تَرَاضٍ مِّنكُمْ"
        }],
        hadith_references=[{
            "source": "کافی، ج ۵، کتاب المعیشة",
            "text": "الْمُسْلِمُونَ عِنْدَ شُرُوطِهِمْ إِلَّا شَرْطاً حَرَّمَ حَلَالاً أَوْ أَحَلَّ حَرَاماً"
        }],
        tags=["#فقه_معاملات", "#رمزارز", "#بیت‌کوین", "#کسب_حلال", "#احکام_اقتصادی"],
        status="PUBLISHED",
        views_count=4320,
        likes_count=428,
        comments_count=18,
        shares_count=94,
        saves_count=186,
        pinned_comment_id="comm_pinned_fatwa_01",
        ai_summary="این پست تحلیلی فقهی و موجز پیرامون رمزارزها از منظر قواعد فقهی تجارت، عدم غرر و عدالت اقتصادی ارائه می‌دهد.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m1 = PostMedia(
        id="med_p1_vid_01",
        post_id="post_fiqh_crypto_01",
        media_type="VIDEO",
        media_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        thumbnail_url="https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=800&q=80",
        duration_seconds=145,
        aspect_ratio="9:16",
        order=0
    )

    # Post 2: Video by Sunni Scholar Mamosta Mohammadi (Taqrib & Brotherhood)
    p2 = Post(
        id="post_taqrib_brotherhood_02",
        user_id="usr_scholar_2",
        scholar_id="scholar_2",
        is_scholar_post=True,
        title="تجلی اخوت اسلامی در پرتو آیه مبارکه اعتصام",
        content="امت اسلام به منزله پیکری واحد است که تنوع آراء فقهی میان مذاهب اربعه اهل سنت و مذهب امامیه، مایه رحمت و نشانه پویایی اجتهاد است.\n\nقرآن کریم ما را به چنگ زدن همگانی به ریسمان الهی امر فرموده است. بیایید در این برهه حساس، رشته‌های برادری ایمانی را با تکیه بر قبله واحد، قرآن واحد و رسالت خاتم‌الانبیاء (ص) مستحکم‌تر سازیم.",
        content_type="VIDEO",
        category="AQAED",
        madhhab="اهل سنت (شافعی)",
        quran_references=[{
            "surah": "آل عمران",
            "ayah": 103,
            "text": "وَاعْتَصِمُوا بِحَبْلِ اللَّهِ جَمِيعًا وَلَا تَفَرَّقُوا"
        }],
        hadith_references=[{
            "source": "صحیح مسلم و سنن ترمذی",
            "text": "مَثَلُ الْمُؤْمِنِينَ فِي تَوَادِّهِمْ وَتَرَاحُمِهِمْ وَتَعَاطُفِهِمْ مَثَلُ الْجَسَدِ إِذَا اشْتَكَى مِنْهُ عُضْوٌ تَدَاعَى لَهُ سَائِرُ الْجَسَدِ بِالسَّهَرِ وَالْحُمَّى"
        }],
        tags=["#وحدت_امت", "#تقریب_مذاهب", "#اخوت_اسلامی", "#قرآن_کریم"],
        status="PUBLISHED",
        views_count=5210,
        likes_count=612,
        comments_count=24,
        shares_count=165,
        saves_count=240,
        ai_summary="بیانات ارزشمند پیرامون حقیقت اخوت ایمانی، نفی تعصبات فرقه‌ای و هم‌افزایی مذاهب اسلامی در سایه قرآن.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m2 = PostMedia(
        id="med_p2_vid_01",
        post_id="post_taqrib_brotherhood_02",
        media_type="VIDEO",
        media_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        thumbnail_url="https://images.unsplash.com/photo-1542816417-0983c9c9ad53?w=800&q=80",
        duration_seconds=180,
        aspect_ratio="16:9",
        order=0
    )

    # Post 3: Audio Podcast by Ayatollah Alavi (Akhlaq & Saharkhizi)
    p3 = Post(
        id="post_podcast_sahar_03",
        user_id="usr_scholar_4",
        scholar_id="scholar_4",
        is_scholar_post=True,
        title="پادکست زمزمه سحر: شرحی بر مناجات العارفین و آثار سحرخیزی",
        content="خلوت شبانه با معبود، داروی دردهای بی‌درمان عصر شتاب‌زدگی و اضطراب است.\n\nدر این پادکست معارفی، با زبانی ساده و صمیمی به برکات مادی و معنوی تهجد، آرامش روانی ناشی از خلوت با خدا و چگونگی مداومت بر بیداری سحر پرداخته‌ام. التماس دعا در لحظات زلال سحر.",
        content_type="AUDIO",
        category="AKHLAQ",
        madhhab="شیعه اثناعشری",
        quran_references=[{
            "surah": "الإسراء",
            "ayah": 79,
            "text": "وَمِنَ اللَّيْلِ فَتَهَجَّدْ بِهِ نَافِلَةً لَّكَ عَسَىٰ أَن يَبْعَثَكَ رَبُّكَ مَقَامًا مَّحْمُودًا"
        }],
        hadith_references=[{
            "source": "بحارالانوار، ج ۸۷",
            "text": "صَلَاةُ اللَّيْلِ تُطَيِّبُ الرِّيحَ وَتَجْلِبُ الرِّزْقَ وَتَذْهَبُ بِالْهَمِّ"
        }],
        tags=["#پادکست_معارفی", "#نماز_شب", "#سحرخیزی", "#آرامش_روان", "#عرفان_عملی"],
        status="PUBLISHED",
        views_count=6780,
        likes_count=820,
        comments_count=32,
        shares_count=290,
        saves_count=380,
        ai_summary="پادکست اخلاقی آرامش‌بخش متمرکز بر آرامش قلب، سحرخیزی و پیوند معنوی با خدای متعال.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m3 = PostMedia(
        id="med_p3_aud_01",
        post_id="post_podcast_sahar_03",
        media_type="AUDIO",
        media_url="https://cdn.islamic.network/quran/audio/128/ar.alafasy/1.mp3",
        thumbnail_url="https://images.unsplash.com/photo-1507692049790-de58290a4334?w=800&q=80",
        duration_seconds=240,
        aspect_ratio="1:1",
        order=0
    )

    # Post 4: Multi-Image Carousel by Molavi Gorgani (Family & Youth)
    p4 = Post(
        id="post_carousel_family_04",
        user_id="usr_scholar_3",
        scholar_id="scholar_3",
        is_scholar_post=True,
        title="اسلایدهای آموزشی: ۵ راهکار نبوی در مواجهه با خطای نوجوان در خانه",
        content="نوجوانان در دنیای بمباران اطلاعات، بیش از سرزنش نیازمند گوش شنوا و تکریم شخصیت هستند.\n\nپیامبر اکرم (ص) الگوی کامل مدارا و محبت در خانواده بودند. در این مجموعه اسلایدهای اینفوگرافیک، ۵ کلید طلایی تربیتی را با هم مرور می‌کنیم که ورق زدن آن برای والدین و مربیان گرامی راهگشاست.",
        content_type="IMAGE_GALLERY",
        category="FAMILY",
        madhhab="اهل سنت (حنفی)",
        tags=["#تربیت_نوجوان", "#خانواده_اسلامی", "#روانشناسی_تربیتی", "#سیره_نبوی"],
        status="PUBLISHED",
        views_count=3900,
        likes_count=385,
        comments_count=14,
        shares_count=120,
        saves_count=215,
        ai_summary="راهنمای مصور ۵ مرحله‌ای تربیت دینی نوجوان با محوریت تکریم و شنیدن فعال برگرفته از سنت پیامبر اعظم.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m4_1 = PostMedia(
        id="med_p4_img_01",
        post_id="post_carousel_family_04",
        media_type="IMAGE",
        media_url="https://images.unsplash.com/photo-1509062522246-3755977927d7?w=800&q=80",
        thumbnail_url="https://images.unsplash.com/photo-1509062522246-3755977927d7?w=400&q=80",
        aspect_ratio="4:5",
        order=0
    )
    m4_2 = PostMedia(
        id="med_p4_img_02",
        post_id="post_carousel_family_04",
        media_type="IMAGE",
        media_url="https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=800&q=80",
        thumbnail_url="https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400&q=80",
        aspect_ratio="4:5",
        order=1
    )

    # Post 5: User Post by Ali Rezaei (Lifestyle & Ziyarat)
    p5 = Post(
        id="post_seeker_ziyarat_05",
        user_id="usr_seeker_1",
        scholar_id=None,
        is_scholar_post=False,
        title="غروب دلنشین صحن آزادی و زمزمه سوره یاسین",
        content="امروز بعد از یک هفته پرمشغله و خستگی‌های کار اداری، توفیق شد دو رکعت نماز بخوانم و در گوشه‌ای از صحن بنشینم. نسیم خنکی که می‌وزید حس آرامش بی‌بدیلی داد.\n\nبه این آیه فکر می‌کردم که فرمود: «أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ». واقعاً هیچ پناهگاهی محکم‌تر از یاد خداوند نیست. نایب‌الزیاره و دعاگوی همه دوستان معارفی و اساتید هستم.",
        content_type="IMAGE_SINGLE",
        category="LIFESTYLE",
        madhhab="شیعه اثناعشری",
        tags=["#دل_نوشته", "#آرامش", "#یاد_خدا", "#تجربه_معنوی"],
        status="PUBLISHED",
        views_count=1820,
        likes_count=215,
        comments_count=9,
        shares_count=18,
        saves_count=42,
        ai_summary="دل‌نوشته تجربی معنوی یک کاربر پیرامون آرامش ذکر خدا و پناه بردن به معنویت در برابر استرس‌های روزمره.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m5 = PostMedia(
        id="med_p5_img_01",
        post_id="post_seeker_ziyarat_05",
        media_type="IMAGE",
        media_url="https://images.unsplash.com/photo-1564769625905-50e93615e769?w=800&q=80",
        thumbnail_url="https://images.unsplash.com/photo-1564769625905-50e93615e769?w=400&q=80",
        aspect_ratio="1:1",
        order=0
    )

    # Post 6: User Post by Zahra Taheri (Tafsir & Waqia)
    p6 = Post(
        id="post_seeker_waqia_06",
        user_id="usr_seeker_2",
        scholar_id=None,
        is_scholar_post=False,
        title="تجربه حفظ سوره واقعه و حس بی‌نیازی قلبی",
        content="سلام و درود به دوستان گرامی اهل معرفت.\nحدود یک ماه است برنامه تلاوت و حفظ آیات پایانی سوره واقعه را قبل از خواب شروع کرده‌ام. حس غنا و گشایشی که در زندگی ایجاد کرده فوق‌العاده است. اساتید محترم، کدام شرح یا تفسیر صوتی را برای درک بهتر اصطلاح «السَّابِقُونَ السَّابِقُونَ» پیشنهاد می‌فرمایید؟",
        content_type="IMAGE_SINGLE",
        category="TAFSIR",
        madhhab="مشترک",
        tags=["#حفظ_قرآن", "#سوره_واقعه", "#تدبر_در_آیات", "#تفسیر"],
        status="PUBLISHED",
        views_count=2140,
        likes_count=265,
        comments_count=11,
        shares_count=25,
        saves_count=74,
        pinned_comment_id="comm_tafsir_guide_01",
        ai_summary="اشتراک تجربه انس با قرآن و درخواست راهنمایی مطالعاتی در باب آیات سوره واقعه.",
        created_at=utc_now(),
        updated_at=utc_now()
    )

    m6 = PostMedia(
        id="med_p6_img_01",
        post_id="post_seeker_waqia_06",
        media_type="IMAGE",
        media_url="https://images.unsplash.com/photo-1609599006353-e629aaabfeae?w=800&q=80",
        thumbnail_url="https://images.unsplash.com/photo-1609599006353-e629aaabfeae?w=400&q=80",
        aspect_ratio="1:1",
        order=0
    )

    db.add_all([p1, p2, p3, p4, p5, p6])
    db.add_all([m1, m2, m3, m4_1, m4_2, m5, m6])
    await db.flush()

    # 3. Seed Comments
    c1_user = PostComment(
        id="comm_user_q_01",
        post_id="post_fiqh_crypto_01",
        user_id="usr_seeker_1",
        content="سلام استاد عابدی گرامی. تشکر از توضیحات شیوا. آیا استیکینگ (Staking) رمزارزها که ماهانه سود معین می‌دهند هم حکم قرض با بهره یا ربا را دارد؟",
        is_scholar_reply=False,
        is_pinned=False,
        likes_count=14,
        status="APPROVED",
        created_at=utc_now()
    )
    c1_scholar_pinned = PostComment(
        id="comm_pinned_fatwa_01",
        post_id="post_fiqh_crypto_01",
        user_id="usr_scholar_1",
        parent_comment_id="comm_user_q_01",
        content="سلام علیکم و رحمة‌الله برادر گرامی. اگر ماهیت استیکینگ مشارکت در پاداش اعتبارسنجی شبکه (Proof of Stake) باشد و سود ناشی از درآمد اعتبارسنجی باشد حلال است؛ اما اگر متضمن تضمین اصل سرمایه و سود قطعی از سوی صرافی به عنوان وام باشد، شبهه ربوی دارد و جایز نیست.",
        is_scholar_reply=True,
        is_pinned=True,
        likes_count=86,
        status="APPROVED",
        created_at=utc_now()
    )
    c2 = PostComment(
        id="comm_taqrib_01",
        post_id="post_taqrib_brotherhood_02",
        user_id="usr_seeker_2",
        content="بسیار عالی و دلگرم‌کننده بود ماموستای عزیز. خدا خیرتان دهد که پیام‌آور صلح و محبت میان پیروان مذاهب اسلامی هستید.",
        is_scholar_reply=False,
        is_pinned=False,
        likes_count=22,
        status="APPROVED",
        created_at=utc_now()
    )
    c6_scholar = PostComment(
        id="comm_tafsir_guide_01",
        post_id="post_seeker_waqia_06",
        user_id="usr_scholar_4",
        content="سلام علیکم دخترم. خداوند توفیقات شما را افزون فرماید. برای درک لطایف سوره واقعه، مطالعه تفسیر المیزان ذیل این سوره و نیز کتاب «پرتوی از قرآن» بسیار راه‌گشا و جان‌افزاست.",
        is_scholar_reply=True,
        is_pinned=True,
        likes_count=45,
        status="APPROVED",
        created_at=utc_now()
    )

    db.add_all([c1_user, c1_scholar_pinned, c2, c6_scholar])

    # 4. Seed Likes & Bookmarks
    db.add_all([
        PostLike(post_id="post_fiqh_crypto_01", user_id="usr_seeker_1"),
        PostLike(post_id="post_taqrib_brotherhood_02", user_id="usr_seeker_1"),
        PostLike(post_id="post_podcast_sahar_03", user_id="usr_seeker_1"),
        PostLike(post_id="post_carousel_family_04", user_id="usr_seeker_2"),
        PostLike(post_id="post_seeker_waqia_06", user_id="usr_scholar_1"),
        PostBookmark(post_id="post_fiqh_crypto_01", user_id="usr_seeker_1"),
        PostBookmark(post_id="post_podcast_sahar_03", user_id="usr_seeker_1")
    ])

    await db.commit()


async def seed_admin_if_needed(db: AsyncSession):
    existing = await db.scalar(select(User).where(User.phone_number == "09120000000"))
    if existing:
        return
    admin_user = User(
        id="usr_admin_1",
        phone_number="09120000000",
        full_name="مدیر سیستم",
        hashed_password=hash_password("123456"),
        role="ADMIN",
        madhhab="مشترک",
        is_active=True,
        age=35,
        gender="MALE",
        education="مدیریت سیستم‌ها",
        knowledge_level="GENERAL",
        avatar="/media/avatars/admin.png"
    )
    db.add(admin_user)
    admin_persona = PersonaConfig(
        user_id="usr_admin_1",
        bot_name="دستیار هوشمند ادمین",
        bot_role_preset="ADMIN_ASSISTANT",
        tone="FORMAL_POLITE"
    )
    db.add(admin_persona)
    await db.commit()


async def seed_thematic_surahs_if_needed(db: AsyncSession):
    existing_ts = await db.scalar(select(ThematicSurah).limit(1))
    if existing_ts:
        return

    # 1. سوره اخوت و برادری ایمانی
    ts_brotherhood = ThematicSurah(
        id="ts_brotherhood_01",
        title="سوره مبارکه اخوت و همبستگی ایمانی",
        topic="اخوت و برادری",
        summary="منشور قرآنی انسجام امت اسلامی، پیوند برادری ایمانی، نفی تنازع و التزام جمعی به حبل‌الله.",
        is_featured=True,
        search_count=48
    )
    db.add(ts_brotherhood)

    ts_brotherhood_ayahs = [
        ThematicAyah(
            thematic_surah_id="ts_brotherhood_01",
            order_index=1,
            original_surah_id=3,
            original_surah_name="آل عمران",
            original_ayah_number=103,
            text_arabic="وَاعْتَصِمُوا بِحَبْلِ اللَّهِ جَمِيعًا وَلَا تَفَرَّقُوا ۚ وَاذْكُرُوا نِعْمَتَ اللَّهِ عَلَيْكُمْ إِذْ كُنتُمْ أَعْدَاءً فَأَلَّفَ بَيْنَ قُلُوبِكُمْ فَأَصْبَحْتُم بِنِعْمَتِهِ إِخْوَانًا",
            text_persian="و همگی به ریسمان خدا چنگ زنید و پراکنده نشوید؛ و نعمت خدا را بر خود به یاد آرید که دشمن یکدیگر بودید، و او میان دلهایتان الفت افکند و به نعمت او برادر شدید.",
            tafsir_lesson="تفسیر المیزان: تمسک به حبل‌الله ضامن صیانت از تشتت اجتماعی است و الفت قلوب، عطیه‌ای الهی فراتر از مناسبات مادی است.",
            reflection_question="چگونه می‌توانیم الفت قلبی را بر محور توحید در میان اطرافیان پایدار نگاه داریم؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/003103.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_brotherhood_01",
            order_index=2,
            original_surah_id=8,
            original_surah_name="الأنفال",
            original_ayah_number=46,
            text_arabic="وَأَطِيعُوا اللَّهَ وَرَسُولَهُ وَلَا تَنَازَعُوا فَتَفْشَلُوا وَتَذْهَبَ رِيحُكُمْ ۖ وَاصْبِرُوا ۚ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
            text_persian="و از خدا و پیامبرش اطاعت نمایید و با یکدیگر نزاع نکنید که سست می‌شوید و هیبت و قدرتتان از میان می‌رود؛ و شکیبایی ورزید که خدا با صابران است.",
            tafsir_lesson="تفسیر نمونه: نزاع درونی آفت عزت و اقتدار اجتماعی است و پایداری بر محور حق، شالوده بقای امت است.",
            reflection_question="کدام رفتارهای نسنجیده در گفتگوها منجر به شکستن اقتدار جمعی می‌شود؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/008046.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_brotherhood_01",
            order_index=3,
            original_surah_id=49,
            original_surah_name="الحجرات",
            original_ayah_number=10,
            text_arabic="إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ ۚ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ",
            text_persian="مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح و آشتی برقرار سازید و از خدا پروا کنید تا مورد رحمت قرار گیرید.",
            tafsir_lesson="تفسیر نور: رابطه مؤمنان با واژه حقوقی و عاطفی «اخوت» توصیف شده است؛ اصلاح ذات‌البین یک فریضه همگانی برای جلب رحمت پروردگار است.",
            reflection_question="امروز برای ترمیم روابط برادران ایمانی چه گام عملی می‌توان برداشت؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/049010.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_brotherhood_01",
            order_index=4,
            original_surah_id=59,
            original_surah_name="الحشر",
            original_ayah_number=9,
            text_arabic="وَالَّذِينَ تَبَوَّءُوا الدَّارَ وَالْإِيمَانَ مِن قَبْلِهِمْ يُحِبُّونَ مَنْ هَاجَرَ إِلَيْهِمْ وَلَا يَجِدُونَ فِي صُدُورِهِمْ حَاجَةً مِّمَّا أُوتُوا وَيُؤْثِرُونَ عَلَىٰ أَنفُسِهِمْ وَلَوْ كَانَ بِهِمْ خَصَاصَةٌ",
            text_persian="و کسانی که پیش از مهاجران در دیار خود و در سراسر ایمان جای گرفتند، مهاجران را دوست می‌دارند و در دل‌های خود کمبودی احساس نمی‌کنند و آنان را بر خود مقدم می‌دارند، هرچند خود نیاز مبرم داشته باشند.",
            tafsir_lesson="تفسیر المیزان: قله ایثار و نفی انحصارطلبی، تجلی راستین اخوت اسلامی در سیره انصار و مهاجران است.",
            reflection_question="تا چه اندازه حاضریم مصلحت برادر ایمانی‌مان را بر میل شخصی خود ترجیح دهیم؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/059009.mp3"
        )
    ]
    db.add_all(ts_brotherhood_ayahs)

    # 2. سوره صبر و پایمردی
    ts_patience = ThematicSurah(
        id="ts_patience_02",
        title="سوره مبارکه صبر و پایمردی در برابر سختی‌ها",
        topic="صبر و استقامت",
        summary="آیات استقامت، مددجویی از صلات و شکیبایی، بشارت پیروزی به صابران و پیوند عزم با توکل الهی.",
        is_featured=True,
        search_count=74
    )
    db.add(ts_patience)

    ts_patience_ayahs = [
        ThematicAyah(
            thematic_surah_id="ts_patience_02",
            order_index=1,
            original_surah_id=2,
            original_surah_name="البقرة",
            original_ayah_number=153,
            text_arabic="يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ ۚ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
            text_persian="ای کسانی که ایمان آورده‌اید! از شکیبایی و نماز یاری جویید؛ همانا خداوند با شکیبایان است.",
            tafsir_lesson="تفسیر نمونه: صبر استقامت درونی را بارور می‌سازد و نماز اتصال به فیض لایزال حق است؛ این دو بال پرواز مؤمن در عبور از بحران‌ها هستند.",
            reflection_question="در دشواری‌های اخیر، چقدر از اهرم نماز و شکیبایی برای آرامش بهره گرفته‌ایم؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/002153.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_patience_02",
            order_index=2,
            original_surah_id=2,
            original_surah_name="البقرة",
            original_ayah_number=155,
            text_arabic="وَلَنَبْلُوَنَّكُم بِشَيْءٍ مِّنَ الْخَوْفِ وَالْجُوعِ وَنَقْصٍ مِّنَ الْأَمْوَالِ وَالْأَنفُسِ وَالثَّمَرَاتِ ۗ وَبَشِّرِ الصَّابِرِينَ",
            text_persian="و قطعاً شما را با چیزی از ترس، گرسنگی، و کاستی در اموال و جان‌ها و محصولات می‌آزماییم؛ و مژده ده به شکیبایان.",
            tafsir_lesson="تفسیر المیزان: شدائد روزگار کلاس تکامل باطنی و آزمون خلوص دل‌ها هستند؛ بشارت الهی پاداش ویژه صابران است.",
            reflection_question="کدام یک از ناملایمات زندگی فرصتی برای پالایش روح و صبوری ما بوده است؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/002155.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_patience_02",
            order_index=3,
            original_surah_id=3,
            original_surah_name="آل عمران",
            original_ayah_number=200,
            text_arabic="يَا أَيُّهَا الَّذِينَ آمَنُوا اصْبِرُوا وَصَابِرُوا وَرَابِطُوا وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُفْلِحُونَ",
            text_persian="ای اهل ایمان! شکیبایی پیشه کنید، در برابر دشمنان پایداری افزون‌تر نمایید، پیوندها و مرزها را پاس دارید و تقوای الهی داشته باشید، شاید رستگار شوید.",
            tafsir_lesson="تفسیر نور: زنجیره چهارگانه رستگاری: صبر درونی فردی، هم‌افزایی شکیبایی اجتماعی، پیوند مرزبانی و تقواپیشگی.",
            reflection_question="چگونه می‌توانیم روحیه مقاومت جمعی را در خانواده و جامعه تقویت کنیم؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/003200.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_patience_02",
            order_index=4,
            original_surah_id=103,
            original_surah_name="العصر",
            original_ayah_number=3,
            text_arabic="إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ",
            text_persian="مگر کسانی که ایمان آورده و کارهای شایسته انجام داده‌اند و یکدیگر را به حق و شکیبایی سفارش نموده‌اند.",
            tafsir_lesson="تفسیر نمونه: تنها راه برون‌رفت از خسران قطعی گذر زمان، پیوند دوسویه تواصی به حق و تواصی به صبر است.",
            reflection_question="چه گام عملی برای سفارش دوجانبه به حق و شکیبایی در معاشرت‌هایمان برمی‌داریم؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/103003.mp3"
        )
    ]
    db.add_all(ts_patience_ayahs)

    # 3. سوره یاد خدا و آرامش دل‌ها
    ts_peace = ThematicSurah(
        id="ts_peace_03",
        title="سوره مبارکه یاد خدا و آرامش دل‌ها",
        topic="آرامش و ذکر خدا",
        summary="آیات نورانی تسکین قلب‌ها، جایگاه ذکر پروردگار در رفع تشویش‌ها و تجلی طمأنینه معنوی.",
        is_featured=True,
        search_count=52
    )
    db.add(ts_peace)

    ts_peace_ayahs = [
        ThematicAyah(
            thematic_surah_id="ts_peace_03",
            order_index=1,
            original_surah_id=13,
            original_surah_name="الرعد",
            original_ayah_number=28,
            text_arabic="الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللَّهِ ۗ أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
            text_persian="همان کسانی که ایمان آورده‌اند و دل‌هایشان به یاد خدا آرام می‌گیرد؛ آگاه باشید که با یاد خدا دل‌ها آرامش می‌یابد.",
            tafsir_lesson="تفسیر نمونه: ذات بی‌نهایت پروردگار تنها پناهگاه راستین و دافع اضطراب‌های بنیادین انسان است.",
            reflection_question="در لحظات اوج دغدغه فکری، چگونه یاد خدا را در عمق جان جاری کنیم؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/013028.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_peace_03",
            order_index=2,
            original_surah_id=20,
            original_surah_name="طه",
            original_ayah_number=14,
            text_arabic="إِنَّنِي أَنَا اللَّهُ لَا إِلَٰهَ إِلَّا أَنَا فَاعْبُدْنِي وَأَقِمِ الصَّلَاةَ لِذِكْرِي",
            text_persian="همانا من الله هستم، معبودی جز من نیست؛ پس مرا پرستش کن و برای یاد من نماز را برپا دار.",
            tafsir_lesson="تفسیر المیزان: جانمایه و روح اقامه صلات، استمرار یاد و توجه قلبی به پروردگار در کوران مشغله‌های دنیاست.",
            reflection_question="چگونه می‌توان کیفیت نماز را از یک عادت قالبی به منبع الهام‌بخش ذکر ارتقا داد؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/020014.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_peace_03",
            order_index=3,
            original_surah_id=33,
            original_surah_name="الأحزاب",
            original_ayah_number=41,
            text_arabic="يَا أَيُّهَا الَّذِينَ آمَنُوا اذْكُرُوا اللَّهَ ذِكْرًا كَثِيرًا وَسَبِّحُوهُ بُكْرَةً وَأَصِيلًا",
            text_persian="ای کسانی که ایمان آورده‌اید! خدا را بسیار یاد کنید و او را در هر صبح و شام تسبیح گویید.",
            tafsir_lesson="تفسیر نور: مداومت بر ذکر کثیر، قلب را در پناه غفلت‌ناپذیری قرار می‌دهد و شیطان را مایوس می‌سازد.",
            reflection_question="چه برنامه‌ای برای تسبیح و تذکر بامداد و شامگاه تنظیم کرده‌ایم؟",
            jev_score=9,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/033041.mp3"
        ),
        ThematicAyah(
            thematic_surah_id="ts_peace_03",
            order_index=4,
            original_surah_id=89,
            original_surah_name="الفجر",
            original_ayah_number=27,
            text_arabic="يَا أَيَّتُهَا النَّفْسُ الْمُطْمَئِنَّةُ ارْجِعِي إِلَىٰ رَبِّكِ رَاضِيَةً مَّرْضِيَّةً",
            text_persian="ای نفس مطمئن و آرام‌یافته! به سوی پروردگارت بازگرد در حالی که هم تو از او خشنودی و هم او از تو خشنود است.",
            tafsir_lesson="تفسیر المیزان: اوج بلوغ عبودیت، دستیابی به گوهر طمأنینه و رضای قلبی متقابل با محبوب ازلی است.",
            reflection_question="چه موانعی روح را از رسیدن به طمأنینه و رضایت از تقدیرات حق بازمی‌دارد؟",
            jev_score=10,
            audio_url="https://everyayah.com/data/Parhizgar_48kbps/089027.mp3"
        )
    ]
    db.add_all(ts_peace_ayahs)

    await db.commit()


async def seed_database(db: AsyncSession):
    # Ensure section configs are seeded even if DB already has other data
    await seed_section_configs_if_needed(db)
    # Ensure admin user is seeded even if DB already has other data
    await seed_admin_if_needed(db)
    # Ensure thematic surahs are seeded even if DB already has other data
    await seed_thematic_surahs_if_needed(db)

    # 1. Check if already seeded
    existing_surah = await db.scalar(select(Surah).limit(1))
    if existing_surah:
        # Core data already exists; ensure feed posts are seeded and return
        await seed_feed_if_needed(db)
        return  # Already seeded

    # 2. Seed Users
    seeker_user = User(
        id="usr_seeker_1",
        phone_number="09121111111",
        full_name="علی رضایی",
        hashed_password=hash_password("123456"),
        role="SEEKER",
        madhhab="شیعه اثناعشری",
        age=28,
        gender="MALE",
        education="کارشناسی ارشد مهندسی نرم‌افزار",
        interests=["TAFSIR", "AKHLAQ"],
        knowledge_level="ACADEMIC",
        learning_goals="آشنایی عمیق‌تر با مفاهیم تدبر در قرآن کریم و فضایل اخلاقی در نهج‌البلاغه",
        avatar="/media/avatars/user_1.png",
        created_at=utc_now()
    )
    scholar_user = User(
        id="usr_scholar_1",
        phone_number="09122222222",
        full_name="حجت‌الاسلام دکتر محمدرضا عابدی",
        hashed_password=hash_password("123456"),
        role="SCHOLAR",
        madhhab="شیعه اثناعشری",
        age=45,
        gender="MALE",
        education="دکتری مبانی فقه و حقوق اسلامی و سطح ۴ حوزه",
        interests=["FIQH", "KALAM", "TAFSIR"],
        knowledge_level="SEMINARY",
        learning_goals="پژوهش و پاسخگویی به شبهات فقهی و کلامی معاصر",
        avatar="/media/avatars/scholar_1.png",
        created_at=utc_now()
    )
    chk_seeker = await db.scalar(select(User).where(User.id == "usr_seeker_1"))
    if not chk_seeker:
        db.add(seeker_user)
    chk_scholar = await db.scalar(select(User).where(User.id == "usr_scholar_1"))
    if not chk_scholar:
        db.add(scholar_user)
    await db.flush()

    # 3. Persona Configurations
    chk_persona = await db.scalar(select(PersonaConfig).where(PersonaConfig.user_id == "usr_seeker_1"))
    if not chk_persona:
        seeker_persona = PersonaConfig(
            user_id="usr_seeker_1",
            bot_name="دستیار معارفی اتحاد",
            bot_role_preset="TAFSIR_RESEARCHER",
            bot_avatar="/media/avatars/bot_tafsir.png",
            tone="FRIENDLY_WARM",
            fiqh_approach="APPROXIMATION_UNITY",
            detail_level="STANDARD",
            include_ayah_address=True,
            include_hadith_references=True,
            custom_prompt_instructions="پاسخ‌ها را با مثال‌های ملموس و زبانی امیدبخش ارائه کن."
        )
        db.add(seeker_persona)

    # 4. Seed Scholars (6 scholars covering different madhhabs, cities, specialties)
    scholars_data = [
        Scholar(
            id="scholar_1",
            user_id="usr_scholar_1",
            name="حجت‌الاسلام دکتر محمدرضا عابدی",
            title="استاد سطوح عالی حوزه علمیه و دکترای فقه و حقوق",
            specialties=["احکام شرعی و فقهی", "معاملات و بورس", "مسائل نوین پزشکی"],
            rating=4.98,
            answer_count=542,
            response_time_hours=2,
            rank=1,
            avatar_color_hex="0xFF8C6239",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_1.jpg",
            is_verified=True,
            madhhab="شیعه اثناعشری",
            city="قم",
            mosque="مرکز فقهی ائمه اطهار (ع)",
            address="قم، میدان معلم، مرکز فقهی ائمه اطهار (ع)",
            latitude=34.6416,
            longitude=50.8746,
            meeting_slots=[
                {"day": "دوشنبه", "time": "۱۶:۰۰ الی ۱۸:۰۰", "location": "مرکز فقهی، اتاق مشاوره شماره ۲", "capacity": 6, "booked": 2},
                {"day": "چهارشنبه", "time": "۱۵:۳۰ الی ۱۷:۳۰", "location": "مرکز فقهی، سالن جلسات", "capacity": 5, "booked": 1}
            ],
            bio="دانش‌آموخته حوزه علمیه قم با بیش از ۱۵ سال سابقه پاسخگویی به استفتائات فقهی و مسائل نوین اقتصادی و بانکی."
        ),
        Scholar(
            id="scholar_2",
            name="ماموستا دکتر صلاح‌الدین محمدی",
            title="مدرس دارالافتاء و استاد فقه شافعی دانشگاه مذاهب",
            specialties=["احکام شرعی و فقهی", "مشاوره و خانواده", "تفسیر و معارف قرآن"],
            rating=4.95,
            answer_count=410,
            response_time_hours=3,
            rank=2,
            avatar_color_hex="0xFF2E7D32",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_2.jpg",
            is_verified=True,
            madhhab="اهل سنت (شافعی)",
            city="سنندج",
            mosque="دارالافتاء امام شافعی",
            address="سنندج، خیابان امام، مجتمع دارالافتاء امام شافعی",
            latitude=35.3113,
            longitude=46.9961,
            meeting_slots=[
                {"day": "یکشنبه", "time": "۱۰:۰۰ الی ۱۲:۰۰", "location": "دارالافتاء امام شافعی، طبقه اول", "capacity": 4, "booked": 1},
                {"day": "سه‌شنبه", "time": "۱۶:۰۰ الی ۱۸:۰۰", "location": "دارالافتاء امام شافعی، دفتر پاسخگویی", "capacity": 5, "booked": 0}
            ],
            bio="عالم و فقیه اهل سنت، پژوهشگر ارشد فقه مقارن و مشاور خانواده با سال‌ها سابقه تدریس در حوزه‌های علمیه اهل سنت."
        ),
        Scholar(
            id="scholar_3",
            name="مولوی عبدالکریم آخوند گرگانی",
            title="مدیر حوزه علمیه و مفتی اهل سنت (حنفی)",
            specialties=["احکام شرعی و فقهی", "اعتقادی و کلامی", "اخلاق و سیر و سلوک"],
            rating=4.92,
            answer_count=380,
            response_time_hours=4,
            rank=3,
            avatar_color_hex="0xFF1565C0",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_3.jpg",
            is_verified=True,
            madhhab="اهل سنت (حنفی)",
            city="گرگان",
            mosque="مسجد جامع اهل سنت",
            address="گرگان، خیابان شهدا، کوچه حوزه علمیه اهل سنت",
            latitude=36.8451,
            longitude=54.4328,
            meeting_slots=[
                {"day": "شنبه", "time": "۱۵:۰۰ الی ۱۷:۰۰", "location": "مسجد جامع اهل سنت، شبستان غربی", "capacity": 8, "booked": 3}
            ],
            bio="مفتی حنفی و استاد برجسته فقه و حدیث در حوزه علمیه اهل سنت شمال کشور."
        ),
        Scholar(
            id="scholar_4",
            name="آیت‌الله سید مرتضی علوی حسینی",
            title="استاد درس خارج فقه و اصول و عضو مجمع عالی حکمت",
            specialties=["اعتقادی و کلامی", "اخلاق و سیر و سلوک", "تفسیر و معارف قرآن"],
            rating=4.99,
            answer_count=620,
            response_time_hours=2,
            rank=4,
            avatar_color_hex="0xFF6A1B9A",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_4.jpg",
            is_verified=True,
            madhhab="شیعه اثناعشری",
            city="مشهد",
            mosque="حرم مطهر رضوی (ع)",
            address="مشهد مقدس، حرم مطهر، دارالقرآن الکریم، صحن انقلاب",
            latitude=36.2878,
            longitude=59.6157,
            meeting_slots=[
                {"day": "شنبه", "time": "۱۶:۳۰ الی ۱۸:۳۰", "location": "حرم مطهر، صحن جمهوری اسلامی، اتاق گفتمان", "capacity": 10, "booked": 4},
                {"day": "پنجشنبه", "time": "۱۰:۰۰ الی ۱۲:۰۰", "location": "حرم مطهر، دارالقرآن، اتاق ۱۲", "capacity": 6, "booked": 2}
            ],
            bio="مدرس باسابقه حکمت، کلام تطبیقی و اخلاق در جوار بارگاه منور رضوی."
        ),
        Scholar(
            id="scholar_5",
            name="حجت‌الاسلام دکتر علیرضا پناهی",
            title="دکترای روانشناسی اسلامی و مشاور ارشد فقه تربیتی",
            specialties=["مشاوره و خانواده", "اخلاق و سیر و سلوک"],
            rating=4.88,
            answer_count=310,
            response_time_hours=3,
            rank=5,
            avatar_color_hex="0xFFD84315",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_5.jpg",
            is_verified=True,
            madhhab="شیعه اثناعشری",
            city="تهران",
            mosque="مسجد دانشگاه تهران",
            address="تهران، میدان انقلاب، خیابان ۱۶ آذر، نهاد رهبری دانشگاه تهران",
            latitude=35.7032,
            longitude=51.3937,
            meeting_slots=[
                {"day": "یکشنبه", "time": "۱۴:۰۰ الی ۱۶:۰۰", "location": "مسجد دانشگاه تهران، دفتر مشاوره دینی", "capacity": 6, "booked": 2},
                {"day": "سه‌شنبه", "time": "۱۶:۰۰ الی ۱۸:۰۰", "location": "مسجد دانشگاه تهران، دفتر مشاوره دینی", "capacity": 5, "booked": 3}
            ],
            bio="مشاور تخصصی خانواده و ازدواج با رویکرد تعمیق ایمان و معارف دینی."
        ),
        Scholar(
            id="scholar_6",
            name="شیخ احمد عبدالملکی",
            title="مدرس علوم قرآن و حدیث دارالعلم شیراز",
            specialties=["تفسیر و معارف قرآن", "اعتقادی و کلامی"],
            rating=4.85,
            answer_count=290,
            response_time_hours=5,
            rank=6,
            avatar_color_hex="0xFF00838F",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_6.jpg",
            is_verified=True,
            madhhab="اهل سنت (شافعی)",
            city="شیراز",
            mosque="مسجد رسول اکرم (ص)",
            address="شیراز، خیابان زند، جنب مسجد رسول اکرم (ص)",
            latitude=29.6105,
            longitude=52.5350,
            meeting_slots=[
                {"day": "چهارشنبه", "time": "۱۷:۰۰ الی ۱۹:۰۰", "location": "دارالعلم شیراز، دفتر قرآن و حدیث", "capacity": 5, "booked": 1}
            ],
            bio="پژوهشگر علوم بلاغت و تفسیر قرآن کریم با تأکید بر محورهای تقریب و وحدت امت اسلامی."
        ),
        Scholar(
            id="scholar_7",
            name="حجت‌الاسلام والمسلمین سید علی حسینی کاشانی",
            title="امام جماعت و مدرس اخلاق و احکام معارف غرب تهران",
            specialties=["احکام شرعی و فقهی", "اخلاق و سیر و سلوک"],
            rating=4.94,
            answer_count=350,
            response_time_hours=2,
            rank=7,
            avatar_color_hex="0xFF303F9F",
            avatar_url="https://cdn.ettehad.app/avatars/scholar_7.jpg",
            is_verified=True,
            madhhab="شیعه اثناعشری",
            city="تهران",
            mosque="مسجد امام صادق (ع) صادقیه",
            address="تهران، فلکه دوم صادقیه، ابتدای بزرگراه اشرفی اصفهانی، مسجد امام صادق (ع)",
            latitude=35.7235,
            longitude=51.3355,
            meeting_slots=[
                {"day": "دوشنبه", "time": "۱۷:۰۰ الی ۱۹:۰۰", "location": "دفتر پاسخگویی مسجد امام صادق (ع)", "capacity": 6, "booked": 1},
                {"day": "پنجشنبه", "time": "۱۸:۰۰ الی ۲۰:۰۰", "location": "دفتر پاسخگویی مسجد امام صادق (ع)", "capacity": 8, "booked": 2}
            ],
            bio="مدرس حوزه و مروج معارف اهل‌بیت، پاسخگوی احکام شرعی و مشاور جوانان در غرب تهران."
        )
    ]
    for sch in scholars_data:
        existing_sch = await db.scalar(select(Scholar).where(Scholar.id == sch.id))
        if not existing_sch:
            db.add(sch)
        else:
            if not existing_sch.user_id and sch.user_id:
                existing_sch.user_id = sch.user_id
    await db.flush()

    # 5. Scholar Quick Replies
    quick_replies = [
        ScholarQuickReply(id="qr_1", scholar_id="scholar_1", title="سلام و احوالپرسی گرم", content="سلام علیکم و رحمة الله. پرسش شما دریافت شد و با دقت در حال بررسی فقهی است.", category="احوالپرسی"),
        ScholarQuickReply(id="qr_2", scholar_id="scholar_1", title="ارجاع به نظر مرجع تقلید", content="طبق نظر اکثر مراجع عظام تقلید، در این فرض عمل مذکور جایز بوده و شبهه‌ای بر آن وارد نیست.", category="ارجاع به مرجع"),
        ScholarQuickReply(id="qr_3", scholar_id="scholar_1", title="نصیحت و توصیه اخلاقی", content="توصیه برادرانه این حقیر آن است که احتیاط را پیشه سازید تا قلبتان همواره در آرامش و تقوا آرام گیرد.", category="نصیحت اخلاقی"),
        ScholarQuickReply(id="qr_4", scholar_id="scholar_1", title="اعلام بررسی پرونده", content="سلام علیکم. برای پاسخ دقیق، آیا می‌توانید جزئیات بیشتری درباره شرایط قرارداد مطرح نمایید؟", category="اعلام بررسی"),
    ]
    for qr in quick_replies:
        chk_qr = await db.scalar(select(ScholarQuickReply).where(ScholarQuickReply.id == qr.id))
        if not chk_qr:
            db.add(qr)
    await db.flush()

    # 6. Sample Consultation Thread & Message
    sample_thread = ConsultationThread(
        id="thread_839210",
        user_id="usr_seeker_1",
        target_scholar_id="scholar_1",
        title="حکم خمس سود سرمایه‌گذاری و صندوق‌های طلا",
        category="احکام شرعی و فقهی",
        tracking_code="ETH-Q-49201",
        status="WAITING_SCHOLAR",
        is_anonymous=False,
        is_public=True,
        is_urgent=False,
        is_bookmarked=False
    )
    chk_th = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == sample_thread.id))
    if not chk_th:
        db.add(sample_thread)
    await db.flush()

    sample_msg = ConsultationMessage(
        id="msg_8210",
        thread_id="thread_839210",
        sender_id="usr_seeker_1",
        sender_role="SEEKER",
        text="سلام علیکم. اگر مقداری طلا یا واحدهای صندوق درآمد ثابت جهت حفظ ارزش پول تا سر سال خمسی نگهداری شود، آیا خمس به آن تعلق می‌گیرد؟",
        citation=None,
        is_read=True
    )
    chk_msg = await db.scalar(select(ConsultationMessage).where(ConsultationMessage.id == sample_msg.id))
    if not chk_msg:
        db.add(sample_msg)
    await db.flush()

    # 7. Library Categories
    categories = [
        LibraryCategory(id="cat_quran", title="قرآن و تفسیر", icon_name="menu_book", order_index=1),
        LibraryCategory(id="cat_hadith", title="حدیث و کلام", icon_name="auto_stories", order_index=2),
        LibraryCategory(id="cat_fiqh", title="فقه و احکام", icon_name="gavel", order_index=3),
        LibraryCategory(id="cat_akhlaq", title="اخلاق و عرفان", icon_name="spa", order_index=4),
        LibraryCategory(id="cat_history", title="تاریخ و سیره", icon_name="history_edu", order_index=5),
        LibraryCategory(id="cat_philosophy", title="علوم عقلی", icon_name="psychology", order_index=6),
        LibraryCategory(id="cat_novel", title="پاییز و رمان", icon_name="import_contacts", order_index=7),
        LibraryCategory(id="cat_travel", title="سفرنامه و خاطرات", icon_name="explore", order_index=8),
    ]
    for cat in categories:
        chk_cat = await db.scalar(select(LibraryCategory).where(LibraryCategory.id == cat.id))
        if not chk_cat:
            db.add(cat)
    await db.flush()

    # 8. Library Posters
    posters = [
        LibraryPoster(
            id="poster_1",
            title="منشور طلایی وحدت امت",
            subtitle="بررسی تطبیقی آیات برادری در تفاسیر فریقین",
            image_url="https://cdn.ettehad.app/library/posters/poster_unity.jpg",
            target_book_id="book_nahj",
            order_index=1
        ),
        LibraryPoster(
            id="poster_2",
            title="چهل حدیث در کمال اخلاق",
            subtitle="سیری در حکمت‌های ناب نبوی و علوی",
            image_url="https://cdn.ettehad.app/library/posters/poster_hadith.jpg",
            target_book_id="book_forty_hadith",
            order_index=2
        )
    ]
    for p in posters:
        chk_p = await db.scalar(select(LibraryPoster).where(LibraryPoster.id == p.id))
        if not chk_p:
            db.add(p)
    await db.flush()

    # 9. Books and Chapters
    book1 = Book(
        id="book_nahj",
        title="نهج‌البلاغه (ترجمه و شرح برگزیده)",
        author="امام علی بن ابی‌طالب (ع) / سید رضی",
        translator="استاد حسین انصاریان",
        publisher="انتشارات دارالعرفان",
        publication_year="۱۴۰۱",
        cover_url="https://cdn.ettehad.app/library/covers/nahj.jpg",
        category_id="cat_hadith",
        is_featured=True,
        tags=["نهج البلاغه", "حکمت", "اخلاق", "سیاست علوی", "وحدت"],
        topics=["توحید و خداشناسی", "آفرینش جهان و انسان", "حکومت‌داری و عدالت اجتماعی", "پندهای تربیتی و اخلاقی", "حقوق متقابل مردم و حاکم"],
        description="جامع‌ترین اثر دربردارنده خطبه‌ها، نامه‌ها و حکمت‌های شگرف امیر مؤمنان علی (ع) با رویکرد اصلاح فرد و جامعه.",
        page_count=650,
        rating=4.98
    )
    book2 = Book(
        id="book_forty_hadith",
        title="چهل حدیث اخلاقی و معنوی",
        author="محدث نوری و جمعی از پژوهشگران",
        translator="سید مهدی شجاعی",
        publisher="نشر نیستان",
        publication_year="۱۴۰۰",
        cover_url="https://cdn.ettehad.app/library/covers/forty_hadith.jpg",
        category_id="cat_akhlaq",
        is_featured=True,
        tags=["حدیث", "اخلاق", "سیر و سلوک", "روایات نبوی"],
        topics=["سیر و سلوک معنوی", "تهذیب نفس و مکارم اخلاق", "برادری ایمانی و مدارا", "حقوق برادر دینی", "اخلاص در عمل"],
        description="گزیده‌ای فاخر از احادیث صحیح‌السند پیامبر اعظم (ص) و ائمه اطهار (ع) درباره مکارم اخلاق، برادری و بندگی خالصانه.",
        page_count=280,
        rating=4.95
    )
    book_fake = Book(
        id="bk_fake_wahdat_01",
        title="رساله اخوت و حقوق متقابل مؤمنان (کتاب آزمایشی)",
        author="دکتر حمیدرضا مهدوی و هیئت علمی پژوهشکده تقریب",
        translator=None,
        publisher="انتشارات دارالتقریب و مجمع جهانی اتحاد",
        publication_year="۱۴۰۳",
        cover_url="https://cdn.ettehad.app/library/covers/wahdat_treatise.jpg",
        category_id="cat_akhlaq",
        is_featured=True,
        tags=["کتاب تستی", "وحدت اسلامی", "اخلاق اجتماعی", "فقه مقارن", "حقوق برادری"],
        topics=["برادری ایمانی", "کرامت انسانی", "آداب گفتگو و مناظره", "حرمت تعرض به جان و مال مسلمان"],
        description="اثر پژوهشی و آزمایشی جهت تبیین مبانی قرآنی، روایی و عقلانی همبستگی میان مذاهب اسلامی و بررسی آداب معاشرت و مدارا در زیست معاصر مسلمانان.",
        language="fa",
        page_count=240,
        rating=4.92
    )
    for b in [book1, book2, book_fake]:
        chk_b = await db.scalar(select(Book).where(Book.id == b.id))
        if not chk_b:
            db.add(b)
    await db.flush()

    ch1_paragraphs = [
        "حمد و سپاس خداوندی را سزاست که ستایش‌کنندگان از عهده ستایشش برنیایند و شمارندگان نعمت‌هایش را نشمارند.",
        "خدایی که افکار دوراندیش به ژرفای ذاتش نرسد و غواصان فهم و اندیشه به کنه وجودش دست نیابند.",
        "سرآغاز دین معرفت اوست و کمال معرفتش تصدیق او، و کمال تصدیقش توحید اوست."
    ]
    chapter1 = BookChapter(
        id="chap_nahj_1",
        book_id="book_nahj",
        chapter_number=1,
        title="خطبه نخست: در آفرینش جهان و انسان و بعثت انبیاء",
        reading_time_minutes=8,
        content="\n\n".join(ch1_paragraphs),
        paragraphs=ch1_paragraphs
    )
    chapter2 = BookChapter(
        id="chap_nahj_2",
        book_id="book_nahj",
        chapter_number=2,
        title="نامه ۵۳: فرمان تاریخی مالک اشتر نخعی در منشور حکمرانی",
        reading_time_minutes=15,
        content="مهربانی با مردم را پوشش دل خویش قرار ده و با آنان مدارا و محبت کن؛ زیرا مردم دو دسته‌اند: یا برادر دینی تواند یا در آفرینش همانند تو.",
        paragraphs=[
            "مهربانی با مردم را پوشش دل خویش قرار ده و با آنان مدارا و محبت کن.",
            "مردم دو دسته‌اند: یا برادر دینی تواند و یا در آفرینش همانند تو؛ پس با آنان همان‌گونه رفتار کن که دوست داری خداوند با تو رفتار کند."
        ]
    )
    fake_ch1 = BookChapter(
        id="chap_fake_01",
        book_id="bk_fake_wahdat_01",
        chapter_number=1,
        title="فصل اول: اصل کرامت تکوینی و اخوت ایمانی در قرآن و سنت",
        reading_time_minutes=7,
        content="پیوند برادری ایمانی در تفکر توحیدی، نه یک تعارف اجتماعی زودگذر و نه صرفاً قرارداد صوری حقوقی است؛ بلکه عهدنامه‌ای ژرف و تکوینی است که مؤمنان را بسان اندام‌های یک کالبد زنده به یکدیگر پیوند می‌دهد.\nخداوند متعال در سوره مبارکه حجرات آیه ۱۰ می‌فرماید: «إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ».",
        paragraphs=[
            "پیوند برادری ایمانی در تفکر توحیدی، نه یک تعارف اجتماعی زودگذر و نه صرفاً قرارداد صوری حقوقی است؛ بلکه عهدنامه‌ای ژرف و تکوینی است که مؤمنان را بسان اندام‌های یک کالبد زنده به یکدیگر پیوند می‌دهد.",
            "خداوند متعال در سوره مبارکه حجرات آیه ۱۰ می‌فرماید: «إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ»."
        ]
    )
    for ch in [chapter1, chapter2, fake_ch1]:
        chk_ch = await db.scalar(select(BookChapter).where(BookChapter.id == ch.id))
        if not chk_ch:
            db.add(ch)
    await db.flush()

    # 10. Reciters
    reciters = [
        Reciter(id="parhizgar", name_fa="استاد شهریار پرهیزگار", name_ar="شهريار پرهيزگار", style="ترتیل آموزشی و دقیق", bitrate="128kbps", is_default=True),
        Reciter(id="abdulbasit", name_fa="استاد عبدالباسط عبدالصمد", name_ar="عبد الباسط عبد الصمد", style="ترتیل مجلسی مرصع", bitrate="192kbps", is_default=False),
        Reciter(id="menshawi", name_fa="استاد محمد صدیق منشاوی", name_ar="محمد صديق المنشاوي", style="ترتیل حزین و خاشعانه", bitrate="128kbps", is_default=False),
        Reciter(id="hussary", name_fa="استاد محمود خلیل الحصری", name_ar="محمود خليل الحصري", style="تحقیق و تجوید کلاسی", bitrate="128kbps", is_default=False)
    ]
    for r in reciters:
        chk_r = await db.scalar(select(Reciter).where(Reciter.id == r.id))
        if not chk_r:
            db.add(r)
    await db.flush()

    # 11. Complete Catalog of 114 Surahs
    surahs_manifest = [
        (1, "الفاتحة", "حمد (فاتحه)", "Al-Fatihah", 7, "MAKKI", 1, 5, 1, 1, "ام‌الکتاب، منشور بندگی و رحمت، شفابخش دل‌ها و ستون نماز."),
        (2, "البقرة", "بقره", "Al-Baqarah", 286, "MADANI", 1, 87, 2, 49, "طولانی‌ترین سوره قرآن شامل احکام اجتماعی، توحید، آیت‌الکرسی و داستان ابراهیم (ع)."),
        (3, "آل عمران", "آل عمران", "Ali 'Imran", 200, "MADANI", 3, 89, 50, 76, "دعوت به ثبات قدم، چنگ زدن به حبل‌الله، ماجرای جنگ احد و مریم مقدس."),
        (4, "النساء", "نساء", "An-Nisa", 176, "MADANI", 4, 92, 77, 106, "احکام خانواده، حقوق زنان و یتیمان، عدالت اجتماعی و قوانین ارث."),
        (5, "المائدة", "مائده", "Al-Ma'idah", 120, "MADANI", 6, 112, 106, 127, "وفای به عهد، احکام حلال و حرام، غدیر خم و ولایت، و داستان هابیل و قابیل."),
        (6, "الأنعام", "انعام", "Al-An'am", 165, "MAKKI", 7, 55, 128, 150, "توحید ناب، مبارزه با شرک و خرافات، و دلایل عظمت پروردگار در آفرینش."),
        (7, "الأعراف", "اعراف", "Al-A'raf", 206, "MAKKI", 8, 39, 151, 176, "داستان پیامبران پیشین، میثاق الست، سرگذشت بنی‌اسرائیل و هشدار به غافلان."),
        (8, "الأنفال", "انفال", "Al-Anfal", 75, "MADANI", 9, 88, 177, 186, "مسائل جهاد و دفاع، جنگ بدر، غنائم و عوامل پیروزی و امدادهای غیبی."),
        (9, "التوبة", "توبه (برائت)", "At-Tawbah", 129, "MADANI", 10, 113, 187, 207, "برائت از مشرکان پیمان‌شکن، انفاق و زکات، و فضیلت توبه و بازگشت به حق."),
        (10, "يونس", "یونس", "Yunus", 109, "MAKKI", 11, 51, 208, 221, "حقانیت وحی، سنت‌های الهی در تاریخ، و نجات یونس و پیروانش."),
        (11, "هود", "هود", "Hud", 123, "MAKKI", 11, 52, 221, 235, "استقامت در مسیر حق، داستان نوح و طوفان بزرگ، و هشدار به ظالمان."),
        (12, "يوسف", "یوسف", "Yusuf", 111, "MAKKI", 12, 53, 235, 248, "احسن‌القصص قرآن، عفت و پاکدامنی، صبر در برابر ابتلائات و صعود از قعر چاه به عزت مصر."),
        (13, "الرعد", "رعد", "Ar-Ra'd", 43, "MADANI", 13, 96, 249, 255, "نشانه‌های حقانیت قرآن، قوانین جهان هستی و آرامش دل‌ها با ذکر خدا."),
        (14, "إبراهيم", "ابراهیم", "Ibrahim", 52, "MAKKI", 13, 72, 255, 261, "رسالت پیامبران برای هدایت از تاریکی به نور، و دعاهای توحیدی حضرت ابراهیم."),
        (15, "الحجر", "حجر", "Al-Hijr", 99, "MAKKI", 14, 54, 262, 267, "تضمین الهی بر حفظ قرآن از تحریف، آفرینش انسان و سرکشی ابلیس."),
        (16, "النحل", "نحل", "An-Nahl", 128, "MAKKI", 14, 70, 267, 281, "نعمت‌های بی‌کران الهی، الهام به زنبور عسل، شکرگزاری و احکام عدل و احسان."),
        (17, "الإسراء", "اسراء (بنی‌اسرائیل)", "Al-Isra", 111, "MAKKI", 15, 50, 282, 293, "معراج پیامبر، منشور اخلاق اجتماعی و نیکی به والدین، و شأن نزول روح."),
        (18, "الكهف", "کهف", "Al-Kahf", 110, "MAKKI", 15, 69, 293, 304, "داستان اصحاب کهف، همراهی موسی و خضر، و ذوالقرنین و سد یاجوج و ماجوج."),
        (19, "مريم", "مریم", "Maryam", 98, "MAKKI", 16, 44, 305, 312, "میلاد اعجازآمیز یحیی و عیسی (ع)، طهارت مریم عذرا و رحمت الهی بر بندگان صالح."),
        (20, "طه", "طه", "Ta-Ha", 135, "MAKKI", 16, 45, 312, 321, "دلجویی از پیامبر، شرح صدر، داستان موسی در کوه طور و مقابله با فرعون و سامری."),
        (21, "الأنبياء", "انبیاء", "Al-Anbiya", 112, "MAKKI", 17, 73, 322, 331, "یادآوری ۱۶ پیامبر بزرگ الهی، پیروزی حق بر باطل و وراثت صالحان بر زمین."),
        (22, "الحج", "حج", "Al-Hajj", 78, "MADANI", 17, 103, 332, 341, "فلسفه مناسک حج ابراهیمی، زلزله رستاخیز و دفاع مشروع از مظلومان."),
        (23, "المؤمنون", "مؤمنون", "Al-Mu'minun", 118, "MAKKI", 18, 74, 342, 349, "ویژگی‌های رستگاران حقیقی در نماز، امانتداری، دوری از لغو و وفای به عهد."),
        (24, "النور", "نور", "An-Nur", 64, "MADANI", 18, 102, 350, 359, "آیه نور، عفت و پاکدامنی، احکام حجاب و آداب اذن ورود به حریم دیگران."),
        (25, "الفرقان", "فرقان", "Al-Furqan", 77, "MAKKI", 18, 42, 359, 366, "معیار تمایز حق از باطل، و اوصاف برجسته بندگان خاص خدای رحمان (عبادالرحمن)."),
        (26, "الشعراء", "شعراء", "Ash-Shu'ara", 227, "MAKKI", 19, 47, 367, 376, "مسئولیت سنگین پیامبران در برابر لجاجت طاغوت‌ها و رسالت متعهدانه سخن."),
        (27, "النمل", "نمل", "An-Naml", 93, "MAKKI", 19, 48, 377, 385, "حکومت سلیمان، فهم زبان مورچگان و هدهد، و ماجرای ملکه سبأ."),
        (28, "القصص", "قصص", "Al-Qasas", 88, "MAKKI", 20, 49, 385, 396, "تولد موسی، افکندن به نیل، فرجام قارون حریص و نوید حکومت مستضعفان."),
        (29, "العنكبوت", "عنکبوت", "Al-'Ankabut", 69, "MAKKI", 20, 85, 396, 404, "آزمون ایمان در کوره ابتلائات، سستی تکیه‌گاه‌های غیرخدا چون خانه عنکبوت."),
        (30, "الروم", "روم", "Ar-Rum", 60, "MAKKI", 21, 84, 404, 410, "پیش‌گویی پیروزی روم، نشانه‌های شگفت آفرینش در پیوند همسران و فصول حیات."),
        (31, "لقمان", "لقمان", "Luqman", 34, "MAKKI", 21, 57, 411, 414, "پندهای ناب حکیمانه لقمان به فرزندش در توحید، نماز، تواضع و صبر."),
        (32, "السجدة", "سجده", "As-Sajdah", 30, "MAKKI", 21, 75, 415, 417, "عظمت قرآن، سجده شبانه صالحان و پاداش پنهان چشم‌روشنی بهشتیان."),
        (33, "الأحزاب", "احزاب", "Al-Ahzab", 73, "MADANI", 21, 90, 418, 427, "نبرد خندق، الگوی حسنه نبوی، آیه تطهیر اهل‌بیت و شأن امهات المؤمنین."),
        (34, "سبأ", "سبأ", "Saba", 54, "MAKKI", 22, 58, 428, 434, "داوود و سلیمان، تمدن سبأ و سیل ویرانگر عرم، و حسابرسی قطعی اعمال."),
        (35, "فاطر", "فاطر", "Fatir", 45, "MAKKI", 22, 43, 434, 440, "آفریننده بال‌های فرشتگان، نیاز مطلق انسان و بی‌نیازی خداوند غنی و حمید."),
        (36, "يس", "یس (قلب قرآن)", "Ya-Sin", 83, "MAKKI", 22, 41, 440, 445, "قلب قرآن کریم، براهین زنده شدن مردگان، حرکت خورشید و ماه در فلک منظم."),
        (37, "الصافات", "صافات", "As-Saffat", 182, "MAKKI", 23, 56, 446, 452, "فرشتگان صف‌کشیده، ماجرای ذبح اسماعیل، و درود بر نوح، ابراهیم و موسی."),
        (38, "ص", "ص", "Sad", 88, "MAKKI", 23, 38, 453, 458, "حکمت و قضاوت داوود، ابتلای ایوب صابر، و توطئه ازلی ابلیس در سجده بر آدم."),
        (39, "الزمر", "زمر", "Az-Zumar", 75, "MAKKI", 23, 59, 458, 467, "اخلاص در دین، آیه مژده رحمت بیکران الهی بر گناهکاران نادم، و سوق دادن پرهیزگاران به بهشت."),
        (40, "غافر", "غافر (مؤمن)", "Ghafir", 85, "MAKKI", 24, 60, 467, 476, "بخشنده گناه و پذیرنده توبه، ماجرای ایمان مؤمن آل‌فرعون و نیایش فرشتگان حامل عرش."),
        (41, "فصلت", "فصلت", "Fussilat", 54, "MAKKI", 24, 61, 477, 482, "روشنی آیات قرآن، پاسخ بدی با نیکی، و گواهی دادن پوست و گوش انسان در قیامت."),
        (42, "الشورى", "شوری", "Ash-Shura", 53, "MAKKI", 25, 62, 483, 489, "مشورت در امور اجتماعی امت، وحدت شریعت‌های آسمانی و مودت اهل‌بیت (ع)."),
        (43, "الزخرف", "زخرف", "Az-Zukhruf", 89, "MAKKI", 25, 63, 489, 495, "بی‌ارزشی تجملات زودگذر دنیا، و ماندگاری تقوا و دوستی‌های پاک در قیامت."),
        (44, "الدخان", "دخان", "Ad-Dukhan", 59, "MAKKI", 25, 64, 496, 498, "نزول قرآن در شب فرخنده قدر و پیش‌بینی رویدادهای آخرالزمانی."),
        (45, "الجاثية", "جاثیه", "Al-Jathiyah", 37, "MAKKI", 25, 65, 499, 502, "زانوزدن امت‌ها در دادگاه عدل الهی، و نشانه‌های توحید در آفاق و انفس."),
        (46, "الأحقاف", "احقاف", "Al-Ahqaf", 35, "MAKKI", 26, 66, 502, 506, "نیکی به پدر و مادر، استقامت اولوالعزم و سرنوشت قوم عاد در ریگستان احقاف."),
        (47, "محمد", "محمد (ص)", "Muhammad", 38, "MADANI", 26, 95, 507, 510, "پاداش ایمان به پیامبر رحمت، فرجام منافقان و تمایز اصحاب حق و باطل."),
        (48, "الفتح", "فتح", "Al-Fath", 29, "MADANI", 26, 111, 511, 515, "فتح مبین صلح حدیبیه، بیعت رضوان و اوصاف مؤمنان همراه پیامبر (اشداء علی الکفار رحماء بینهم)."),
        (49, "الحجرات", "حجرات", "Al-Hujurat", 18, "MADANI", 26, 106, 515, 517, "منشور اخلاق معاشرت، پیوند برادری اسلامی، نهی از غیبت، تجسس و مسخره‌کردن و معیار تقوا."),
        (50, "ق", "ق", "Qaf", 45, "MAKKI", 26, 34, 518, 520, "حقیقت رستاخیز، نزدیکی خداوند به انسان از رگ گردن، و فرشتگان ثبت اعمال."),
        (51, "الذاريات", "ذاریات", "Adh-Dhariyat", 60, "MAKKI", 26, 67, 520, 523, "هدف آفرینش جن و انس در بندگی و عبادت، و رزاقیت بی‌دریغ پروردگار."),
        (52, "الطور", "طور", "At-Tur", 49, "MAKKI", 27, 76, 523, 525, "سوگند به طور سینا، حقانیت وعده عذاب و سیمای سراسر نشاط بهشتیان."),
        (53, "النجم", "نجم", "An-Najm", 62, "MAKKI", 27, 23, 526, 528, "عصمت وحیانی کلام رسول‌الله، معراج تا سدرةالمنتهی و رد شرک بت‌ها."),
        (54, "القمر", "قمر", "Al-Qamar", 55, "MAKKI", 27, 37, 528, 531, "معجزه شق‌القمر، آسانی قرآن برای پندآموزی و فرجام اقوام طغیان‌گر."),
        (55, "الرحمن", "الرحمن (عروس قرآن)", "Ar-Rahman", 78, "MADANI", 27, 97, 531, 534, "عروس قرآن، شمارش نعمت‌های الهی و تکرار پرطنین (فبای آلاء ربکما تکذبان)."),
        (56, "الواقعة", "واقعه", "Al-Waqi'ah", 96, "MAKKI", 27, 46, 534, 537, "دسته‌بندی انسان‌ها در قیامت به سابقون مقرب، اصحاب یمین و اصحاب شمال."),
        (57, "الحديد", "حدید", "Al-Hadid", 29, "MADANI", 27, 94, 537, 541, "انفاق پیش از فتح، منافع شگرف آهن برای قسط و داد، و تقوای نورافشان."),
        (58, "المجادلة", "مجادله", "Al-Mujadilah", 22, "MADANI", 28, 105, 542, 545, "شنیده شدن ندای زن مظلوم، نجوا و آداب مجالس، و برتری حزب‌الله."),
        (59, "الحشر", "حشر", "Al-Hashr", 24, "MADANI", 28, 101, 545, 548, "ایثار انصار نسبت به مهاجرین، تأمل در عظمت قرآن بر کوه‌ها و اسامی حسنای الهی."),
        (60, "الممتحنة", "ممتحنه", "Al-Mumtahanah", 13, "MADANI", 28, 91, 549, 551, "مرزبندی دوستی با دشمنان خدا، الگوی حضرت ابراهیم و مدارا با غیرمسلمانان مسالمت‌جو."),
        (61, "الصف", "صف", "As-Saff", 14, "MADANI", 28, 109, 551, 553, "جهاد در صف‌های به‌هم‌پیوسته سربی، مژده عیسی (ع) به نام مبارک احمد (ص) و تجارت پرسود ایمان."),
        (62, "الجمعة", "جمعه", "Al-Jumu'ah", 11, "MADANI", 28, 110, 553, 554, "فلسفه بعثت در تزکیه و تعلیم، نقد عالمان بی‌عمل چون حمار حامل کتاب، و دعوت به نماز جمعه."),
        (63, "المنافقون", "منافقون", "Al-Munafiqun", 11, "MADANI", 28, 104, 554, 555, "چهره‌گشایی از نفاق پنهان، خطرات ثروت و فرزند در غفلت از یاد خدا."),
        (64, "التغابن", "تغابن", "At-Taghabun", 18, "MADANI", 28, 108, 556, 557, "روز حسرت و آشکار شدن سود و زیان حقیقی، و انفاق وام نیکو (قرض‌الحسنه) به پروردگار."),
        (65, "الطلاق", "طلاق", "At-Talaq", 12, "MADANI", 28, 99, 558, 559, "احکام مداراجویانه طلاق، حفظ حرمت‌ها، و مژده گشایش پس از تنگی برای اهل تقوا."),
        (66, "التحريم", "تحریم", "At-Tahrim", 12, "MADANI", 28, 107, 560, 561, "توبه نصوح و خالص، الگوی مؤمنان در آسیه همسر فرعون و مریم دخت عمران."),
        (67, "الملك", "ملک (تبارک)", "Al-Mulk", 30, "MAKKI", 29, 77, 562, 564, "آفرینش مرگ و زندگی برای آزمون نیکوترین عمل، و شگفتی آسمان‌های هفتگانه."),
        (68, "القلم", "قلم", "Al-Qalam", 52, "MAKKI", 29, 2, 564, 566, "سوگند به قلم و آنچه می‌نگارد، تجلیل از اخلاق عظیم پیامبر (و انک لعلی خلق عظیم)."),
        (69, "الحاقة", "حاقه", "Al-Haqqah", 52, "MAKKI", 29, 78, 566, 568, "روز حقیقت بی‌پرده، دریافت نامه عمل به دست راست، و پاکی قرآن از سحر و کهانت."),
        (70, "المعارج", "معارج", "Al-Ma'arij", 44, "MAKKI", 29, 79, 568, 570, "عروج فرشتگان، بی‌تابی انسان در ناملایمات جز نمازگزاران پایدار و حق‌شناسان نیازمندان."),
        (71, "نوح", "نوح", "Nuh", 28, "MAKKI", 29, 71, 570, 571, "۹۵۰ سال دعوت شبانه‌روزی نوح، استغفار و بارش برکات آسمان و زمین."),
        (72, "الجن", "جن", "Al-Jinn", 28, "MAKKI", 29, 40, 572, 573, "شنیدن قرآن شگفت توسط جنیان و هدایت آنان به سوی توحید."),
        (73, "المزمل", "مزمل", "Al-Muzzammil", 20, "MAKKI", 29, 3, 574, 575, "دعوت پیامبر به قیام و شب‌زنده‌داری، تلاوت ترتیل قرآن و آمادگی برای پذیرش کلامی سنگین."),
        (74, "المدثر", "مدثر", "Al-Muddaththir", 56, "MAKKI", 29, 4, 575, 577, "فرمان قیام و انذار همگانی، پاکیزگی جامه و دوری از پلیدی، و عذاب سقر."),
        (75, "القيامة", "قیامت", "Al-Qiyamah", 40, "MAKKI", 29, 31, 577, 578, "سوگند به نفس لوامه ملامت‌گر، جزئیات زنده شدن سرانگشتان در رستاخیز."),
        (76, "الإنسان", "انسان (دهر)", "Al-Insan", 31, "MADANI", 29, 98, 578, 580, "آفرینش انسان، نذر و اطعام مخلصانه اهل‌بیت (ع) به مسکین و یتیم و اسیر."),
        (77, "المرسلات", "مرسلات", "Al-Mursalat", 50, "MAKKI", 29, 33, 580, 581, "سوگند به بادهای مأمور، نشیب و فرازهای روز داوری و هشدار به تکذیب‌کنندگان."),
        (78, "النبأ", "نبأ", "An-Naba", 40, "MAKKI", 30, 80, 582, 583, "خبر بزرگ رستاخیز، خواب مایه‌ی آرامش، و حسرت کافران که ای کاش خاک بودیم."),
        (79, "النازعات", "نازعات", "An-Nazi'at", 46, "MAKKI", 30, 81, 583, 584, "فرشتگان ستاننده جان، سرکشی فرعون و جایگاه آرام پرهیزگاران در بهشت."),
        (80, "عبس", "عبس", "Abasa", 42, "MAKKI", 30, 24, 585, 586, "تذکر درباره برخورد با نابینا، نعمت‌های ارزاق و روز فرار انسان از برادر، مادر و پدر."),
        (81, "التكوير", "تکویر", "At-Takwir", 29, "MAKKI", 30, 7, 586, 587, "تاریک شدن خورشید و فروریختن ستارگان، پرسش از خون دختران زنده‌به‌گور."),
        (82, "الانفطار", "انفطار", "Al-Infitar", 19, "MAKKI", 30, 82, 587, 587, "شکافتن آسمان، بازخواست از فریب‌خوردن انسان در برابر پروردگار کریم."),
        (83, "المطففين", "مطففین", "Al-Mutaffifin", 36, "MAKKI", 30, 86, 587, 589, "وای بر کم‌فروشان و ترازوداران خائن، پرونده سجین و نوشیدنی بهشتی تسنیم."),
        (84, "الانشقاق", "انشقاق", "Al-Inshiqaq", 25, "MAKKI", 30, 83, 589, 590, "تلاش خستگی‌ناپذیر انسان تا دیدار پروردگار و شادمانی دریافت‌کنندگان کارنامه از راست."),
        (85, "البروج", "بروج", "Al-Buruj", 22, "MAKKI", 30, 27, 590, 590, "ماجرای اصحاب اخدود و سوختن مؤمنان پایدار در آتش، و لوح محفوظ الهی."),
        (86, "الطارق", "طارق", "At-Tariq", 17, "MAKKI", 30, 36, 591, 591, "سوگند به ستاره شکافنده شب، آشکار شدن رازهای پنهان و آب جهنده آفرینش انسان."),
        (87, "الأعلى", "اعلی", "Al-A'la", 19, "MAKKI", 30, 8, 591, 592, "تسبیح پروردگار بلندمرتبه، رستگاری در گرو تزکیه و یاد خدا، و پیوند با صحف ابراهیم و موسی."),
        (88, "الغاشية", "غاشیه", "Al-Ghashiyah", 26, "MAKKI", 30, 68, 592, 593, "چهره‌های سرافکنده و چهره‌های شادمان قیامت، تفکر در خلقت شتر و استواری کوه‌ها."),
        (89, "الفجر", "فجر", "Al-Fajr", 30, "MAKKI", 30, 10, 593, 594, "سوگند به سپیده‌دم و شب‌های ده‌گانه، سرنوشت ارم و عاد، و خطاب آرامش‌بخش به نفس مطمئنه."),
        (90, "البلد", "بلد", "Al-Balad", 20, "MAKKI", 30, 35, 594, 595, "سوگند به شهر امن مکه، آفرینش انسان در سختی و گردنه بلند آزاد کردن بردگان و اطعام یتیمان."),
        (91, "الشمس", "شمس", "Ash-Shams", 15, "MAKKI", 30, 26, 595, 595, "یازده سوگند متوالی بر رستگاری تزکیه‌کنندگان نفس و تباهی آلوده‌سازان آن."),
        (92, "الليل", "لیل", "Al-Layl", 21, "MAKKI", 30, 9, 595, 596, "تقابل راه انفاق و تقوا با راه بخل و تکبر در سرنوشت آدمی."),
        (93, "الضحى", "ضحی", "Ad-Duha", 11, "MAKKI", 30, 11, 596, 596, "سوگند به روشنایی روز، دلداری به پیامبر در پایان انتظار وحی، و نهی از رنجاندن یتیم و سائل."),
        (94, "الشرح", "شرح (انشراح)", "Ash-Sharh", 8, "MAKKI", 30, 12, 596, 596, "شرح صدر پیامبر، سبک شدن بارهای سنگین، و وعده حتمی آسانی پس از هر دشواری."),
        (95, "التين", "تین", "At-Tin", 8, "MAKKI", 30, 28, 597, 597, "سوگند به انجیر و زیتون، آفرینش انسان در نیکوترین قامت و سقوط بی‌ایمانان به پست‌ترین درکات."),
        (96, "العلق", "علق", "Al-'Alaq", 19, "MAKKI", 30, 1, 597, 597, "نخستین آیات وحی با فرمان (اقرأ باسم ربک)، کرامت قلم، و سرکشی انسان در پی ثروت‌اندوزی."),
        (97, "القدر", "قدر", "Al-Qadr", 5, "MAKKI", 30, 25, 598, 598, "نزول قرآن در شب قدر، برتری آن از هزار ماه، و فرود فرشتگان تا طلوع فجر."),
        (98, "البينة", "بینه", "Al-Bayyinah", 8, "MADANI", 30, 100, 598, 599, "حجت آشکار الهی، حقیقت دین در اخلاص نماز و زکات، و معرفی صالحان به عنوان بهترین آفریدگان."),
        (99, "الزلزلة", "زلزله", "Az-Zalzalah", 8, "MADANI", 30, 93, 599, 599, "زمین‌لرزه مهیب قیامت، سخن گفتن زمین و حسابرسی اعمال حتی به سنگینی ذره‌ای خرد."),
        (100, "العاديات", "عادیات", "Al-'Adiyat", 11, "MAKKI", 30, 14, 599, 600, "سوگند به اسبان نفس‌زنان مجاهدان، ناسپاسی انسان و آشکار شدن سرایر دل‌ها."),
        (101, "القارعة", "قارعه", "Al-Qari'ah", 11, "MAKKI", 30, 30, 600, 600, "کوبنده هولناک، پریشانی مردم چون پروانه‌ها و سنجش میزان سنگینی اعمال نیک."),
        (102, "التكاثر", "تکاثر", "At-Takathur", 8, "MAKKI", 30, 16, 600, 600, "نکوهش تفاخر و مسابقه در فزونی مال تا لب گور، و بازخواست حتمی از نعمت‌ها."),
        (103, "العصر", "عصر", "Al-'Asr", 3, "MAKKI", 30, 13, 601, 601, "سوگند به زمانه، خسارت بنیادین همه انسان‌ها جز ایمان‌آورندگان، اهل عمل صالح و توصیه‌کنندگان به حق و صبر."),
        (104, "الهمزة", "همزه", "Al-Humazah", 9, "MAKKI", 30, 32, 601, 601, "وای بر عیب‌جویان و طعنه‌زنندگان ثروت‌اندوز، و کیفر در آتش شعله‌ور حطمه."),
        (105, "الفيل", "فیل", "Al-Fil", 5, "MAKKI", 30, 19, 601, 601, "ماجرای تاریخی هجوم ابرهه برای تخریب کعبه و نابودی سپاهیان فیل با پرندگان ابابیل."),
        (106, "قريش", "قریش", "Quraysh", 4, "MAKKI", 30, 29, 602, 602, "الفت و امنیت کاروان‌های قریش و سپاسگزاری از پروردگار کعبه که طعام‌دهنده و ایمن‌بخش است."),
        (107, "الماعون", "ماعون", "Al-Ma'un", 7, "MAKKI", 30, 17, 602, 602, "نشانه‌های تکذیب دین در راندن یتیمان، ریای در نماز و دریغ داشتن از کوچک‌ترین نیاز نیازمندان."),
        (108, "الكوثر", "کوثر", "Al-Kawthar", 3, "MAKKI", 30, 15, 602, 602, "عطای خیر کثیر و نسل مبارک فاطمه زهرا (س) به پیامبر، قربانی شکرانه و عقیم ماندن دشمنان."),
        (109, "الكافرون", "کافرون", "Al-Kafirun", 6, "MAKKI", 30, 18, 603, 603, "مرزبندی قاطع توحید با شرک و بت‌پرستی و رد هرگونه سازش عقیدتی (لکم دینکم ولی دین)."),
        (110, "النصر", "نصر", "An-Nasr", 3, "MADANI", 30, 114, 603, 603, "نوید فتح مکه و ورود گروه‌گروه مردم به دین خدا، و فرمان تسبیح و استغفار."),
        (111, "المسد", "مسد (لهب)", "Al-Masad", 5, "MAKKI", 30, 6, 603, 603, "هلاکت ابولهب و همسرش هیزم‌کش آتش به سبب دشمنی کینه‌توزانه با پیامبر."),
        (112, "الإخلاص", "اخلاص (توحید)", "Al-Ikhlas", 4, "MAKKI", 30, 22, 604, 604, "شناسنامه ناب خداوند: یکتایی مطلق (احد)، بی‌نیازی (صمد)، منزه از زایش و بی‌مانندی همیشگی."),
        (113, "الفلق", "فلق", "Al-Falaq", 5, "MAKKI", 30, 20, 604, 604, "پناه بردن به پروردگار سپیده‌دم از شر آفریدگان، تاریکی شب و حسادت حسودان."),
        (114, "الناس", "ناس", "An-Nas", 6, "MAKKI", 30, 21, 604, 604, "پناه بردن به مالک و خدای مردمان از وسوسه‌های پنهان شیطان صفتان جنی و انسی.")
    ]

    for item in surahs_manifest:
        chk_s = await db.scalar(select(Surah).where(Surah.id == item[0]))
        if not chk_s:
            s = Surah(
                id=item[0],
                name_arabic=item[1],
                name_persian=item[2],
                name_transliterated=item[3],
                ayah_count=item[4],
                revelation_type=item[5],
                juz_number=item[6],
                revelation_order=item[7],
                start_page=item[8],
                end_page=item[9],
                summary=item[10]
            )
            db.add(s)
    await db.flush()

    # 12. Complete Ayahs of Surah 1 (Al-Fatihah)
    fatihah_ayahs = [
        (1, 1, "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "به نام خداوند بخشنده مهربان", "بسم الله الرحمن الرحيم", 1, 1, 1, False),
        (1, 2, "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "ستایش مخصوص خداوندی است که پروردگار جهانیان است", "الحمد لله رب العالمين", 1, 1, 1, False),
        (1, 3, "الرَّحْمَٰنِ الرَّحِيمِ", "بخشنده و مهربان است", "الرحمن الرحيم", 1, 1, 1, False),
        (1, 4, "مَالِكِ يَوْمِ الدِّينِ", "مالک و فرمانروای روز جزاست", "مالك يوم الدين", 1, 1, 1, False),
        (1, 5, "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم", "إياك نعبد وإياك نستعين", 1, 1, 1, False),
        (1, 6, "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ", "ما را به راه راست هدایت فرما", "اهدنا الصراط المستقيم", 1, 1, 1, False),
        (1, 7, "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ", "راه کسانی که به آنان نعمت دادی، نه راه خشم‌گرفتگان و نه گمراهان", "صراط الذين أنعمت عليهم غير المغضوب عليهم ولا الضالين", 1, 1, 1, False),
    ]

    for item in fatihah_ayahs:
        chk_a = await db.scalar(select(Ayah).where(Ayah.surah_id == item[0], Ayah.ayah_number == item[1]))
        if not chk_a:
            a = Ayah(
                surah_id=item[0],
                ayah_number=item[1],
                text_arabic=item[2],
                text_persian=item[3],
                text_clean=item[4],
                juz=item[5],
                hizb=item[6],
                page=item[7],
                sajdah=item[8]
            )
            db.add(a)

    # 13. Ayah 10 of Surah 49 (Al-Hujurat) with Tadabbur Tools Bundle
    chk_hujurat = await db.scalar(select(Ayah).where(Ayah.surah_id == 49, Ayah.ayah_number == 10))
    if not chk_hujurat:
        hujurat_10 = Ayah(
            surah_id=49,
            ayah_number=10,
            text_arabic="إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ ۚ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ",
            text_persian="همانا مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح و آشتی برقرار سازید و تقوای الهی پیشه کنید، باشد که مورد رحمت قرار گیرید.",
            text_clean="إنما المؤمنون إخوة فأصلحوا بين أخويكم واتقوا الله لعلكم ترحمون",
            juz=26,
            hizb=51,
            page=516,
            sajdah=False
        )
        db.add(hujurat_10)

    # Tadabbur Data for Surah 49 Ayah 10 (matching the exact spec!)
    chk_tad = await db.scalar(select(AyahTadabburData).where(AyahTadabburData.surah_id == 49, AyahTadabburData.ayah_number == 10))
    if not chk_tad:
        tadabbur_hujurat = AyahTadabburData(
            surah_id=49,
            ayah_number=10,
            brief_tafsir="یکی از اساسی‌ترین پایه‌های نظام اجتماعی اسلام و منشور طلایی «اتحاد»؛ پیوند ایمانی چنان نیرومند و عمیق است که مانند پیوند برادری نسبی، حقوق، مودت و وظایف متقابل را ایجاب می‌کند.",
            keywords=[
                {"word": "إنما", "meaning": "اداه حصر قطعی (تنها و مسلماً)"},
                {"word": "المؤمنون", "meaning": "اهل ایمان و باور قلبی"},
                {"word": "إخوة", "meaning": "برادری راستین و حقیقی"},
                {"word": "فأصلحوا", "meaning": "مسئولیت اصلاح‌گری و آشتی‌دادن جمعی"}
            ],
            ai_tadabbur=[
                "برادری ایمانی فراتر از مرزهای جغرافیایی، زبانی، نژادی و قبیله‌ای است.",
                "بی‌تفاوتی در برابر اختلاف میان برادران ایمانی مذموم است؛ هر مؤمنی مصلح و پیام‌آور صلح است.",
                "رحمت پروردگار در جامعه‌ای جریان می‌یابد که سایه برادری و صلح بر آن حاکم باشد."
            ],
            reflection_question="امروز چه اقدام عملی می‌توانیم برای پایان دادن به کدورت‌ها و تقویت برادری میان اطرافیانمان برداریم؟",
            related_ayahs=[
                {"surahId": 3, "ayahNumber": 103, "relation": "چنگ زدن به حبل‌الله و نفی تفرقه"},
                {"surahId": 8, "ayahNumber": 46, "relation": "هشدار نسبت به نزاع و از بین رفتن شوکت امت"}
            ],
            translations={
                "ansarian": "مسلماً همه مؤمنان با یکدیگر برادرند؛ پس میان برادرانتان صلح و صفا برقرار کنید و از خدا پروا نمایید تا مورد رحمت قرار گیرید.",
                "makarem": "مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح و آشتی برقرار سازید و تقوای الهی پیشه کنید، باشد که مورد رحمت قرار گیرید.",
                "fooladvand": "در حقيقت مؤمنان با هم برادرند، پس ميان برادرانتان سازش دهيد و از خدا پروا بداريد، اميد كه مورد رحمت قرار گيريد."
            }
        )
        db.add(tadabbur_hujurat)
    await db.flush()

    # 14. Audio Timing Segments for Surah 1 (Parhizgar)
    # Ensure reciter 'parhizgar' exists in DB before adding segment
    reciter_check = await db.scalar(select(Reciter).where(Reciter.id == "parhizgar"))
    if not reciter_check:
        db.add(Reciter(id="parhizgar", name_fa="استاد شهریار پرهیزگار", name_ar="شهريار پرهيزگار", style="ترتیل آموزشی و دقیق", bitrate="128kbps", is_default=True))
        await db.flush()

    existing_seg = await db.scalar(select(AudioSegment).where(AudioSegment.surah_id == 1, AudioSegment.reciter_id == "parhizgar"))
    if not existing_seg:
        parhizgar_audio = AudioSegment(
            surah_id=1,
            reciter_id="parhizgar",
            audio_url="https://cdn.ettehad.app/quran/audio/parhizgar/001.mp3",
            duration_ms=42000,
            segments=[
                {"ayahNumber": 1, "startMs": 0, "endMs": 5200},
                {"ayahNumber": 2, "startMs": 5200, "endMs": 10500},
                {"ayahNumber": 3, "startMs": 10500, "endMs": 15800},
                {"ayahNumber": 4, "startMs": 15800, "endMs": 21000},
                {"ayahNumber": 5, "startMs": 21000, "endMs": 28400},
                {"ayahNumber": 6, "startMs": 28400, "endMs": 34600},
                {"ayahNumber": 7, "startMs": 34600, "endMs": 42000}
            ]
        )
        db.add(parhizgar_audio)
    await db.flush()

    # 15. Prompt Suggestions (matching Section 5.4)
    prompt_suggestions = [
        PromptSuggestion(
            title="حقیقت اتحاد در قرآن",
            query="مفهوم حبل‌الله و راه‌های حفظ همبستگی در جامعه اسلامی چیست؟",
            icon_name="groups",
            order_index=1
        ),
        PromptSuggestion(
            title="آرامش در پرتو قرآن",
            query="کدام آیات قرآن بیشترین آرامش قلبی و امیدواری را به انسان می‌بخشند؟",
            icon_name="favorite",
            order_index=2
        ),
        PromptSuggestion(
            title="داستان حضرت یوسف (ع)",
            query="مهم‌ترین درس‌های مدیریتی و اخلاقی از احسن‌القصص سوره یوسف چیست؟",
            icon_name="menu_book",
            order_index=3
        ),
        PromptSuggestion(
            title="فضیلت نماز شب و سحرخیزی",
            query="تأثیر معنوی تهجد و عبادت در سحرگاهان طبق آیات قرآن چیست؟",
            icon_name="bedtime",
            order_index=4
        )
    ]
    db.add_all(prompt_suggestions)

    await db.commit()

    # 16. Ensure feed posts & interactions are seeded
    await seed_feed_if_needed(db)
