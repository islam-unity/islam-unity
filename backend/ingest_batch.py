import os
import sys
import asyncio
import argparse
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure stdout for UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import AsyncSessionLocal, engine
from app.db.base import Base
from app.services.library_service import LibraryService


async def main_async(file_path: str, batch_size: int, resume: bool = True, export_dir: str = "./media/ai_exports"):
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"❌ خطا: فایل مورد نظر یافت نشد: {path}")
        sys.exit(1)

    print(f"\n📂 بارگذاری فایل: {path.name} ({path.stat().st_size:,} بایت)")
    print(f"⚡ اندازه دسته‌ها (Batch Size): {batch_size}")
    print(f"🔄 قابلیت ادامه کار در صورت قطعی (Resume): {'فعال' if resume else 'غیرفعال'}")
    print(f"📁 پوشه ذخیره خروجی‌های LLM: {export_dir}")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(path, "rb") as f:
        file_bytes = f.read()

    async with AsyncSessionLocal() as session:
        try:
            result = await LibraryService.ingest_from_json_file(
                db=session,
                file_bytes=file_bytes,
                filename=path.name,
                batch_size=batch_size,
                resume=resume,
                export_dir=export_dir
            )
            print("\n🎉 عملیات با موفقیت به پایان رسید:")
            print(f"   • تعداد کتب پردازش‌شده: {result.get('booksProcessed', 1)}")
            print(f"   • مجموع فصول: {result.get('totalChapters', 0)}")
            print(f"   • مجموع چانک‌های نمایه‌سازی‌شده: {result.get('totalChunksIndexed', 0)}")
            for b in result.get('books', []):
                if b.get('exportFile'):
                    print(f"   • 💾 فایل منظم خروجی LLM: {b.get('exportFile')}")
                if b.get('resumedChunks'):
                    print(f"   • 🔄 چانک‌های بازیابی‌شده از قبل: {b.get('resumedChunks')}")
        except Exception as e:
            print(f"\n❌ خطا در پردازش فایل: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ورود دسته‌ای داده‌ها به سامانه هوشمند اتحاد با نمایش مراحل، درصد باقی‌مانده و ذخیره‌سازی منظم خروجی‌های LLM"
    )
    parser.add_argument(
        "file",
        help="مسیر فایل JSON یا JSONL ورودی (مثلاً dataset - Copy.jsonl یا book.json)"
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=5,
        help="تعداد چانک‌ها در هر دسته پردازشی هوش مصنوعی (پیش‌فرض: 5)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="غیرفعال‌سازی بررسی سابقه و پردازش مجدد همه چانک‌ها از ابتدا"
    )
    parser.add_argument(
        "--export-dir",
        default="./media/ai_exports",
        help="مسیر پوشه ذخیره‌سازی فایل‌های منظم خروجی LLM (پیش‌فرض: ./media/ai_exports)"
    )

    args = parser.parse_args()
    asyncio.run(main_async(args.file, args.batch_size, resume=not args.no_resume, export_dir=args.export_dir))


if __name__ == "__main__":
    main()
