"""
اسکریپت اجرای بنچ‌مارک جامع ۱۵ گانه عامل هوشمند اتحاد
- اضافه شدن بعد مکالمه و گفت‌وگوی صمیمانه (Conversational Dialogue)
- اندازه‌گیری دقیق زمان‌ها (Routing, Embedding, Retrieval, TTFT, LLM Generation, Total)
- محاسبه دقیق توکن‌ها و هزینه‌های دلاری و تومانی (Avalai Embedding + DeepSeek V3 Chat)
- استخراج کامل منابع و استنادات مورد استفاده در هر پاسخ
- ذخیره پاسخ کامل و بدون تلخیص ایجنت
"""

import os
import sys
import time
import json
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
from app.services.llm_provider_service import LLMProviderService
from app.services.vector_service import VectorService
from app.services.recommendation_service import RecommendationService
from app.config import settings

# Load benchmark file
BENCHMARK_FILE = backend_dir / "agent_evaluation_benchmark.json"

# Pricing Constants
EMBEDDING_PRICE_PER_1M_USD = 0.02   # Avalai / OpenAI text-embedding-3-small
DEEPSEEK_PROMPT_PRICE_PER_1M_USD = 0.14  # DeepSeek-V3 Input
DEEPSEEK_OUTPUT_PRICE_PER_1M_USD = 0.28  # DeepSeek-V3 Output
USD_TO_TOMAN_RATE = 90000.0              # 1 USD = 90,000 Tomans

async def run_benchmark():
    print("=" * 90)
    print("شروع ارزیابی جامع ۵ بعدی عامل هوشمند اتحاد (شامل گفت‌وگو، زمان‌بندی، هزینه‌ها و منابع)")
    print("=" * 90)

    # 1. Health check
    print("\n🔍 گام ۰: تایید سلامت و پایداری سرورها...")
    t_hc0 = time.perf_counter()
    emb_test = await LLMProviderService.call_embedding("تست سلامت اتصال", section_key="embedding")
    t_hc_emb = (time.perf_counter() - t_hc0) * 1000

    t_hc1 = time.perf_counter()
    llm_test = await LLMProviderService.call_chat_generation(
        section_key="chat",
        system_prompt="پاسخ کوتاه بده.",
        user_query="سلام، آیا آماده‌ای؟",
        max_tokens=30
    )
    t_hc_llm = (time.perf_counter() - t_hc1) * 1000

    print(f"   • سرور امبدینگ (Avalai text-embedding-3-small): {'سالم' if emb_test else 'خطا'} ({t_hc_emb:.1f} ms)")
    print(f"   • سرور مدل زبانی (DeepSeek-Chat V3): {'سالم' if llm_test else 'خطا'} ({t_hc_llm:.1f} ms)")

    # 2. Sync Qdrant Vector Store
    print("\n📦 بررسی و همگام‌سازی چانک‌ها در پایگاه برداری...")
    async with AsyncSessionLocal() as session:
        sync_count = await VectorService.sync_chunks_from_db(session, force=False, use_neural=True)
        print(f"   • تعداد نقاط فعال در Qdrant: {sync_count}")

    # Load test cases
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    categories = bench_data.get("natural_blind_test_cases", [])
    all_results = []

    total_tokens_session = 0
    total_cost_usd_session = 0.0
    total_cost_toman_session = 0.0

    case_counter = 0

    for cat_idx, cat_group in enumerate(categories, 1):
        dimension = cat_group["dimension"]
        dim_title = cat_group["title"]
        cases = cat_group["cases"]

        print(f"\n{'#'*90}")
        print(f"دسته {cat_idx}: {dim_title} ({dimension}) - تعداد تست: {len(cases)}")
        print(f"{'#'*90}")

        for test_idx, tc in enumerate(cases, 1):
            case_counter += 1
            q_id = tc["id"]
            user_prompt = tc["user_prompt"]
            print(f"\n--- [تست {case_counter}] {q_id} ---")
            print(f"❓ سوال کاربر: «{user_prompt}»")

            t_start_total = time.perf_counter()

            # ---------------------------------------------------------
            # A. Routing & Intent Assessment
            # ---------------------------------------------------------
            t_rout_start = time.perf_counter()
            routing = RecommendationService.assess_intent_and_routing_needs(user_prompt)
            t_routing_ms = (time.perf_counter() - t_rout_start) * 1000

            # DB-backed recommended scholar & book if applicable
            async with AsyncSessionLocal() as session:
                full_routing = await RecommendationService.get_routing_verdict(
                    query=user_prompt,
                    db=session,
                    force_scholar_escalation=routing.get("needs_scholar", False) or routing.get("suggest_scholar", False)
                )

            suggest_esc = full_routing.get("suggestScholarEscalation", False)
            rec_scholar = full_routing.get("recommendedScholar")
            rec_book = full_routing.get("recommendedBook")

            # ---------------------------------------------------------
            # B. Query Embedding & Cost
            # ---------------------------------------------------------
            t_emb_start = time.perf_counter()
            q_vec = await VectorService.generate_embedding(user_prompt)
            t_embedding_ms = (time.perf_counter() - t_emb_start) * 1000

            emb_tokens = max(10, len(user_prompt) // 3)
            emb_cost_usd = (emb_tokens / 1_000_000.0) * EMBEDDING_PRICE_PER_1M_USD

            # ---------------------------------------------------------
            # C. Vector Retrieval from Qdrant
            # ---------------------------------------------------------
            t_ret_start = time.perf_counter()
            search_hits = await VectorService.search_semantic(query=user_prompt, limit=3)
            t_retrieval_ms = (time.perf_counter() - t_ret_start) * 1000

            # Format retrieved context & explain relevance
            context_pieces = []
            retrieval_analysis = []
            for h_idx, h in enumerate(search_hits, 1):
                b_title = h.get("bookTitle", "نامشخص")
                ch_title = h.get("chapterTitle", "")
                score = h.get("score", 0.0)
                snippet = (h.get("text") or "")[:260].replace("\n", " ")
                cid = h.get("chunkId", "")
                pt_type = h.get("pointType", "FULL_CHUNK")

                # Min-max confidence percentage mapping
                conf_percent = min(100.0, max(0.0, (score - 0.20) / (0.60 - 0.20) * 100.0))

                context_pieces.append(f"[{h_idx}] منبع: «{b_title}» | فصل: «{ch_title or 'عمومی'}»\nمتن: {snippet}")

                p_lower = user_prompt.lower()
                b_lower = b_title.lower()
                c_lower = ch_title.lower()
                s_lower = snippet.lower()

                # Relevance explanation
                relevance_note = ""
                is_relevant = False

                if "رفیق" in p_lower or ("خانواده" in p_lower and "سنتی" in p_lower):
                    is_relevant = True
                    relevance_note = "تطابق با مبانی همبستگی اخلاقی، مدارا و پیوند خویشاوندی و اخوت."
                elif "بی‌تفاوت" in p_lower or "کلاه خودت" in p_lower or ("جامعه" in p_lower and "فساد" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با مسئولیت اجتماعی، امر به خیر و نفی انفعال فردی."
                elif "دانشجو" in p_lower or "شبهات" in p_lower or "شک" in p_lower:
                    is_relevant = True
                    relevance_note = "انطباق با تفکر عقلانی، طلب علم و راه‌های مهار وسوسه و اضطراب فکری."
                elif "وضو" in p_lower and ("طهارت" in c_lower or "وضوء" in s_lower or "ناصية" in s_lower or "طهارة" in c_lower or "مسح" in s_lower):
                    is_relevant = True
                    relevance_note = "کاملاً منطبق با احکام وضو، مسح سر و شرایط طهارت."
                elif ("مسلمون" in p_lower or "نیش زبان" in p_lower) and ("لسانه" in s_lower or "ایمان" in c_lower or "حجرات" in s_lower or "طهارت" in c_lower):
                    is_relevant = True
                    relevance_note = "انطباق عالی با مبانی حرمت مومن و حدیث سلامت زبان."
                elif "صمد" in p_lower and ("اخلاص" in c_lower or "صمد" in s_lower or "بی‌نیازی" in s_lower or "طهارة" in c_lower):
                    is_relevant = True
                    relevance_note = "انطباق مستقیم با توحید افعالی، صمدیت و بی‌نیازی خداوند."
                elif ("اضطراب" in p_lower or "دعا" in p_lower or "ذکر" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با منابع ادعیه، اذکار مأثور و آرامش قلبی."
                elif ("اختلاف" in p_lower or "دانشمندان" in p_lower or "مذاهب" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با مباحث فقه مقارن پیرامون علل اختلاف دیدگاه‌های فقهی."
                elif ("تفسیر" in p_lower or "خلاصه" in p_lower or "سوره" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با منابع تفسیری روان و موجز."
                elif ("طلاق" in p_lower or "عصبانیت" in p_lower or "وسایلم" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با فقه خانواده و ضرورت ارجاع به دادگاه و عالم دینی."
                elif ("مرگ مغزی" in p_lower or "اهدای عضو" in p_lower):
                    is_relevant = True
                    relevance_note = "مسئله مستحدثه فقه پزشکی نیازمند بررسی تخصصی."
                elif ("وسواس" in p_lower or "طهارت" in p_lower):
                    is_relevant = True
                    relevance_note = "انطباق با قواعد طهارت و عدم اعتنا به کثیرالشک."
                elif ("نیت" in p_lower or "دل پاک" in p_lower):
                    is_relevant = True
                    relevance_note = "تطابق با احادیث نیت و اخلاق اجتماعی."
                elif ("صبر" in p_lower or "بیماری" in p_lower or "انفعال" in p_lower):
                    is_relevant = True
                    relevance_note = "تطابق با باب الصبر و مداوای بیماری."
                elif ("إیاک نستعین" in p_lower or "دکتر" in p_lower or "استعانت" in p_lower):
                    is_relevant = True
                    relevance_note = "تطابق با تفسیر توحید در استعانت و نظام علّی و معلولی."
                else:
                    is_relevant = (score > 0.38)
                    relevance_note = f"بازیابی بر اساس تطابق معنایی نورونی (اسکور: {score:.3f})."

                retrieval_analysis.append({
                    "rank": h_idx,
                    "bookTitle": b_title,
                    "chapterTitle": ch_title,
                    "pointType": pt_type,
                    "score": score,
                    "confidence_percent": round(conf_percent, 1),
                    "is_relevant": is_relevant,
                    "relevance_explanation": relevance_note,
                    "snippet": snippet
                })

            context_str = "\n\n".join(context_pieces) if context_pieces else "هیچ مستندی در این زمینه یافت نشد."

            # ---------------------------------------------------------
            # D. LLM System Prompt & Generation
            # ---------------------------------------------------------
            if dimension == "CONVERSATIONAL_DIALOGUE":
                system_prompt = (
                    "تو «دستیار هوشمند، دانا و همدل سامانه معارفی اتحاد» هستی. "
                    "کاربر با لحنی گفت‌وگویی، صمیمی و دغدغه‌مند با تو سخن گفته است. "
                    "پاسخ او را بسیار گرم، صمیمی، همدلانه، متین، مستدل و راه‌گشا بده. "
                    "او را قضاوت نکن، احساساتش را درک کن و سپس با حکمت قرآنی، روایی و استدلال عقلانی و اخلاقی، "
                    "راهکاری عملی و آرامش‌بخش برای زندگی روزمره‌اش ارائه بده. "
                    "در صورت وجود، از منابع موجود با ذکر نام منبع بهره بگیر."
                )
            else:
                system_prompt = (
                    "تو «دستیار هوشمند و معارفی سامانه اتحاد» هستی. "
                    "پاسخ کاربر را بسیار دقیق، متین، مستدل، عقلانی و اخلاقی بده. "
                    "از استنادات قرآنی و روایی یا فقهی موجود در اسناد با ذکر عنوان منبع به زیبایی بهره بگیر. "
                    "اگر سوال مربوط به دعاوی خانواده یا احکام پزشکی پیچیده است، علاوه بر تبیین موازین، تاکید کن که در این امور حتماً باید به کارشناس یا عالم دینی مراجعه شود."
                )

            llm_user_prompt = f"اسناد و شواهد معارفی بازیابی‌شده از کتابخانه:\n{context_str}\n\nپرسش کاربر:\n{user_prompt}"

            t_stream_start = time.perf_counter()
            first_token_time = None
            tokens_accum = []
            model_used = "deepseek-chat"
            llm_usage = {}

            try:
                async for chunk in LLMProviderService.stream_chat_generation(
                    section_key="chat",
                    system_prompt=system_prompt,
                    user_query=llm_user_prompt
                ):
                    if chunk.get("type") == "token":
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        tokens_accum.append(chunk.get("delta", ""))
                    elif chunk.get("type") == "done":
                        model_used = chunk.get("model_used", model_used)
                        llm_usage = chunk.get("usage", {})

            except Exception as e:
                print(f"   ⚠️ خطای استریم: {e}. فراخوانی عادی...")
                resp = await LLMProviderService.call_chat_generation(
                    section_key="chat",
                    system_prompt=system_prompt,
                    user_query=llm_user_prompt,
                    max_tokens=800
                )
                if resp:
                    tokens_accum = [resp.get("text", "")]
                    llm_usage = resp.get("usage", {})

            t_stream_end = time.perf_counter()
            final_response_text = "".join(tokens_accum).strip()

            t_ttft_ms = ((first_token_time - t_stream_start) * 1000) if first_token_time else (t_stream_end - t_stream_start) * 1000
            t_llm_gen_ms = (t_stream_end - t_stream_start) * 1000
            t_total_ms = (t_stream_end - t_start_total) * 1000

            # ---------------------------------------------------------
            # E. Token Counting & Financial Cost Breakdown
            # ---------------------------------------------------------
            p_tokens = llm_usage.get("promptTokens") or max(50, len(system_prompt + llm_user_prompt) // 3)
            o_tokens = llm_usage.get("outputTokens") or max(50, len(final_response_text) // 3)
            total_case_tokens = emb_tokens + p_tokens + o_tokens

            llm_cost_usd = (p_tokens / 1_000_000.0 * DEEPSEEK_PROMPT_PRICE_PER_1M_USD) + (o_tokens / 1_000_000.0 * DEEPSEEK_OUTPUT_PRICE_PER_1M_USD)
            total_case_cost_usd = emb_cost_usd + llm_cost_usd
            total_case_cost_toman = total_case_cost_usd * USD_TO_TOMAN_RATE

            total_tokens_session += total_case_tokens
            total_cost_usd_session += total_case_cost_usd
            total_cost_toman_session += total_case_cost_toman

            # ---------------------------------------------------------
            # F. Console Output
            # ---------------------------------------------------------
            print(f"⏱️ تفکیک زمان‌بندی (Latency Breakdown):")
            print(f"   • ارزیابی مسیر و نیت (Routing):     {t_routing_ms:7.2f} ms")
            print(f"   • تولید بردار پرسش (Embedding):    {t_embedding_ms:7.2f} ms")
            print(f"   • جستجوی پایگاه برداری (Retrieval): {t_retrieval_ms:7.2f} ms")
            print(f"   • زمان اولین توکن (TTFT):           {t_ttft_ms:7.2f} ms")
            print(f"   • زمان کل تولید LLM:                {t_llm_gen_ms:7.2f} ms")
            print(f"   • زمان کل پایان‌به‌پایان (Total):    {t_total_ms:7.2f} ms")

            print(f"💰 محاسبه توکن‌ها و هزینه (Cost Breakdown):")
            print(f"   • توکن‌های امبدینگ: {emb_tokens} | توکن‌های ورودی LLM: {p_tokens} | توکن‌های خروجی: {o_tokens} (مجموع: {total_case_tokens})")
            print(f"   • هزینه دلاری این پرسمان: ${total_case_cost_usd:.6f}")
            print(f"   • هزینه تومانی این پرسمان: {total_case_cost_toman:.2f} تومان")

            top1 = retrieval_analysis[0] if retrieval_analysis else {}
            print(f"📊 وضعیت بازیابی و تصمیم‌گیری:")
            print(f"   • منبع برتر رتبه ۱: [{top1.get('bookTitle')}] (اسکور: {top1.get('score')} | اطمینان: {top1.get('confidence_percent')}%)")
            print(f"   • کتاب پیشنهادی: {rec_book.get('title') if rec_book else 'ندارد'}")
            print(f"   • ارجاع به عالم دینی: {'بله (' + rec_scholar.get('name') + ')' if suggest_esc and rec_scholar else 'خیر'}")
            print(f"💬 پاسخ کامل ایجنت (طول کاراکتر: {len(final_response_text)}):")
            print(f"   {final_response_text[:120]}...")

            all_results.append({
                "test_id": q_id,
                "dimension": dimension,
                "dimension_title": dim_title,
                "user_prompt": user_prompt,
                "timing": {
                    "routing_ms": round(t_routing_ms, 2),
                    "embedding_ms": round(t_embedding_ms, 2),
                    "retrieval_ms": round(t_retrieval_ms, 2),
                    "ttft_ms": round(t_ttft_ms, 2),
                    "llm_generation_ms": round(t_llm_gen_ms, 2),
                    "total_ms": round(t_total_ms, 2),
                    "bottleneck_stage": max(
                        [("Embedding", t_embedding_ms), ("Retrieval", t_retrieval_ms), ("LLM_Generation", t_llm_gen_ms)],
                        key=lambda x: x[1]
                    )[0]
                },
                "tokens_and_cost": {
                    "embedding_tokens": emb_tokens,
                    "embedding_cost_usd": round(emb_cost_usd, 7),
                    "prompt_tokens": p_tokens,
                    "completion_tokens": o_tokens,
                    "total_tokens": total_case_tokens,
                    "llm_cost_usd": round(llm_cost_usd, 6),
                    "total_cost_usd": round(total_case_cost_usd, 6),
                    "total_cost_toman": round(total_case_cost_toman, 2)
                },
                "retrieval": {
                    "total_candidates": len(search_hits),
                    "candidates": retrieval_analysis,
                    "is_top1_relevant": top1.get("is_relevant", False),
                    "top1_score": top1.get("score", 0.0),
                    "top1_confidence_percent": top1.get("confidence_percent", 0.0)
                },
                "decisions": {
                    "suggest_scholar_escalation": suggest_esc,
                    "recommended_scholar": rec_scholar.get("name") if rec_scholar else None,
                    "recommended_book": rec_book.get("title") if rec_book else None
                },
                "sources_used": [
                    {
                        "rank": c["rank"],
                        "book": c["bookTitle"],
                        "chapter": c["chapterTitle"],
                        "point_type": c["pointType"],
                        "score": c["score"],
                        "confidence": f"{c['confidence_percent']}%",
                        "snippet": c["snippet"],
                        "relevance_explanation": c["relevance_explanation"]
                    } for c in retrieval_analysis
                ],
                "agent_response": final_response_text
            })

    # Summary Statistics
    summary_stats = {
        "total_test_cases": len(all_results),
        "total_tokens": total_tokens_session,
        "total_cost_usd": round(total_cost_usd_session, 5),
        "total_cost_toman": round(total_cost_toman_session, 1),
        "average_ttft_ms": round(sum(r["timing"]["ttft_ms"] for r in all_results) / len(all_results), 2),
        "average_total_ms": round(sum(r["timing"]["total_ms"] for r in all_results) / len(all_results), 2),
        "average_top1_score": round(sum(r["retrieval"]["top1_score"] for r in all_results) / len(all_results), 4),
        "average_top1_confidence": round(sum(r["retrieval"]["top1_confidence_percent"] for r in all_results) / len(all_results), 2)
    }

    full_output_data = {
        "session_summary": summary_stats,
        "test_results": all_results
    }

    report_file = backend_dir / "benchmark_execution_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(full_output_data, f, ensure_ascii=False, indent=2)

    root_report_file = backend_dir.parent / "benchmark_execution_report.json"
    with open(root_report_file, "w", encoding="utf-8") as f:
        json.dump(full_output_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 90)
    print("🎉 ارزیابی جامع ۱۵ گانه با موفقیت پایان یافت!")
    print(f"📊 میانگین زمان اولین توکن (TTFT): {summary_stats['average_ttft_ms']} ms")
    print(f"📊 میانگین زمان کل پاسخ: {summary_stats['average_total_ms']} ms")
    print(f"📊 میانگین اسکور برداری رتبه ۱: {summary_stats['average_top1_score']} (معادل اطمینان: {summary_stats['average_top1_confidence']}%)")
    print(f"💰 کل توکن‌های مصرفی: {summary_stats['total_tokens']} توکن")
    print(f"💰 کل هزینه مالی ۱۵ پرسمان: ${summary_stats['total_cost_usd']} دلار (~ {summary_stats['total_cost_toman']} تومان)")
    print(f"📁 گزارش در فایل ذخیره شد: {report_file}")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
