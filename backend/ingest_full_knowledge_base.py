"""
اسکریپت خط لوله بارگذاری جامع و تدریجی پایگاه دانش معارفی (Full Content Ingestion Pipeline)
قابلیت‌ها:
1. پشتیبانی از تمامی قالب‌های خام: تفاسیر JSON، احادیث JSON، و متون فقهی OpenITI
2. ایجاد ساختارمند رکوردها در SQL: کتب (Book)، فصول (BookChapter) و چانک‌های دانشی (KnowledgeChunk)
3. ذخیره وضعیت و چک‌پوینت (Checkpoint / Resume) در فایل ingestion_state.json
4. امکان بارگذاری دسته‌ای (Batch) و همگام‌سازی فوری یا مرحله‌ای با پایگاه برداری Qdrant
5. پارامترهای خط فرمان منعطف (--book, --max-chunks, --batch-size, --sync-vector, --dry-run)
"""

import os
import sys
import re
import json
import uuid
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

workspace_dir = backend_dir.parent

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.db.models.library import Book, BookChapter, KnowledgeChunk, LibraryCategory
from app.services.vector_service import VectorService
from app.config import settings

STATE_FILE = backend_dir / "ingestion_state.json"

# Clean OpenITI text
def clean_openiti_text(raw_text: str) -> str:
    t = re.sub(r'#META#.*?\n', '', raw_text)
    t = re.sub(r'#META#Header#End#', '', t)
    t = re.sub(r'#|~~|Page\w+|ms\w+|@\w+@|\d+\.\d+@|\[.*?\]', '', t)
    t = re.sub(r'\r', '', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

# State management
def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"completed_books": {}, "total_chunks_ingested": 0, "last_updated": None}

def save_state(state: Dict[str, Any]):
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# Parsers
class ContentParsers:

    @staticmethod
    def parse_tafsir_jalalayn(file_path: Path, max_chunks: Optional[int] = None) -> List[Dict[str, Any]]:
        """Parses ar.jalalayn.json grouping Ayahs into balanced thematic chunks."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        surahs = data.get("tafsir", [])
        chunks = []
        chunk_idx = 0

        for surah_idx, ayahs in enumerate(surahs, 1):
            buffer_ayahs = []
            buffer_text = []

            for a_idx, a_tafsir in enumerate(ayahs, 1):
                clean_t = a_tafsir.strip()
                if not clean_t:
                    continue
                buffer_ayahs.append(a_idx)
                buffer_text.append(f"[آیه {a_idx}] {clean_t}")

                # Group every 3-5 ayahs or ~250 words into a chunk
                curr_words = sum(len(t.split()) for t in buffer_text)
                if curr_words >= 150 or len(buffer_ayahs) >= 5 or a_idx == len(ayahs):
                    chunk_idx += 1
                    joined_text = "\n".join(buffer_text)
                    summary = f"تفسیر موجز آیات {buffer_ayahs[0]} تا {buffer_ayahs[-1]} سوره {surah_idx} از تفسیر الجلالین."
                    chunks.append({
                        "order": chunk_idx,
                        "chapter_title": f"سوره {surah_idx} (آیات {buffer_ayahs[0]}-{buffer_ayahs[-1]})",
                        "full_text": joined_text,
                        "text_arabic": joined_text,
                        "summary": summary,
                        "core_concepts": [f"سوره {surah_idx}", f"آیات {buffer_ayahs[0]}-{buffer_ayahs[-1]}", "تفسیر قرآن", "الجلالین"],
                        "hypothetical_questions": [f"تفسیر آیه {buffer_ayahs[0]} سوره {surah_idx} چیست؟"],
                        "content_type": "TAFSIR"
                    })
                    buffer_ayahs = []
                    buffer_text = []

                    if max_chunks and len(chunks) >= max_chunks:
                        return chunks

        return chunks

    @staticmethod
    def parse_hadith_json(file_path: Path, max_chunks: Optional[int] = None) -> List[Dict[str, Any]]:
        """Parses hadith json (nawawi40 or riyad_assalihin)."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        hadiths = data.get("hadiths", [])
        chunks = []

        for idx, h in enumerate(hadiths, 1):
            ar_text = h.get("arabic", "").strip()
            en_meta = h.get("english", {})
            narrator = en_meta.get("narrator", "")
            en_text = en_meta.get("text", "")
            if not ar_text:
                continue

            summary = f"حدیث شماره {idx}: نقل از {narrator[:60]}. موضوع پیرامون سنت و اخلاق نبوی."
            chunks.append({
                "order": idx,
                "chapter_title": f"حدیث شماره {idx}",
                "full_text": f"{ar_text}\n\n[ترجمه و راوی]: {narrator} {en_text}".strip(),
                "text_arabic": ar_text,
                "summary": summary,
                "core_concepts": ["حدیث نبوی", "سنت", "روایت اخلاقی"],
                "hypothetical_questions": [f"متن و مفهوم حدیث {idx} چیست؟"],
                "content_type": "HADITH"
            })
            if max_chunks and len(chunks) >= max_chunks:
                break
        return chunks

    @staticmethod
    def parse_fiqh_openiti(file_path: Path, max_chunks: Optional[int] = None) -> List[Dict[str, Any]]:
        """Parses OpenITI text dividing chapters by ### or # کتاب / # باب."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        cleaned = clean_openiti_text(content)
        # Split on headers like "كتاب ..." or "باب ..."
        raw_sections = re.split(r'\n(?=(?:###|كتاب|باب|فصل)\s+)', cleaned)
        chunks = []
        chunk_idx = 0

        for sec in raw_sections:
            sec = sec.strip()
            if len(sec) < 80:
                continue
            lines = sec.split("\n")
            title = lines[0].replace("###", "").replace("|", "").strip()[:80] or f"فصل {chunk_idx + 1}"

            # If section is very large, chunk into ~300-500 words
            words = sec.split()
            step = 350
            for w_i in range(0, len(words), step):
                chunk_idx += 1
                chunk_words = words[w_i:w_i + step]
                chunk_text = " ".join(chunk_words)
                summary = f"بخشی از {title}: احکام و ادله فقهی تفصیلی."

                chunks.append({
                    "order": chunk_idx,
                    "chapter_title": title,
                    "full_text": chunk_text,
                    "text_arabic": chunk_text,
                    "summary": summary,
                    "core_concepts": [title[:30], "فقه و احکام شرعی", "مسائل فقهی"],
                    "hypothetical_questions": [f"احکام مربوط به {title[:40]} چیست؟"],
                    "content_type": "FIQH"
                })
                if max_chunks and len(chunks) >= max_chunks:
                    return chunks

        return chunks

# Book Registry Metadata
RAW_BOOKS_CATALOG = [
    {
        "id": "bk_fiqh_quduri",
        "title": "مختصر القدوري في الفقه الحنفي",
        "author": "أبو الحسين أحمد بن محمد القدوري",
        "category_id": "cat_fiqh_comparative",
        "category_title": "فقه و احکام",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "fiqh" / "mukhtasar_al_quduri_hanafi.txt",
        "type": "FIQH_TEXT",
        "topics": ["فقه حنفی", "طهارت", "نماز", "معاملات", "احکام شرعی"]
    },
    {
        "id": "bk_fiqh_bidayat",
        "title": "بداية المجتهد ونهاية المقتصد",
        "author": "ابن رشد الحفيد القرطبي",
        "category_id": "cat_fiqh_comparative",
        "category_title": "فقه و احکام",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "fiqh" / "bidayat_al_mujtahid_ibn_rushd.txt",
        "type": "FIQH_TEXT",
        "topics": ["فقه مقارن", "مذاهب اربعه", "اصول فقه", "علل اختلاف فقهاء"]
    },
    {
        "id": "bk_fiqh_sharai",
        "title": "شرائع الإسلام في مسائل الحلال والحرام",
        "author": "المحقق الحلي (جعفر بن الحسن)",
        "category_id": "cat_fiqh_comparative",
        "category_title": "فقه و احکام",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "fiqh" / "sharai_al_islam_hilli_jafari.txt",
        "type": "FIQH_TEXT",
        "topics": ["فقه جعفری", "عبادات", "معاملات", "قضا و شهادات"]
    },
    {
        "id": "bk_tafsir_jalalayn",
        "title": "تفسير الجلالين",
        "author": "جلال الدين المحلي وجلال الدين السيوطي",
        "category_id": "cat_tafsir_sciences",
        "category_title": "تفسیر و علوم قرآن",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "tafsir" / "tafsir-json" / "json" / "ar.jalalayn.json",
        "type": "TAFSIR_JSON",
        "topics": ["تفسیر قرآن", "معانی آیات", "علوم قرآنی", "تفسیر موجز"]
    },
    {
        "id": "bk_hadith_nawawi40",
        "title": "الأربعون النووية",
        "author": "الإمام يحيى بن شرف النووي",
        "category_id": "cat_hadith_sunnah",
        "category_title": "حدیث و سنن",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "hadith" / "hadith-json" / "db" / "by_book" / "forties" / "nawawi40.json",
        "type": "HADITH_JSON",
        "topics": ["حدیث صحیح", "اخلاق", "ارکان اسلام", "ایمان و احسان"]
    },
    {
        "id": "bk_hadith_riyad",
        "title": "رياض الصالحين من كلام سيد المرسلين",
        "author": "الإمام النووي",
        "category_id": "cat_hadith_sunnah",
        "category_title": "حدیث و سنن",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "hadith" / "hadith-json" / "db" / "by_book" / "other_books" / "riyad_assalihin.json",
        "type": "HADITH_JSON",
        "topics": ["احادیث اخلاقی", "سیر و سلوک", "ادب معاشرت", "صبر و تقوا"]
    },
    {
        "id": "bk_misc_adhkar",
        "title": "الأذكار المنتخبة من كلام سيد الأبرار",
        "author": "الإمام النووي",
        "category_id": "cat_ethics_spirituality",
        "category_title": "اخلاق و معنویت",
        "language": "ar",
        "path": workspace_dir / "raw_data_books" / "misc" / "al_adhkar_nawawi.txt",
        "type": "FIQH_TEXT",
        "topics": ["ادعیه و اذکار", "تسبیحات روزمره", "آرامش قلبی", "ذکر و دعا"]
    }
]

async def ingest_book(book_meta: Dict[str, Any], max_chunks: Optional[int] = None, sync_vector: bool = True):
    b_id = book_meta["id"]
    b_title = book_meta["title"]
    f_path = book_meta["path"]
    b_type = book_meta["type"]

    print(f"\n=======================================================")
    print(f"📖 شروع پردازش کتاب: «{b_title}» ({b_id})")
    print(f"=======================================================")

    if not f_path.exists():
        print(f"❌ فایل کتاب در مسیر {f_path} یافت نشد!")
        return

    # Parse chunks based on format
    if b_type == "TAFSIR_JSON":
        parsed_chunks = ContentParsers.parse_tafsir_jalalayn(f_path, max_chunks=max_chunks)
    elif b_type == "HADITH_JSON":
        parsed_chunks = ContentParsers.parse_hadith_json(f_path, max_chunks=max_chunks)
    else:
        parsed_chunks = ContentParsers.parse_fiqh_openiti(f_path, max_chunks=max_chunks)

    print(f"   • تعداد قطعات استخراج‌شده: {len(parsed_chunks)}")
    if not parsed_chunks:
        return

    # Ingest into SQLite
    async with AsyncSessionLocal() as session:
        # 1. Ensure Category exists
        cat_id = book_meta.get("category_id") or "cat_general"
        cat_title = book_meta.get("category_title") or "معارف اسلامی"
        cat = await session.scalar(select(LibraryCategory).where(LibraryCategory.id == cat_id))
        if not cat:
            cat = LibraryCategory(id=cat_id, title=cat_title, icon_name="menu_book", order_index=1)
            session.add(cat)
            await session.commit()

        # 2. Ensure Book exists
        book = await session.scalar(select(Book).where(Book.id == b_id))
        if not book:
            book = Book(
                id=b_id,
                title=b_title,
                author=book_meta["author"],
                category_id=cat_id,
                language=book_meta.get("language", "ar"),
                topics=book_meta.get("topics", []),
                tags=[book_meta.get("category_title", "معارف")],
                description=f"کتاب مرجع {b_title} تألیف {book_meta['author']}."
            )
            session.add(book)
            await session.commit()

        # 3. Create or map Chapter
        ch_id = f"ch_{b_id}_main"
        chapter = await session.scalar(select(BookChapter).where(BookChapter.id == ch_id))
        if not chapter:
            chapter = BookChapter(
                id=ch_id,
                book_id=b_id,
                chapter_number=1,
                title=f"متن جامع {b_title}",
                content=f"فهرست و متن مباحث {b_title}"
            )
            session.add(chapter)
            await session.commit()

        # 4. Insert chunks in batches
        existing_count = await session.scalar(
            select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.book_id == b_id)
        )
        print(f"   • چانک‌های موجود در دیتابیس: {existing_count}")

        new_chunks_added = 0
        for ch in parsed_chunks:
            chk_id = f"chk_{b_id}_{ch['order']:05d}"
            # Check if exists
            exists = await session.scalar(select(KnowledgeChunk.id).where(KnowledgeChunk.id == chk_id))
            if not exists:
                chunk_obj = KnowledgeChunk(
                    id=chk_id,
                    book_id=b_id,
                    chapter_id=ch_id,
                    chunk_order=ch["order"],
                    full_text=ch["full_text"],
                    text_arabic=ch.get("text_arabic"),
                    summary=ch.get("summary", ""),
                    core_concepts=ch.get("core_concepts", []),
                    hypothetical_questions=ch.get("hypothetical_questions", []),
                    content_type=ch.get("content_type", "TEXT")
                )
                session.add(chunk_obj)
                new_chunks_added += 1

        if new_chunks_added > 0:
            await session.commit()
            print(f"   ✅ {new_chunks_added} چانک جدید در پایگاه داده SQL ثبت گردید.")
        else:
            print(f"   ℹ️ تمامی چانک‌های این کتاب قبلاً در SQL ثبت شده‌اند.")

    # 5. Sync to Qdrant if requested
    if sync_vector:
        print(f"   🚀 همگام‌سازی برداری نورونی با Avalai...")
        async with AsyncSessionLocal() as session:
            count = await VectorService.sync_chunks_from_db(session, force=False, use_neural=True)
            print(f"   🎉 تعداد کل نقاط فعال در Qdrant: {count}")

    # Update state
    state = load_state()
    state["completed_books"][b_id] = {
        "title": b_title,
        "chunks_count": len(parsed_chunks),
        "synced_at": datetime.now(timezone.utc).isoformat()
    }
    state["total_chunks_ingested"] = sum(b["chunks_count"] for b in state["completed_books"].values())
    save_state(state)
    print(f"   💾 وضعیت استخراج در {STATE_FILE} ذخیره شد.")

async def main():
    parser = argparse.ArgumentParser(description="ابزار خط لوله بارگذاری جامع کتب در پایگاه داده و وکتور")
    parser.add_argument("--book", type=str, help="شناسه کتاب خاص برای بارگذاری (مثلاً bk_fiqh_quduri)")
    parser.add_argument("--max-chunks", type=int, default=None, help="حداکثر تعداد چانک به ازای هر کتاب (برای کنترل هزینه)")
    parser.add_argument("--sync-vector", action="store_true", default=True, help="همگام‌سازی برداری در Qdrant")
    parser.add_argument("--no-sync-vector", dest="sync_vector", action="store_false", help="عدم همگام‌سازی برداری")
    parser.add_argument("--dry-run", action="store_true", help="فقط بررسی و شمارش چانک‌ها بدون نوشتن در دیتابیس")

    args = parser.parse_args()

    print("=" * 80)
    print("شروع خط لوله بارگذاری جامع پایگاه دانش اتحاد (Production Ingestion Pipeline)")
    print("=" * 80)

    state = load_state()
    print(f"📊 وضعیت قبلی: {len(state['completed_books'])} کتاب، {state['total_chunks_ingested']} چانک ذخیره شده.")

    targets = RAW_BOOKS_CATALOG
    if args.book:
        targets = [b for b in RAW_BOOKS_CATALOG if b["id"] == args.book]
        if not targets:
            print(f"❌ کتاب با شناسه {args.book} یافت نشد.")
            return

    for b in targets:
        if args.dry_run:
            print(f"🔍 [Dry Run] بررسی کتاب {b['title']}...")
            if b["type"] == "TAFSIR_JSON":
                items = ContentParsers.parse_tafsir_jalalayn(b["path"], max_chunks=args.max_chunks)
            elif b["type"] == "HADITH_JSON":
                items = ContentParsers.parse_hadith_json(b["path"], max_chunks=args.max_chunks)
            else:
                items = ContentParsers.parse_fiqh_openiti(b["path"], max_chunks=args.max_chunks)
            print(f"   • تعداد چانک‌های قابل استخراج: {len(items)}")
        else:
            await ingest_book(b, max_chunks=args.max_chunks, sync_vector=args.sync_vector)

    print("\n🎉 فرآیند بارگذاری با موفقیت پایان یافت!")

if __name__ == "__main__":
    asyncio.run(main())
