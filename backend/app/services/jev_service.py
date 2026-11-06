import re
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class JevService:
    """
    TypeSafe AI Jev - System One Non-Autoregressive Decision Engine
    Performs fast, typed, calibrated decisions (Choice, Score, Noul) without generative token waste.
    Includes robust fallback for offline or unconfigured environments.
    """

    @classmethod
    async def select_chapter(
        cls,
        user_query: str,
        chapters: List[str],
        book_title: str = ""
    ) -> Optional[str]:
        """
        Uses Jev's 'choice' answer type to select the single most relevant chapter out of candidates.
        Latency: ~70-200ms.
        """
        if not chapters:
            return None
        if len(chapters) == 1:
            return chapters[0]

        from app.services.llm_provider_service import LLMProviderService
        jev_cfg = await LLMProviderService.get_section_config(None, "jev")
        jev_url = jev_cfg.get("base_url") or settings.JEV_BASE_URL or settings.JEV_API_URL
        jev_key = jev_cfg.get("api_key") or settings.JEV_API_KEY

        if jev_key and len(jev_key.strip()) > 5:
            try:
                choice_map = {f"ch_{i}": ch for i, ch in enumerate(chapters[:20])}
                payload = {
                    "model": jev_cfg.get("model_name") or settings.JEV_MODEL or "jev-latest",
                    "state": {
                        "user_question": user_query,
                        "book_title": book_title
                    },
                    "questions": {
                        "target_chapter": {
                            "type": "choice",
                            "choices": choice_map,
                            "criteria": {"rule": "کدام یک از فصول بالا مرتبط‌ترین مبحث را برای پاسخ به سوال کاربر دارد؟"}
                        }
                    }
                }
                async with httpx.AsyncClient(timeout=4.0, trust_env=False) as client:
                    resp = await client.post(
                        jev_url,
                        headers={
                            "Authorization": f"Bearer {jev_key}",
                            "Content-Type": "application/json"
                        },
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        ans = data.get("answers", {}).get("target_chapter", {})
                        chosen = ans.get("choice") or ans.get("value")
                        if chosen in choice_map:
                            return choice_map[chosen]
                        if chosen and chosen in chapters:
                            return chosen
            except Exception as e:
                logger.warning(f"Jev API call for chapter selection failed: {e}. Using fallback.")

        # Fallback chapter matcher
        return cls._fallback_select_chapter(user_query, chapters)

    @classmethod
    async def evaluate_sufficiency(
        cls,
        user_query: str,
        retrieved_evidence: str
    ) -> Dict[str, Any]:
        """
        Uses Jev's 'noul' (calibrated probability 0.0 - 1.0) and 'score' to check
        if the retrieved text sufficiently and helpfully answers the user query.
        """
        if not retrieved_evidence or len(retrieved_evidence.strip()) < 15:
            return {
                "is_sufficient": False,
                "confidence": 0.05,
                "score": 1,
                "reasoning": "متن بازیابی‌شده خالی یا بسیار کوتاه است."
            }

        from app.services.llm_provider_service import LLMProviderService
        jev_cfg = await LLMProviderService.get_section_config(None, "jev")
        jev_url = jev_cfg.get("base_url") or settings.JEV_BASE_URL or settings.JEV_API_URL
        jev_key = jev_cfg.get("api_key") or settings.JEV_API_KEY

        if jev_key and len(jev_key.strip()) > 5:
            try:
                payload = {
                    "model": jev_cfg.get("model_name") or settings.JEV_MODEL or "jev-latest",
                    "state": {
                        "question": user_query,
                        "retrieved_evidence": retrieved_evidence[:1500]
                    },
                    "questions": {
                        "is_sufficient": {
                            "type": "choice",
                            "choices": {"sufficient": "شواهد کافی و مستقیم است", "insufficient": "شواهد ناکافی یا نامرتبط است"},
                            "criteria": {
                                "sufficient": "شواهد به طور مستقیم، معتبر و کافی به سوال کاربر پاسخ می‌دهند و مرتبط با موضوع است",
                                "insufficient": "شواهد نامرتبط است، موضوع دیگری است یا به سوال پاسخ نمی‌دهد"
                            }
                        }
                    }
                }
                async with httpx.AsyncClient(timeout=4.0, trust_env=False) as client:
                    resp = await client.post(
                        jev_url,
                        headers={
                            "Authorization": f"Bearer {jev_key}",
                            "Content-Type": "application/json"
                        },
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        ans = data.get("answers", {}).get("is_sufficient", {})
                        choice = ans.get("choice")
                        conf = float(ans.get("confidence", 0.8))
                        is_suff = (choice == "sufficient")
                        return {
                            "is_sufficient": is_suff,
                            "confidence": conf,
                            "score": 9 if is_suff else 3,
                            "reasoning": "ارزیابی مستقیم توسط مدل تصمیم‌گیر TypeSafe JEV انجام شد."
                        }
            except Exception as e:
                logger.warning(f"Jev API call for sufficiency evaluation failed: {e}. Using fallback.")

        # Fallback sufficiency evaluation
        return cls._fallback_evaluate_sufficiency(user_query, retrieved_evidence)

    @classmethod
    def _fallback_select_chapter(cls, query: str, chapters: List[str]) -> str:
        """
        Fallback keyword and domain-aware chapter matcher.
        """
        q_tokens = set([w.strip() for w in query.replace("؟", "").split() if len(w.strip()) > 2])
        best_chapter = chapters[0]
        max_score = -1

        # Domain knowledge mappings
        fiqh_taharah_keywords = {"نجس", "متنجس", "آب", "میاه", "طهارت", "بول", "وضو", "غسل", "پاکی", "تطهیر"}
        fiqh_salat_keywords = {"نماز", "صلاة", "قبله", "سجده", "رکوع", "اذان", "اقامه"}
        fiqh_sawm_keywords = {"روزه", "صوم", "رمضان", "کفاره", "افطار", "سحری"}
        fiqh_zakat_keywords = {"زکات", "خمس", "صدقه", "مالیات"}
        ethics_keywords = {"صبر", "شکر", "توکل", "اخلاق", "ریا", "حسد", "ایمان"}

        for ch in chapters:
            ch_lower = ch.lower()
            score = 0
            for token in q_tokens:
                if token in ch_lower:
                    score += 3

            # Semantic domain heuristics
            if any(k in q_tokens for k in fiqh_taharah_keywords) and ("طهار" in ch_lower or "میاه" in ch_lower or "آب" in ch_lower):
                score += 5
            if any(k in q_tokens for k in fiqh_salat_keywords) and ("صلاة" in ch_lower or "نماز" in ch_lower):
                score += 5
            if any(k in q_tokens for k in fiqh_sawm_keywords) and ("صوم" in ch_lower or "روزه" in ch_lower):
                score += 5
            if any(k in q_tokens for k in ethics_keywords) and ("صبر" in ch_lower or "اخلاق" in ch_lower or "رقائق" in ch_lower):
                score += 5

            if score > max_score:
                max_score = score
                best_chapter = ch

        return best_chapter

    @classmethod
    def _fallback_evaluate_sufficiency(cls, query: str, evidence: str) -> Dict[str, Any]:
        """
        Cross-lingual sufficiency evaluator powered by CrossLingualService.
        """
        try:
            from app.services.cross_lingual_service import CrossLingualService
            coverage = CrossLingualService.calculate_crosslingual_coverage(query, evidence)
        except Exception:
            coverage = 0.5

        # Calibrated confidence calculation
        confidence = min(0.99, max(0.1, coverage * 0.92 + (0.08 if len(evidence) > 80 and coverage >= 0.3 else 0.0)))
        is_sufficient = confidence >= 0.50 and coverage >= 0.35

        return {
            "is_sufficient": is_sufficient,
            "confidence": round(confidence, 2),
            "score": int(round(confidence * 10)),
            "reasoning": f"تطابق کلیدواژه‌ای دوزبانه (عربی/فارسی) به میزان {int(coverage * 100)}% در متن شواهد."
        }

    @classmethod
    async def batch_rerank_chunks(
        cls,
        user_query: str,
        candidate_chunks: List[Dict[str, Any]],
        min_score: int = 6,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fast multi-score batch reranking for 10-20 chunk summaries in a single Jev call (~100-250ms).
        Assigns relevance score (1-10) to each candidate and returns top-k filtered by min_score.
        """
        if not candidate_chunks:
            return []
        if len(candidate_chunks) == 1:
            chunk = candidate_chunks[0].copy()
            chunk["jev_score"] = 8
            return [chunk]

        # Limit to top 20 candidates for latency safety
        eval_candidates = candidate_chunks[:20]

        from app.services.llm_provider_service import LLMProviderService
        jev_cfg = await LLMProviderService.get_section_config(None, "jev")
        jev_url = jev_cfg.get("base_url") or settings.JEV_BASE_URL or settings.JEV_API_URL
        jev_key = jev_cfg.get("api_key") or settings.JEV_API_KEY

        scored_candidates: List[Dict[str, Any]] = []

        if jev_key and len(jev_key.strip()) > 5:
            try:
                summaries_state = {}
                questions = {}
                for idx, c in enumerate(eval_candidates):
                    c_key = f"c_{idx}"
                    summary_text = (c.get("summary") or c.get("excerpt") or c.get("text") or "")[:200]
                    title_text = c.get("chapterTitle") or c.get("title") or c.get("bookTitle") or f"بخش {idx+1}"
                    summaries_state[c_key] = f"[{title_text}]: {summary_text}"
                    questions[f"{c_key}_score"] = {
                        "type": "score",
                        "min": 1,
                        "max": 10,
                        "instruction": f"میزان انطباق مفهومی متن {c_key} با پرسش کاربر چقدر است؟"
                    }

                payload = {
                    "state": {
                        "user_question": user_query,
                        "candidates": summaries_state
                    },
                    "questions": questions
                }

                async with httpx.AsyncClient(timeout=4.5) as client:
                    resp = await client.post(
                        jev_url,
                        headers={
                            "Authorization": f"Bearer {jev_key}",
                            "Content-Type": "application/json"
                        },
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answers = data.get("answers", {})
                        for idx, c in enumerate(eval_candidates):
                            c_copy = dict(c)
                            score_val = answers.get(f"c_{idx}_score", {}).get("value")
                            try:
                                c_copy["jev_score"] = int(score_val) if score_val is not None else 5
                            except (ValueError, TypeError):
                                c_copy["jev_score"] = 5
                            scored_candidates.append(c_copy)
            except Exception as e:
                logger.warning(f"Jev batch rerank call failed: {e}. Using fallback batch scoring.")
                scored_candidates = []

        if not scored_candidates:
            scored_candidates = cls._fallback_batch_rerank(user_query, eval_candidates)

        # Sort descending by Jev score
        sorted_by_score = sorted(scored_candidates, key=lambda x: x.get("jev_score", 0), reverse=True)

        # Filter by minimum score threshold
        passing = [c for c in sorted_by_score if c.get("jev_score", 0) >= min_score]
        if not passing and sorted_by_score:
            # Fallback: keep best candidates if they at least have score >= 4
            passing = [c for c in sorted_by_score if c.get("jev_score", 0) >= 4]

        return passing[:top_k]

    @classmethod
    def _fallback_batch_rerank(
        cls,
        user_query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fallback cross-lingual keyword and token-overlap scoring for batch candidates.
        """
        try:
            from app.services.cross_lingual_service import CrossLingualService
        except Exception:
            CrossLingualService = None

        results = []
        for c in candidates:
            c_copy = dict(c)
            text_target = f"{c.get('title', '')} {c.get('chapterTitle', '')} {c.get('summary', '')} {c.get('excerpt', '')}"
            if CrossLingualService:
                ratio = CrossLingualService.calculate_crosslingual_coverage(user_query, text_target)
            else:
                q_tokens = [w.strip() for w in user_query.replace("؟", "").split() if len(w.strip()) > 2]
                matches = sum(1 for t in q_tokens if t.lower() in text_target.lower())
                ratio = matches / len(q_tokens) if q_tokens else 0.5

            # Base score on token overlap ratio scaled 1-10
            base_score = int(round(ratio * 7)) + 2

            # Boost if vector search score was already high
            vec_score = c.get("score")
            if vec_score and isinstance(vec_score, (int, float)):
                if vec_score > 0.8:
                    base_score += 2
                elif vec_score > 0.6:
                    base_score += 1

            c_copy["jev_score"] = min(10, max(1, base_score))
            results.append(c_copy)

        return results

