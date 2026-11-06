import sys
import time
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import AsyncSessionLocal
from app.services.vector_service import VectorService
from app.services.recommendation_service import RecommendationService

async def main():
    print("=" * 70)
    print("همگام‌سازی و تولید امبدینگ‌های نورونی Avalai برای تمام چانک‌های کتابخانه")
    print("=" * 70)

    t0 = time.perf_counter()
    async with AsyncSessionLocal() as session:
        count = await VectorService.sync_chunks_from_db(session, force=True, use_neural=True)
    t_end = time.perf_counter()

    print(f"\n✅ همگام‌سازی کامل شد: {count} نقطه برداری نورونی ثبت شدند در {(t_end - t0):.2f} ثانیه.")

    # Test Search on Sample Blind Queries
    test_queries = [
        "موقع وضو گرفتن، دقیقاً کجای سرم رو باید مسح بکشم و چقدرش واجبه؟",
        "توی جمع دوستان یکی رو دیدم که ادعای مسلمونی می‌کنه ولی با متلک و نیش زبان می‌رنجونه",
        "توی قرآن یه جا خوندم که خدا «صمد» هست. این صمد دقیقاً یعنی چی تو زندگی ما؟",
        "تازگی‌ها صبح‌ها که بیدار می‌شم یا شب‌ها قبل خواب خیلی اضطراب و استرس دارم کتاب دعا می‌خوام",
        "چرا دانشمندان اسلامی توی مسائل شرعی و فقهی این‌قدر با هم اختلاف نظر دارن؟",
        "می‌خوام معنی سوره‌های قرآن رو آیه به آیه بخونم تفسیر خلاصه روان می‌خوام"
    ]

    print("\n🔍 بررسی امتیازهای شباهت برداری نورونی پس از اصلاح:")
    for q in test_queries:
        t_s0 = time.perf_counter()
        hits = await VectorService.search_semantic(query=q, limit=2)
        t_s = (time.perf_counter() - t_s0) * 1000
        print(f"\n❓ پرسش: «{q}»")
        if hits:
            top = hits[0]
            print(f"   ✨ رتبه ۱: [{top.get('bookTitle')}] فصل: {top.get('chapterTitle')} (اسکور: {top.get('score'):.4f} | {t_s:.1f}ms)")
            print(f"      متن: {top.get('text')[:120]}...")
        else:
            print("   ⚠️ نتیجه‌ای یافت نشد.")

        # Test Book Recommendation
        async with AsyncSessionLocal() as session:
            rec_s, rec_b = await RecommendationService.recommend_scholar_and_book(q, db=session)
            print(f"   📚 کتاب پیشنهادی: {rec_b.get('title') if rec_b else '---'}")
            print(f"   👤 ارجاع به عالم: {rec_s.get('name') if rec_s else '---'}")

if __name__ == "__main__":
    asyncio.run(main())
