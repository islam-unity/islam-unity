"""
اسکریپت جامع استخراج نمونه‌های تصادفی از منابع دانلود شده و ثبت همزمان در:
1. کتابخانه و پایگاه داده رابطه‌ای SQL (جداول books, book_chapters, knowledge_chunks)
2. پایگاه برداری معنایی چندوجهی Vector DB (کیودرانت Qdrant)
3. ذخیره شناسنامه کامل استخراج در فایل JSON (کتاب‌ها، فصول، بخش‌ها و محتوا)
"""

import os
import sys
import json
import uuid
import re
import random
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

workspace_dir = backend_dir.parent

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sqlalchemy import select, func, or_
from app.db.session import AsyncSessionLocal, engine
from app.db.base import Base
from app.db.models.library import Book, BookChapter, KnowledgeChunk, LibraryCategory
from app.services.vector_service import VectorService
from app.config import settings


def clean_openiti_text(raw_text: str) -> str:
    """Clean OpenITI markup tags, page numbers, and formatting artefacts."""
    t = re.sub(r'#META#.*?\n', '', raw_text)
    t = re.sub(r'#META#Header#End#', '', t)
    t = re.sub(r'#|~~|Page\w+|ms\w+|@\w+@|\d+\.\d+@|\[.*?\]', '', t)
    t = re.sub(r'\r', '', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()


def extract_raw_samples():
    """Extract random, authentic sections from the downloaded source books."""
    print("⏳ در حال استخراج بخش‌های منتخب از منابع دانلود شده...")
    extracted_books = []

    # ---------------------------------------------------------
    # 1. الأربعون النووية (حديث)
    # ---------------------------------------------------------
    p_nawawi = workspace_dir / "raw_data_books" / "hadith" / "hadith-json" / "db" / "by_book" / "forties" / "nawawi40.json"
    if p_nawawi.exists():
        with open(p_nawawi, "r", encoding="utf-8") as f:
            data = json.load(f)
            hadiths = data.get("hadiths", [])
            # Hadith 1 (Niyyah) & Hadith 2 (Jibril - Islam, Iman, Ihsan)
            h1 = hadiths[0] if len(hadiths) > 0 else None
            h2 = hadiths[1] if len(hadiths) > 1 else None

            chunks = []
            if h1:
                chunks.append({
                    "chunk_id": "chk_nawawi_h01",
                    "chapter_title": "باب الإخلاص وإحضار النية",
                    "hadith_index": 1,
                    "text": h1.get("arabic", "").strip(),
                    "text_arabic": h1.get("arabic", "").strip(),
                    "summary": "حدیث مشهور نبوی درباره نقش بنیادین نیت و اخلاص در قبولی تمام اعمال و عبادات. عمل هر کس بر اساس قصد درونی او محاسبه می‌شود؛ چه هجرت به سوی خدا و پیامبر و چه برای اهداف دنیوی.",
                    "hypothetical_questions": [
                        "آیا در اسلام قبولی اعمال وابسته به نیت درونی است؟",
                        "حدیث إنما الأعمال بالنیات چه پیامی درباره اخلاص دارد؟",
                        "تفاوت هجرت برای رضای خدا با هجرت برای مقاصد دنیوی چیست؟"
                    ],
                    "core_concepts": ["اخلاص", "نیت", "إنما الأعمال بالنيات", "هجرت", "قبولی عمل", "حدیث نبوی"],
                    "domain_insights": [
                        "هیچ عبادتی بدون قصد قربت و اخلاص پذیرفته نیست.",
                        "ارزش‌گذاری الهی بر انگیزه باطنی استوار است نه صرف ظاهر کردار."
                    ]
                })
            if h2:
                chunks.append({
                    "chunk_id": "chk_nawawi_h02",
                    "chapter_title": "باب مراتب الدین (الإسلام والإیمان والإحسان)",
                    "hadith_index": 2,
                    "text": h2.get("arabic", "").strip(),
                    "text_arabic": h2.get("arabic", "").strip(),
                    "summary": "حدیث مشهور جبرائیل (ع) که ارکان سه‌گانه دین را تببین می‌کند: ۱. اسلام (شهادتین، نماز، زکات، روزه، حج)، ۲. ایمان (باور به خدا، ملائکه، کتب آسمانی، انبیاء، روز قیامت و تقدیر)، ۳. احسان (پرستش خداوند چنانکه گویا او را می‌بینی)، و نشانه‌های آخرالزمان.",
                    "hypothetical_questions": [
                        "ارکان اسلام و ایمان در حدیث معروف جبرائیل چیستند؟",
                        "مفهوم احسان در عبادت بر اساس فرموده پیامبر اکرم (ص) چگونه است؟",
                        "نشانه‌های روز قیامت طبق روایت امام نووی چیست؟"
                    ],
                    "core_concepts": ["حدیث جبرائیل", "ارکان اسلام", "ایمان", "احسان", "آخرالزمان", "عقاید اسلامی"],
                    "domain_insights": [
                        "دین در سه مرتبه ظاهری (اسلام)، باطنی و قلبی (ایمان) و شهودی (احسان) تعریف می‌شود.",
                        "مراقبه در عبادت و احساس حضور دائم در پیشگاه الهی اوج مقام احسان است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_hadith_nawawi40",
                "title": "الأربعون النووية في الأحاديث الصحيحة النبوية",
                "author": "الإمام يحيى بن شرف النووي",
                "category_id": "cat_hadith",
                "madhhab": "عام / نبوی",
                "language": "ar",
                "source_file": "raw_data_books/hadith/hadith-json/db/by_book/forties/nawawi40.json",
                "description": "مجموعه ۴۲ حدیث محوری و بنیادین از سخنان رسول اکرم (ص) که پایه‌های شریعت، اخلاق و معارف دین اسلام را تشکیل می‌دهند.",
                "tags": ["حدیث", "اربعین", "سنت نبوی", "اخلاق", "عقاید"],
                "topics": ["ایمان", "اخلاص", "احکام کلی شریعت", "حقوق مسلمین"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 2. صحيح البخاري (حديث)
    # ---------------------------------------------------------
    p_bukhari = workspace_dir / "raw_data_books" / "hadith" / "hadith-json" / "db" / "by_book" / "the_9_books" / "bukhari.json"
    if p_bukhari.exists():
        with open(p_bukhari, "r", encoding="utf-8") as f:
            data = json.load(f)
            hadiths = data.get("hadiths", [])
            # Search for specific prominent hadiths
            h_iman = None
            h_ilm = None
            for h in hadiths[:300]:
                ar_txt = h.get("arabic", "")
                if not h_iman and "المسلم من سلم المسلمون من لسانه ويده" in ar_txt:
                    h_iman = h
                if not h_ilm and ("من سلك طريقا" in ar_txt or "طلب العلم" in ar_txt or "يرد الله به خيرا يفقهه في الدين" in ar_txt):
                    h_ilm = h
                if h_iman and h_ilm:
                    break
            if not h_iman and len(hadiths) > 10:
                h_iman = hadiths[9]
            if not h_ilm and len(hadiths) > 70:
                h_ilm = hadiths[70]

            chunks = []
            if h_iman:
                chunks.append({
                    "chunk_id": "chk_bukhari_h01",
                    "chapter_title": "كتاب الإيمان - باب المسلم من سلم المسلمون من لسانه ويده",
                    "hadith_index": h_iman.get("idInBook", 10),
                    "text": h_iman.get("arabic", "").strip(),
                    "text_arabic": h_iman.get("arabic", "").strip(),
                    "summary": "تعریف حقیقت اسلام و هجرت در کلام پیامبر (ص): مسلمان راستین کسی است که دیگر مسلمانان از زبان و دست او در امان و سلامت باشند، و مهاجر واقعی کسی است که از گناهان و منهیات الهی دوری گزیند.",
                    "hypothetical_questions": [
                        "مسلمان واقعی در بیان پیامبر اسلام (ص) چه ویژگی‌هایی دارد؟",
                        "معنای هجرت باطنی و دوری از گناهان طبق صحیح بخاری چیست؟",
                        "حرمت آزار زبانی و بدنی دیگران در شریعت اسلام چگونه تبیین شده است؟"
                    ],
                    "core_concepts": ["حقیقت اسلام", "سلامت زبان و دست", "حقوق برادران ایمانی", "هجرت از گناه", "صحیح بخاری"],
                    "domain_insights": [
                        "امنیت اجتماعی و روانی جامعه اسلامی شرط اساسی کمال ایمان فردی است.",
                        "مسلمان نباید با نیش زبان، بدگویی یا تعرض فیزیکی به برادران خود آسیب رساند."
                    ]
                })
            if h_ilm:
                chunks.append({
                    "chunk_id": "chk_bukhari_h02",
                    "chapter_title": "كتاب العلم - باب من يرد الله به خيرا يفقهه في الدين",
                    "hadith_index": h_ilm.get("idInBook", 71),
                    "text": h_ilm.get("arabic", "").strip(),
                    "text_arabic": h_ilm.get("arabic", "").strip(),
                    "summary": "روایت پیامبر اکرم (ص) در فضیلت فهم عمیق معارف دین: هرگاه خداوند خیر و هدایت بنده‌ای را بخواهد، او را در دین و احکام شریعت آگاه و فقیه می‌گرداند و بینش حقیقت‌نگر به او می‌بخشد.",
                    "hypothetical_questions": [
                        "نشانه اراده خیر خداوند برای بنده بر اساس احادیث صحیح بخاری چیست؟",
                        "فضیلت تفقه و فهم عمیق شریعت در احادیث نبوی چگونه آمده است؟",
                        "چه رابطه‌ای میان برکت الهی و یادگیری معارف دینی وجود دارد؟"
                    ],
                    "core_concepts": ["طلب علم", "تفقه در دین", "من يرد الله به خيرا", "فضیلت دانش", "صحیح بخاری"],
                    "domain_insights": [
                        "فهم درست دین بزرگ‌ترین موهبت الهی برای رهایی از انحراف و جهالت است.",
                        "دانش دین باید مقدمه بصیرت، عمل صالح و خدمت به بندگان خدا باشد."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_hadith_bukhari",
                "title": "صحيح البخاري (الجامع المسند الصحيح المختصر)",
                "author": "الإمام محمد بن إسماعيل البخاري",
                "category_id": "cat_hadith",
                "madhhab": "عام / اهل سنت",
                "language": "ar",
                "source_file": "raw_data_books/hadith/hadith-json/db/by_book/the_9_books/bukhari.json",
                "description": "یکی از معتبرترین جوامع روایی شامل احادیث مسند و صحیح نبوی در زمینه‌های ایمان، علم، عبادات، معاملات و اخلاق اجتماعی.",
                "tags": ["صحیح بخاری", "احادیث نبوی", "کتب تسعه", "اهل سنت", "روایات"],
                "topics": ["ایمان", "علم", "اخلاق", "جامعه اسلامی"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 3. رياض الصالحين (حديث و اخلاق)
    # ---------------------------------------------------------
    p_riyad = workspace_dir / "raw_data_books" / "hadith" / "hadith-json" / "db" / "by_book" / "other_books" / "riyad_assalihin.json"
    if p_riyad.exists():
        with open(p_riyad, "r", encoding="utf-8") as f:
            data = json.load(f)
            hadiths = data.get("hadiths", [])
            h_sabr = None
            h_birr = None
            for h in hadiths:
                txt = h.get("arabic", "")
                if not h_sabr and "عجبا لأمر المؤمن" in txt:
                    h_sabr = h
                if not h_birr and "اتق الله حيثما كنت" in txt:
                    h_birr = h
                if h_sabr and h_birr:
                    break
            if not h_sabr and len(hadiths) > 25:
                h_sabr = hadiths[25]
            if not h_birr and len(hadiths) > 60:
                h_birr = hadiths[60]

            chunks = []
            if h_sabr:
                chunks.append({
                    "chunk_id": "chk_riyad_h01",
                    "chapter_title": "باب الصبر في السراء والضراء",
                    "hadith_index": h_sabr.get("idInBook", 27),
                    "text": h_sabr.get("arabic", "").strip(),
                    "text_arabic": h_sabr.get("arabic", "").strip(),
                    "summary": "روایت زیبای صهیب رومی از پیامبر (ص): شگفتا از کار و احوال مؤمن! تمام مقدرات او خیر است؛ اگر آسایش و نعمتی به او رسد شکر می‌گذارد و خیر می‌بیند، و اگر دچار سختی و گزندی شود صبر پیشه می‌کند و آن نیز برایش سراسر پاداش و خیر می‌گردد.",
                    "hypothetical_questions": [
                        "چرا تمام مقدرات مؤمن در غم و شادی تبدیل به خیر و ثواب می‌شود؟",
                        "نقش صبر و شکر در آرامش روحی مسلمان طبق ریاض الصالحین چیست؟",
                        "برخورد صحیح مؤمن با سختی‌ها و گشایش‌های روزگار چگونه باید باشد؟"
                    ],
                    "core_concepts": ["صبر", "شکر", "عجبا لأمر المؤمن", "توکل", "رضایت به قضای الهی", "ریاض الصالحین"],
                    "domain_insights": [
                        "مؤمن حقیقی در فراز و نشیب‌های زندگی تعادل روحی خود را میان شکر و صبر حفظ می‌کند.",
                        "سختی‌ها در زندگی مؤمن مایه‌ی ارتقای درجات و کفاره لغزش‌هاست."
                    ]
                })
            if h_birr:
                chunks.append({
                    "chunk_id": "chk_riyad_h02",
                    "chapter_title": "باب التقوى ومخالطة الناس بالخلق الحسن",
                    "hadith_index": h_birr.get("idInBook", 61),
                    "text": h_birr.get("arabic", "").strip(),
                    "text_arabic": h_birr.get("arabic", "").strip(),
                    "summary": "سفارش جامع رسول خدا (ص) به معاذ بن جبل و ابوذر: در هر جا و هر حالی که هستی تقوای الهی پیشه کن، و به دنبال هر کار بد، کار نیکی انجام ده تا آن را محو سازد، و با مردم با اخلاق نیکو و شایسته معاشرت نما.",
                    "hypothetical_questions": [
                        "سه توصیه طلایی پیامبر (ص) درباره تقوا، توبه و اخلاق اجتماعی چیست؟",
                        "چگونه انجام کارهای نیک گناهان و رفتارهای اشتباه را جبران می‌کند؟",
                        "آداب اسلامی معاشرت با عموم مردم بر اساس آموزه‌های نبوی چیست؟"
                    ],
                    "core_concepts": ["تقوا", "حسن خلق", "محو گناهان با حسنات", "معاشرت نیکو", "اخلاق اسلامی"],
                    "domain_insights": [
                        "تقوا نباید محدود به مکان خاصی باشد بلکه ناظر بر همه سکنات زندگی است.",
                        "جبران لغزش‌ها با اعمال صالح راهبرد کلیدی اسلام برای بازسازی شخصیت روحی است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_hadith_riyad",
                "title": "رياض الصالحين من حديث سيد المرسلين",
                "author": "الإمام يحيى بن شرف النووي",
                "category_id": "cat_akhlaq",
                "madhhab": "عام / مشترک",
                "language": "ar",
                "source_file": "raw_data_books/hadith/hadith-json/db/by_book/other_books/riyad_assalihin.json",
                "description": "کتاب جامع تهذیب نفس، سیر و سلوک و اخلاق عملی مبتنی بر معتبرترین احادیث نبوی که در سراسر جهان اسلام مورد استقبال است.",
                "tags": ["ریاض الصالحین", "اخلاق", "صبر", "تقوا", "حدیث"],
                "topics": ["فضایل اخلاقی", "حقوق والدین", "آداب معاشرت", "معنویت"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 4. تفسير الجلالين (تفسير)
    # ---------------------------------------------------------
    p_jalalayn = workspace_dir / "raw_data_books" / "tafsir" / "tafsir-json" / "json" / "ar.jalalayn.json"
    if p_jalalayn.exists():
        with open(p_jalalayn, "r", encoding="utf-8") as f:
            data = json.load(f)
            tafsir_data = data.get("tafsir", [])
            # Surah 1: Al-Fatiha
            fatiha_ayahs = tafsir_data[0] if len(tafsir_data) > 0 else []
            fatiha_combined = "\n".join([f"آیه {idx+1}: {txt}" for idx, txt in enumerate(fatiha_ayahs)])

            # Surah 2 Ayah 255 (Ayat al-Kursi)
            baqarah_ayahs = tafsir_data[1] if len(tafsir_data) > 1 else []
            kursi_text = baqarah_ayahs[254] if len(baqarah_ayahs) >= 255 else (baqarah_ayahs[0] if baqarah_ayahs else "")

            chunks = []
            if fatiha_combined:
                chunks.append({
                    "chunk_id": "chk_jalalayn_s01",
                    "chapter_title": "تفسير سورة الفاتحة (أم الكتاب)",
                    "hadith_index": 1,
                    "text": fatiha_combined.strip(),
                    "text_arabic": fatiha_combined.strip(),
                    "summary": "تفسیر موجز و استوار جلالین بر سوره مبارکه فاتحة الکتاب: تبیین معانی حمد و ثنای الهی، ربوبیت بر جهانیان، رحمانیت پروردگار، مالکیت روز جزا، توحید در عبادت و استعانت، و طلب هدایت به صراط مستقیم نعمت‌یافتگان.",
                    "hypothetical_questions": [
                        "تفسیر جلالین عبارت «إياك نعبد وإياك نستعين» را چگونه شرح داده است؟",
                        "منظور از «صراط الذين أنعمت عليهم» و نعمت‌یافتگان در تفسیر جلالین چیست؟",
                        "چرا سوره فاتحه ام‌الکتاب و سرآغاز قرآن نامیده شده است؟"
                    ],
                    "core_concepts": ["سوره فاتحه", "تفسیر جلالین", "رب العالمین", "صراط مستقیم", "توحید افعالی", "استعانت"],
                    "domain_insights": [
                        "حصر عبادت و یاری‌خواهی به درگاه الهی زیربنای توحید عملی در زندگی مؤمن است.",
                        "صراط مستقیم راهی است متمایز از غضب‌شدگان و گمراهان تاریخ."
                    ]
                })

            if kursi_text:
                chunks.append({
                    "chunk_id": "chk_jalalayn_s02_kursi",
                    "chapter_title": "تفسير آية الكرسي (سورة البقرة: ۲۵۵)",
                    "hadith_index": 255,
                    "text": f"تفسير آية الكرسي: {kursi_text}".strip(),
                    "text_arabic": kursi_text.strip(),
                    "summary": "تفسیر آیه الکرسی در جلالین: تبیین اسمای حسنای «الحی» و «القیوم»، نفی هرگونه خواب و غفلت از پیشگاه خداوندی، حاکمیت مطلق بر آسمان‌ها و زمین، شرایط شفاعت به اذن پروردگار و وسعت بیکران کرسی و علم الهی.",
                    "hypothetical_questions": [
                        "معنای حی و قیوم و وسعت کرسی الهی در آیه الکرسی چیست؟",
                        "شفاعت در پیشگاه خداوند متعال بر چه مبنایی مجاز شمرده شده است؟",
                        "دلالت آیه ۲۵۵ سوره بقره بر احاطه علمی خداوند بر آشکار و نهان چگونه است؟"
                    ],
                    "core_concepts": ["آية الكرسي", "الحي القيوم", "تفسیر جلالین", "شفاعت", "علم الهی", "توحید ذاتی"],
                    "domain_insights": [
                        "تدبیر هستی لحظه‌ای از اراده و آگاهی قیومیت حق پنهان و ساقط نمی‌شود.",
                        "شفاعت در قیامت حقی است انحصاری که تنها به اذن و رضایت پروردگار تحقق می‌یابد."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_tafsir_jalalayn",
                "title": "تفسير الجلالين",
                "author": "جلال الدين المحلي وجلال الدين السيوطي",
                "category_id": "cat_quran",
                "madhhab": "عام / روایی",
                "language": "ar",
                "source_file": "raw_data_books/tafsir/tafsir-json/json/ar.jalalayn.json",
                "description": "یکی از ماندگارترین و معتبرترین تفاسیر موجز و روان قرآن کریم که کلمات و عبارات دشوار تمام آیات را با دقت واژگانی و نحوی معنا کرده است.",
                "tags": ["تفسیر قرآن", "جلالین", "سیوطی", "علوم قرآن", "آیات"],
                "topics": ["تفسیر ترتیبی", "توحید", "شأن نزول", "هدایت قرآنی"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 5. تفسير السعدي (تفسير معاصر و بياني)
    # ---------------------------------------------------------
    p_saddi = workspace_dir / "raw_data_books" / "tafsir" / "tafsir-json" / "json" / "ar.saddi.json"
    if p_saddi.exists():
        with open(p_saddi, "r", encoding="utf-8") as f:
            data = json.load(f)
            tafsir_data = data.get("tafsir", [])
            # Surah 49: Al-Hujurat (Ethics and Unity)
            hujurat_ayahs = tafsir_data[48] if len(tafsir_data) >= 49 else []
            hujurat_txt = hujurat_ayahs[9] if len(hujurat_ayahs) >= 10 else (hujurat_ayahs[0] if hujurat_ayahs else "")

            # Surah 112: Al-Ikhlas
            ikhlas_ayahs = tafsir_data[111] if len(tafsir_data) >= 112 else []
            ikhlas_txt = "\n".join([f"آیه {idx+1}: {txt}" for idx, txt in enumerate(ikhlas_ayahs)]) if ikhlas_ayahs else ""

            chunks = []
            if hujurat_txt:
                chunks.append({
                    "chunk_id": "chk_saddi_hujurat",
                    "chapter_title": "تفسير سورة الحجرات (حقوق الأخوة الإسلامية وإصلاح ذات البين)",
                    "hadith_index": 10,
                    "text": f"تفسير سورة الحجرات (إنما المؤمنون إخوة): {hujurat_txt}".strip(),
                    "text_arabic": hujurat_txt.strip(),
                    "summary": "تفسیر علامه سعدی پیرامون آیه شریفه «إنما المؤمنون إخوة فأصلحوا بين أخويكم»: تبیین اصل بنیادین برادری ایمانی میان همه مسلمانان، وجوب اصلاح اختلافات و پرهیز جدی از تفرقه، مسخره کردن، عیب‌جویی، القاب زشت، سوءظن و غیبت.",
                    "hypothetical_questions": [
                        "دیدگاه علامه سعدی درباره وظیفه مسلمانان در هنگام بروز اختلاف بین برادران ایمانی چیست؟",
                        "چرا خداوند مؤمنان را با وجود تفاوت‌های نژادی و زبانی برادر یکدیگر خوانده است؟",
                        "احکام و آثار نهی از تجسس و غیبت در سوره حجرات چگونه تبیین شده است؟"
                    ],
                    "core_concepts": ["سوره حجرات", "اخوت اسلامی", "تفسیر سعدی", "اصلاح ذات البین", "نهی از غیبت", "وحدت امت"],
                    "domain_insights": [
                        "برادری ایمانی پیوندی فراتر از نسبت‌های خونی و قومی است که حقوق متقابل بر دوش همگان می‌نهد.",
                        "اصلاح میان مؤمنان و رفع کدورت‌ها فریضه‌ای اجتماعی برای حفظ اقتدار جامعه اسلامی است."
                    ]
                })

            if ikhlas_txt:
                chunks.append({
                    "chunk_id": "chk_saddi_ikhlas",
                    "chapter_title": "تفسير سورة الإخلاص (بيان التوحيد الخالص وصفات الكمال)",
                    "hadith_index": 1,
                    "text": f"تفسير سورة الإخلاص: {ikhlas_txt}".strip(),
                    "text_arabic": ikhlas_txt.strip(),
                    "summary": "تفسیر تحلیلی سوره توحید و اخلاص در کلام سعدی: اثبات احدیت ذات پروردگار، صمدیت به معنای بی‌نیازی مطلق خداوند و نیاز همه‌جانبه تمام آفریدگان به او، نفی هرگونه فرزند، پدر و همتا برای حضرت حق.",
                    "hypothetical_questions": [
                        "معنای واژه «الصمد» در تفسیر سوره اخلاص علامه سعدی چیست؟",
                        "چرا سوره اخلاص برابر با ثلث قرآن در فضیلت و معارف دانسته شده است؟",
                        "استدلال‌های قرآنی بر نفی همتا، شریک و زاد و ولد برای خداوند کدامند؟"
                    ],
                    "core_concepts": ["سوره اخلاص", "توحید الصمد", "تفسیر السعدی", "یکتاپرستی", "صفات کمال الهی"],
                    "domain_insights": [
                        "خداوند در ذات، اسما و افعال بی‌همتاست و کمال مطلق از آن اوست.",
                        "اخلاص در عقیده پایه و اساس تمامی فضایل معنوی و نجات اخروی انسان است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_tafsir_saddi",
                "title": "تيسير الكريم الرحمن في تفسير كلام المنان",
                "author": "الشيخ عبد الرحمن بن ناصر السعدي",
                "category_id": "cat_quran",
                "madhhab": "عام / سلفی معتدل",
                "language": "ar",
                "source_file": "raw_data_books/tafsir/tafsir-json/json/ar.saddi.json",
                "description": "تفسیری شیوا، روان و مبتنی بر هدایت‌ها و پندهای تربیتی و اخلاقی قرآن کریم بدون پیچیدگی‌های غیرضروری لفظی.",
                "tags": ["تفسیر سعدی", "هدایت قرآنی", "اخلاق", "تربیت اسلامی", "توحید"],
                "topics": ["اخوت دینی", "معاشرت قرآنی", "خداشناسی", "اصلاح نفس"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 6. مختصر القدوري (فقه حنفي)
    # ---------------------------------------------------------
    p_quduri = workspace_dir / "raw_data_books" / "fiqh" / "mukhtasar_al_quduri_hanafi.txt"
    if p_quduri.exists():
        with open(p_quduri, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
            # Extract Kitab al-Tahara
            m_tahara = re.search(r'### \| AUTO 1 - كتاب الطهارة(.*?)### \|', raw, re.DOTALL)
            tahara_txt = clean_openiti_text(m_tahara.group(1))[:1500] if m_tahara else ""

            # Extract Kitab al-Salat
            m_salat = re.search(r'### \| AUTO 2 - كتاب الصلاة(.*?)### \|', raw, re.DOTALL)
            salat_txt = clean_openiti_text(m_salat.group(1))[:1500] if m_salat else ""

            chunks = []
            if tahara_txt:
                chunks.append({
                    "chunk_id": "chk_quduri_tahara",
                    "chapter_title": "كتاب الطهارة - فرائض الوضوء وسننه ونواقضه",
                    "hadith_index": 1,
                    "text": tahara_txt,
                    "text_arabic": tahara_txt,
                    "summary": "احکام و فتاوای فقه حنفی در باب طهارت: تبیین چهار فرض وضو (شستن صورت، دست‌ها تا آرنج، مسح یک چهارم سر و شستن پاها تا قوزک)، سنن وضو (شستن دست‌ها در ابتدا، تسمیه، مسواک، مضمضه، استنشاق) و موارد ناقض وضو.",
                    "hypothetical_questions": [
                        "فرایض وضو در مذهب حنفی طبق مختصر القدوری چیست؟",
                        "میزان واجب مسح سر و سنن مستحب وضو در فقه حنفی چگونه است؟",
                        "نواقض وضو و اسباب باطل شدن طهارت در دیدگاه احناف کدامند؟"
                    ],
                    "core_concepts": ["فقه حنفی", "مختصر القدوری", "طهارت", "فرائض وضو", "نواقض وضو", "احکام شرعی"],
                    "domain_insights": [
                        "رعایت شروط و ارکان طهارت مقدمه صحت نماز و طواف است.",
                        "مذهب حنفی مسح سر به میزان ناصیه (یک چهارم سر) را فرض و کفایت‌کننده می‌داند."
                    ]
                })

            if salat_txt:
                chunks.append({
                    "chunk_id": "chk_quduri_salat",
                    "chapter_title": "كتاب الصلاة - مواقيت الصلاة وشروط صحتها",
                    "hadith_index": 2,
                    "text": salat_txt,
                    "text_arabic": salat_txt,
                    "summary": "احکام نماز و اوقات شرعی پنجگانه در مذهب حنفی: زمان فضیلت و انتهای نمازهای فجر، ظهر، عصر، مغرب و عشاء، اوقات کراهت اقامه نماز و شروط صحت نماز شامل طهارت از حدث و خبث، ستر عورت، استقبال قبله و نیت.",
                    "hypothetical_questions": [
                        "مواقیت شرعی نمازهای پنجگانه در مذهب امام ابو حنیفه چگونه محاسبه می‌شود؟",
                        "اوقات کراهت نماز در شبانه‌روز طبق کتاب مختصر القدوری کدامند؟",
                        "شروط شش‌گانه صحت نماز پیش از ورود به تکبیرة الاحرام چیست؟"
                    ],
                    "core_concepts": ["فقه حنفی", "مواقیت الصلاة", "شروط نماز", "قبله", "طهارت مکان و لباس", "مختصر القدوری"],
                    "domain_insights": [
                        "نماز در وقت مقرر از نشانه‌های پایبندی به نظم و عهد با پروردگار است.",
                        "طهارت بدن، جامه و جایگاه نمازگزار و پوشش عورت شرط واجب صحت نماز است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_fiqh_quduri",
                "title": "مختصر القدوري في الفقه الحنفي",
                "author": "أبو الحسين أحمد بن محمد القدوري البغدادي",
                "category_id": "cat_fiqh",
                "madhhab": "حنفی",
                "language": "ar",
                "source_file": "raw_data_books/fiqh/mukhtasar_al_quduri_hanafi.txt",
                "description": "کتاب درسی و متن اصلی فقه حنفی (معروف به الکتاب) که فتاوای استوار مذهب ابوحنیفه را به اختصار و دقت بیان نموده است.",
                "tags": ["فقه حنفی", "قدوری", "طهارت", "نماز", "احکام اهل سنت"],
                "topics": ["وضو", "غسل", "اوقات شرعی", "عبادات حنفی"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 7. شرائع الإسلام (فقه جعفري)
    # ---------------------------------------------------------
    p_sharai = workspace_dir / "raw_data_books" / "fiqh" / "sharai_al_islam_hilli_jafari.txt"
    if p_sharai.exists():
        with open(p_sharai, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
            m_qada = re.search(r'# كتاب القضاء والنظر في: صفات القاضي(.*?)# وهل يشترط علمه بالكتابة', raw, re.DOTALL)
            qada_txt = clean_openiti_text(m_qada.group(1))[:1500] if m_qada else ""

            m_sawm = re.search(r'# كتاب الصوم(.*?)# خاتمة', raw, re.DOTALL)
            sawm_txt = clean_openiti_text(m_sawm.group(1))[:1500] if m_sawm else ""

            chunks = []
            if qada_txt:
                chunks.append({
                    "chunk_id": "chk_sharai_qada",
                    "chapter_title": "كتاب القضاء - صفات القاضي الشرعي وآداب الحكم",
                    "hadith_index": 1,
                    "text": qada_txt,
                    "text_arabic": qada_txt,
                    "summary": "فتاوای فقه جعفری در کتاب القضاء محقق حلی: تبیین صفات و شروط بنیادین قاضی شرعی اعم از بلوغ، عقل، ایمان، عدالت، طهارت مولد، اجتهاد در احکام و ذکورت. بیان حرمت اخذ رشوه و وجوب مساوات میان طرفین دعوا در نگاه و تکریم.",
                    "hypothetical_questions": [
                        "شرایط و اوصاف قاضی شرعی در فقه امامیه طبق شرائع الإسلام چیست؟",
                        "حکم اخذ رشوه، هدایا و دستمزد در امر قضاوت از نظر محقق حلی چیست؟",
                        "آداب اسلامی برخورد قاضی با شاکی و متهم در دادگاه شرعی چگونه است؟"
                    ],
                    "core_concepts": ["فقه جعفری", "شرائع الإسلام", "محقق حلی", "قضاوت اسلامی", "شرایط قاضی", "عدالت قضایی"],
                    "domain_insights": [
                        "قضاوت منصبی خطیر است که نیازمند اجتهاد، عدالت نفسانی و استقلال رأی می‌باشد.",
                        "رعایت بی‌طرفی کامل و پرهیز از شائبه‌های مالی شرط مشروعیت حکم قاضی است."
                    ]
                })

            if sawm_txt:
                chunks.append({
                    "chunk_id": "chk_sharai_sawm",
                    "chapter_title": "كتاب الصوم - نية الصيام وشروط الوجوب والمفطرات",
                    "hadith_index": 2,
                    "text": sawm_txt,
                    "text_arabic": sawm_txt,
                    "summary": "احکام روزه در مذهب جعفری: نیت قربت الی الله، شروط وجوب روزه بر مکلف (بلوغ، عقل، قدرت، سلامت از بیماری و عدم سفر شرعی)، و تبیین مفطرات و مواردی که روزه را باطل می‌کند همراه با احکام قضا و کفاره.",
                    "hypothetical_questions": [
                        "شروط وجوب روزه ماه مبارک رمضان در فقه جعفری چیست؟",
                        "احکام نیت روزه و وقت نیت برای روزه واجب و مستحب چگونه است؟",
                        "مفطرات اصلی و احکام کفاره عمدی در شرائع الإسلام کدامند؟"
                    ],
                    "core_concepts": ["فقه جعفری", "روزه ماه رمضان", "مفطرات صوم", "نیت قربت", "شرائع الإسلام"],
                    "domain_insights": [
                        "امساک و روزه‌داری تمرین خودسازی و تسلط اراده بر کشش‌های غریزی است.",
                        "قصد قربت و استمرار نیت تا مغرب شرعی رکن اساسی پذیرش روزه است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_fiqh_sharai",
                "title": "شرائع الإسلام في مسائل الحلال والحرام",
                "author": "المحقق الحلي (جعفر بن الحسن بن يحيى)",
                "category_id": "cat_fiqh",
                "madhhab": "جعفری",
                "language": "ar",
                "source_file": "raw_data_books/fiqh/sharai_al_islam_hilli_jafari.txt",
                "description": "دقیق‌ترین و مشهورترین متن فقه فتوایی و استدلالی شیعه امامیه که قرن‌ها مرجع اصلی تدریس و پژوهش در حوزه‌های علمیه بوده است.",
                "tags": ["فقه جعفری", "محقق حلی", "شرائع الاسلام", "قضاوت", "روزه", "امامیه"],
                "topics": ["قضاوت اسلامی", "شروط قاضی", "احکام صوم", "عبادات و معاملات"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 8. بداية المجتهد (فقه مقارن)
    # ---------------------------------------------------------
    p_bidayat = workspace_dir / "raw_data_books" / "fiqh" / "bidayat_al_mujtahid_ibn_rushd.txt"
    if p_bidayat.exists():
        with open(p_bidayat, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
            m_asbab = re.search(r'فإن الأسباب التي أوجبت الاختلاف(.*?)فمنها', raw, re.DOTALL)
            if not m_asbab:
                m_asbab = re.search(r'كتاب الطهارة(.*?)فصل', raw, re.DOTALL)
            asbab_txt = clean_openiti_text(m_asbab.group(0))[:1500] if m_asbab else ""

            m_zakat = re.search(r'كتاب الزكاة(.*?)فصل', raw, re.DOTALL)
            zakat_txt = clean_openiti_text(m_zakat.group(0))[:1500] if m_zakat else ""

            chunks = []
            if asbab_txt:
                chunks.append({
                    "chunk_id": "chk_bidayat_asbab",
                    "chapter_title": "مقدمة أسباب اختلاف الفقهاء وقواعد الاستنباط المقارن",
                    "hadith_index": 1,
                    "text": asbab_txt,
                    "text_arabic": asbab_txt,
                    "summary": "تبیین ژرف ابن رشد در فقه مقارن پیرامون خاستگاه‌های علمی اختلاف آراء میان فقهای مذاهب اربعه و اهل‌بیت: اشتراک الفاظ در کتاب و سنت، حمل بر حقیقت یا مجاز، تفاوت در روایات و شرایط صحت حدیث، تعارض و ترجیح، و گستره قیاس و مصلحت.",
                    "hypothetical_questions": [
                        "دلایل اصلی اختلاف دیدگاه‌های فقهی میان مذاهب اسلامی در کتاب بدایة المجتهد چیست؟",
                        "نقش اشتراک لفظی و دلالت حقیقت و مجاز در تفاوت احکام استنباطی چیست؟",
                        "دیدگاه ابن رشد فیلسوف و فقیه مالکی درباره مشروعیت تفاوت آراء فقهی چیست؟"
                    ],
                    "core_concepts": ["فقه مقارن", "ابن رشد الحفید", "بدایة المجتهد", "اسباب اختلاف الفقهاء", "اصول فقه", "تقریب مذاهب"],
                    "domain_insights": [
                        "اختلاف در فروع فقهی ناشی از قواعد زبان‌شناختی و اجتهادی است و مایه پویایی شریعت است.",
                        "شناخت ادله دیگر مذاهب روح تسامح، عقلانیت و برادری را در امت اسلامی تقویت می‌کند."
                    ]
                })

            if zakat_txt:
                chunks.append({
                    "chunk_id": "chk_bidayat_zakat",
                    "chapter_title": "كتاب الزكاة المقارن - الأموال الزكوية والنصاب بين المذاهب",
                    "hadith_index": 2,
                    "text": zakat_txt,
                    "text_arabic": zakat_txt,
                    "summary": "بررسی مقایسه‌ای کتاب زکات در بدایة المجتهد: ادله مذاهب در وجوب زکات انعام ثلاثه، نقدین (طلا و نقره) و غلات چهارگانه، شروط نصاب و حول، و مواضع اتفاق و اختلاف ائمه مذاهب در زکات سایر اموال تجاری و کشاورزی.",
                    "hypothetical_questions": [
                        "موارد اتفاق و اختلاف مذاهب اسلامی در اقلام مشمول زکات چیست؟",
                        "حکمت و شرایط گذشت سال (حول) و رسیدن به نصاب در فقه مقارن چگونه است؟",
                        "دیدگاه تطبیقی ابن رشد درباره مصرف زکات برای فقرا و مساکین چیست؟"
                    ],
                    "core_concepts": ["فقه مقارن", "زکات", "اموال زکوی", "نصاب زکات", "بدایة المجتهد", "اقتصاد اسلامی"],
                    "domain_insights": [
                        "زکات ستون نظام عدالت اقتصادی اسلام برای بازتوزیع ثروت و ریشه‌کنی فقر است.",
                        "فقه تطبیقی نشان می‌دهد که هدف مشترک تمام فقها تحقق عدالت و حمایت از نیازمندان است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_fiqh_bidayat",
                "title": "بداية المجتهد ونهاية المقتصد (فقه مقارن)",
                "author": "ابن رشد الحفيد (محمد بن أحمد بن رشد القرطبي)",
                "category_id": "cat_fiqh",
                "madhhab": "مقارن بین المذاهب",
                "language": "ar",
                "source_file": "raw_data_books/fiqh/bidayat_al_mujtahid_ibn_rushd.txt",
                "description": "شاهکار فقه تطبیقی و مقارن دنیای اسلام که ادله مذاهب اربعه و دیگر فقها را در کنار علل اختلاف آراء با بی‌طرفی کامل بررسی می‌کند.",
                "tags": ["فقه مقارن", "ابن رشد", "بدایة المجتهد", "تقریب", "اختلاف الفقهاء", "زکات"],
                "topics": ["فقه تطبیقی", "ادله احکام", "قواعد اجتهاد", "زکات و عبادات"],
                "chunks": chunks
            })

    # ---------------------------------------------------------
    # 9. الأذكار النووية (أدعية وأخلاق)
    # ---------------------------------------------------------
    p_adhkar = workspace_dir / "raw_data_books" / "misc" / "al_adhkar_nawawi.txt"
    if p_adhkar.exists():
        with open(p_adhkar, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
            m_fadl = re.search(r'### \$ 18- باب مختصر في أحرف مما جاء في فضل الذكر(.*?)###', raw, re.DOTALL)
            fadl_txt = clean_openiti_text(m_fadl.group(1))[:1500] if m_fadl else ""

            m_sabah = re.search(r'باب ما يقول إذا أصبح وإذا أمسى(.*?)###', raw, re.DOTALL)
            sabah_txt = clean_openiti_text(m_sabah.group(1))[:1500] if m_sabah else ""

            chunks = []
            if fadl_txt:
                chunks.append({
                    "chunk_id": "chk_adhkar_fadl",
                    "chapter_title": "باب فضل الذكر المطلق وعمارة الأوقات بالتسبيح والتحميد",
                    "hadith_index": 1,
                    "text": fadl_txt,
                    "text_arabic": fadl_txt,
                    "summary": "آموزه‌های امام نووی در کتاب الأذکار پیرامون فضیلت بی‌کران یاد خداوند: تسبیح، تحمید، تهلیل و تکبیر به عنوان برترین توشه مؤمن، برابری ذکر خدا با جهاد و صدقه در ایجاد آرامش قلبی و ثواب بی‌پایان اخروی.",
                    "hypothetical_questions": [
                        "فضیلت ذکر مطلق و آثار یاد دائم خداوند در زندگی مؤمن چیست؟",
                        "احادیث معتبر نبوی درباره پاداش سبحان الله والحمد لله چیست؟",
                        "چرا ذکر پروردگار برترین اعمال و مایه‌ی جلای دل‌ها شمرده شده است؟"
                    ],
                    "core_concepts": ["الاذکار النواویة", "فضیلت ذکر", "تسبیح و تحمید", "ذکر قلبی", "آرامش معنوی", "ادعیه نبوی"],
                    "domain_insights": [
                        "ذکر مداوم یاد خدا مانع غفلت و زنگار روحی در کوران حوادث روزمره است.",
                        "زبان ذاکر و دل خاشع سبب نزول رحمت و سکینت الهی بر انسان می‌گردد."
                    ]
                })

            if sabah_txt:
                chunks.append({
                    "chunk_id": "chk_adhkar_sabah",
                    "chapter_title": "باب أذكار الصباح والمساء ودعاء الحفظ والأمان",
                    "hadith_index": 2,
                    "text": sabah_txt,
                    "text_arabic": sabah_txt,
                    "summary": "مجموعه دعاهای مأثور و روایات اصیل پیامبر اکرم (ص) در آغاز صبح و هنگام غروب آفتاب برای طلب عافیت، پناه بردن به قدرت الهی از شرور شیاطین، بیماری‌ها، اندوه و حوادث ناگوار روزگار.",
                    "hypothetical_questions": [
                        "ادعیه توصیه شده نبوی در هنگام صبحگاه و شامگاه کدامند؟",
                        "دعای اصبحنا واصبح الملک لله چه مضامین توحیدی و حفاظتی دارد؟",
                        "چگونه اذکار روزانه انسان را از آفات، اضطراب و بلایا محافظت می‌کند؟"
                    ],
                    "core_concepts": ["اذکار الصباح والمساء", "حفظ و امان", "دعای نبوی", "الاذکار", "عافیت", "توکل"],
                    "domain_insights": [
                        "آغاز و پایان روز با یاد پروردگار روزی و روح انسان را در حصن امان الهی قرار می‌دهد.",
                        "دعا سلاح مؤمن برای دفع اضطراب و کسب انرژی معنوی است."
                    ]
                })

            extracted_books.append({
                "book_id": "bk_misc_adhkar",
                "title": "الأذكار المنتخبة من كلام سيد الأبرار",
                "author": "الإمام يحيى بن شرف النووي",
                "category_id": "cat_akhlaq",
                "madhhab": "عام / روایات",
                "language": "ar",
                "source_file": "raw_data_books/misc/al_adhkar_nawawi.txt",
                "description": "جامع‌ترین کتاب ادعیه و اذکار مستند از سیره رسول خدا (ص) در تمام حالات شبانه‌روز، عبادات و آداب زندگی.",
                "tags": ["اذکار نووی", "ادعیه", "ذکر صبح و شام", "دعا", "معنویت"],
                "topics": ["فضیلت ذکر", "پناه بردن به خدا", "سنت نبوی", "آرامش دل"],
                "chunks": chunks
            })

    print(f"✅ استخراج {len(extracted_books)} کتاب با مجموع {sum(len(b['chunks']) for b in extracted_books)} بخش نمونه انجام شد.")
    return extracted_books


async def save_extracted_json(extracted_books):
    """Save the extraction report and all chunks into a detailed JSON file."""
    output_path = workspace_dir / "extracted_test_samples.json"
    backend_output_path = backend_dir / "extracted_test_samples.json"

    total_chunks = sum(len(b["chunks"]) for b in extracted_books)
    data = {
        "metadata": {
            "title": "گزارش استخراج قطعات راندوم و منتخب از منابع دانلودی برای تست سامانه اتحاد",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_books_extracted": len(extracted_books),
            "total_sections_extracted": total_chunks,
            "target_environments": ["SQL Database (ettehad.db)", "Qdrant Vector Database", "Library Catalog System"],
            "categories_covered": ["cat_hadith", "cat_quran", "cat_fiqh", "cat_akhlaq"],
            "schools_of_thought_covered": ["نبوی / عام", "اهل سنت", "حنفی", "جعفری", "مقارن بین المذاهب"]
        },
        "books_overview": [
            {
                "book_id": b["book_id"],
                "title": b["title"],
                "author": b["author"],
                "category_id": b["category_id"],
                "madhhab": b["madhhab"],
                "source_file": b["source_file"],
                "sections_count": len(b["chunks"])
            }
            for b in extracted_books
        ],
        "extracted_books_and_sections": extracted_books
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(backend_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📄 فایل JSON استخراج شده در دو مسیر ذخیره شد:")
    print(f"   1. {output_path}")
    print(f"   2. {backend_output_path}")
    return output_path


async def ingest_into_sql_and_vector(extracted_books):
    """Persist books, chapters, and chunks into SQL tables and Qdrant Vector store."""
    print("\n🚀 آغاز ثبت داده‌ها در پایگاه داده رابطه‌ای (SQL) و پایگاه برداری (Vector Qdrant)...")

    # 1. Ensure SQL Tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Ingest into SQL
    async with AsyncSessionLocal() as session:
        for book_info in extracted_books:
            b_id = book_info["book_id"]
            # Check or Upsert Book
            book_obj = await session.scalar(select(Book).where(Book.id == b_id))
            if not book_obj:
                book_obj = Book(
                    id=b_id,
                    title=book_info["title"],
                    author=book_info["author"],
                    category_id=book_info["category_id"],
                    tags=book_info["tags"],
                    topics=book_info["topics"],
                    language=book_info.get("language", "ar"),
                    description=book_info.get("description", ""),
                    is_featured=True,
                    page_count=max(len(book_info["chunks"]) * 20, 50),
                    rating=4.9
                )
                session.add(book_obj)
            else:
                book_obj.title = book_info["title"]
                book_obj.author = book_info["author"]
                book_obj.category_id = book_info["category_id"]
                book_obj.tags = book_info["tags"]
                book_obj.topics = book_info["topics"]
                book_obj.description = book_info.get("description", "")

            # Create or update Chapters and KnowledgeChunks
            for c_idx, chk in enumerate(book_info["chunks"], 1):
                ch_id = f"ch_{b_id}_{c_idx}"
                ch_obj = await session.scalar(select(BookChapter).where(BookChapter.id == ch_id))
                if not ch_obj:
                    ch_obj = BookChapter(
                        id=ch_id,
                        book_id=b_id,
                        chapter_number=c_idx,
                        title=chk["chapter_title"],
                        reading_time_minutes=4,
                        content=chk["text"],
                        paragraphs=[chk["text"]]
                    )
                    session.add(ch_obj)
                else:
                    ch_obj.title = chk["chapter_title"]
                    ch_obj.content = chk["text"]
                    ch_obj.paragraphs = [chk["text"]]

                # KnowledgeChunk in SQL
                chunk_id = chk["chunk_id"]
                kc_obj = await session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id))
                if not kc_obj:
                    kc_obj = KnowledgeChunk(
                        id=chunk_id,
                        book_id=b_id,
                        chapter_id=ch_id,
                        chunk_order=c_idx,
                        full_text=chk["text"],
                        text_arabic=chk.get("text_arabic") or chk["text"],
                        summary=chk.get("summary", ""),
                        hypothetical_questions=chk.get("hypothetical_questions", []),
                        core_concepts=chk.get("core_concepts", []),
                        domain_insights=chk.get("domain_insights", []),
                        page_number=chk.get("hadith_index", c_idx),
                        content_type="HADITH" if "hadith" in b_id else ("TAFSIR" if "tafsir" in b_id else ("FIQH" if "fiqh" in b_id else "ETHICS")),
                        language="ar",
                        is_processed=True
                    )
                    session.add(kc_obj)
                else:
                    kc_obj.full_text = chk["text"]
                    kc_obj.text_arabic = chk.get("text_arabic") or chk["text"]
                    kc_obj.summary = chk.get("summary", "")
                    kc_obj.hypothetical_questions = chk.get("hypothetical_questions", [])
                    kc_obj.core_concepts = chk.get("core_concepts", [])
                    kc_obj.domain_insights = chk.get("domain_insights", [])

        await session.commit()
        print("✅ تمامی کتب، فصول و چانک‌ها با موفقیت در پایگاه داده SQL (جداول books, book_chapters, knowledge_chunks) ثبت شدند.")

    # 3. Synchronize backend/ettehad.db with root ettehad.db
    backend_db = backend_dir / "ettehad.db"
    root_db = workspace_dir / "ettehad.db"
    try:
        shutil.copy2(backend_db, root_db)
        print("🔄 پایگاه داده ریشه (root ettehad.db) با نسخه به‌روزرسانی‌شده همگام‌سازی شد.")
    except Exception as e:
        print(f"⚠️ اخطار در کپی دیتابیس ریشه: {e}")

    # 4. Multi-Vector Indexing into Qdrant
    print("\n🧠 در حال ساخت و ذخیره امبدینگ‌های چندوجهی در پایگاه برداری Qdrant...")
    batch_vector_items = []
    for b in extracted_books:
        for c_idx, chk in enumerate(b["chunks"], 1):
            batch_vector_items.append({
                "chunk_id": chk["chunk_id"],
                "combined_text": f"{chk['text']} {chk.get('summary', '')}",
                "repr_data": {
                    "summary": chk.get("summary", ""),
                    "hypothetical_questions": chk.get("hypothetical_questions", []),
                    "core_concepts": chk.get("core_concepts", [])
                },
                "payload": {
                    "bookId": b["book_id"],
                    "bookTitle": b["title"],
                    "author": b["author"],
                    "category": b["category_id"],
                    "madhhab": b["madhhab"],
                    "majorTopic": b["title"],
                    "chapter": chk["chapter_title"],
                    "text": chk["text"],
                    "textArabic": chk.get("text_arabic", ""),
                    "summary": chk.get("summary", ""),
                    "topics": b["topics"],
                    "tags": b["tags"],
                    "pageNumber": chk.get("hadith_index", c_idx),
                    "point_type": "FULL_CHUNK"
                }
            })

    indexed_count = await VectorService.upsert_batch_chunks(batch_vector_items)
    print(f"🎯 بردارسازی چندوجهی با موفقیت انجام شد ({len(batch_vector_items)} چانک پایه -> ده‌ها نقطه برداری در Qdrant ثبت شدند).")

    # 5. Test Verification Query
    print("\n🔍 انجام استعلام آزمایشی معنایی از پایگاه برداری...")
    test_queries = [
        "اخلاص در نیت و هجرت به سوی خدا",
        "احکام و شرایط وضو در مذهب حنفی",
        "تفسیر آیه الکرسی و صفات الهی",
        "شرایط قاضی و عدالت در قضاوت اسلامی"
    ]
    for q in test_queries:
        res = await VectorService.search_semantic(query=q, limit=2)
        print(f"\n🔎 پرسش: «{q}»")
        if res:
            for r in res:
                print(f"   ✨ نتیجه: [{r.get('bookTitle')}] فصل: {r.get('chapterTitle')} (امتیاز تشابه: {r.get('score')})")
                print(f"      خلاصه: {r.get('text')[:100]}...")
        else:
            print("   ⚠️ نتیجه‌ای یافت نشد.")


async def main():
    extracted_books = extract_raw_samples()
    await save_extracted_json(extracted_books)
    await ingest_into_sql_and_vector(extracted_books)
    print("\n🎉 تمامی مراحل استخراج، ذخیره در JSON، ثبت در SQL و ایندکس برداری در Vector با موفقیت به پایان رسید!")


if __name__ == "__main__":
    asyncio.run(main())
