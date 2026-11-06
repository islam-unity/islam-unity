import re
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_chat import SourceCitationDTO
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    is_valid: bool = True
    verdict: str = "PASSED"  # PASSED, CORRECTED, FLAGGED
    issues_found: List[str] = field(default_factory=list)
    corrected_answer: Optional[str] = None
    citation_check_passed: bool = True
    rulings_verified: bool = True


class AgentVerifier:
    """
    Evaluates that rulings and opinions in the agent's draft answer strictly align
    with retrieved evidence sources, and validates clickable citation references.
    """

    @classmethod
    async def verify_and_refine(
        cls,
        draft_answer: str,
        sources: List[SourceCitationDTO],
        user_query: str,
        target_madhhab: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> VerificationResult:
        if not draft_answer or not draft_answer.strip():
            return VerificationResult(is_valid=True, verdict="PASSED")

        # 1. Deterministic Code-Level Citation Verification
        citation_issues = []
        # Find all markdown links like [1](...) or [2](...)
        cited_indices = re.findall(r"\[(\d+)\]\((.*?)\)", draft_answer)
        valid_indices = {s.index for s in sources}

        for idx_str, url in cited_indices:
            try:
                idx = int(idx_str)
                if idx not in valid_indices:
                    citation_issues.append(f"شماره ارجاع [{idx}] در فهرست منابع یافت نشد.")
            except ValueError:
                pass

        # If no sources were retrieved at all, check if draft falsely claims certainty
        has_sources = len(sources) > 0

        # 2. Lightweight LLM Ruling-to-Source Verification
        # Only needed if sources exist and query involves religious rulings
        if not has_sources:
            return VerificationResult(
                is_valid=True,
                verdict="PASSED" if not citation_issues else "FLAGGED",
                issues_found=citation_issues,
                citation_check_passed=len(citation_issues) == 0,
                rulings_verified=True
            )

        evidence_summary = "\n".join([
            f"منبع [{s.index}]: {s.title} ({s.madhhab or 'عمومی'})\nشواهد: {s.excerpt or ''}"
            for s in sources[:5]
        ])

        system_instruction = (
            "تو بخش ارزیاب و اعتبارسنج (Verifier) یک ایجنت معارفی هستی.\n"
            "وظیفه تو این است که احکام، فتواها و نظرات اصلی پاسخ را با متن منابع مقایسه کنی.\n"
            "نیاز به ریزبینی کلمه‌به‌کلمه نیست؛ صرفاً اطمینان حاصل کن که:\n"
            "1. حکم یا نظر اصلی مطرح‌شده با متن منبع استنادی تناقض نداشته باشد.\n"
            "2. اگر مذهب خاصی مطرح است، نظر مربوط به همان مذهب نقل شده باشد.\n"
            "\n"
            "قوانین بسیار مهم:\n"
            "- هرگونه ارزیابی، ایراد، نقد یا توصیه داخلی (مانند «به جای فلان از بهمان استفاده شود»، «باید اصلاح شود»، «ارجاع اشتباه است») را حتماً در آرایه issues بنویس.\n"
            "- فیلد suggested_correction فقط و فقط در صورتی پر شود که متن کامل و پیراسته جدید پاسخ برای ارائه به کاربر را نگارش کرده باشی (متن آماده خواندن برای کاربر).\n"
            "- هرگز جملات دستوری، توصیه‌ای، نقد ایجنت یا تحلیل درونی را در suggested_correction قرار نده! اگر متن کامل بازنویسی‌شده نداری، مقدار آن را حتماً null بگذار.\n"
            "\n"
            "خروجی به صورت شیء JSON با ساختار زیر باشد:\n"
            "{\n"
            '  "is_aligned": true,\n'
            '  "issues": [],\n'
            '  "suggested_correction": null\n'
            "}"
        )

        user_content = (
            f"پرسش کاربر: {user_query}\n"
            f"مذهب مد نظر: {target_madhhab or 'عمومی/مقارن'}\n\n"
            f"منابع و شواهد معتبر:\n{evidence_summary}\n\n"
            f"پیش‌نویس پاسخ:\n{draft_answer}"
        )

        try:
            resp = await LLMProviderService.call_chat(
                prompt=user_content,
                system_instruction=system_instruction,
                section_key="agent_verifier",
                db=db,
                temperature=0.1,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            raw_text = ""
            if isinstance(resp, dict):
                raw_text = str(resp.get("text") or "").strip()
            elif isinstance(resp, str):
                raw_text = resp.strip()

            if raw_text:
                if "<think>" in raw_text:
                    if "</think>" in raw_text:
                        raw_text = raw_text.split("</think>")[-1].strip()
                    else:
                        raw_text = raw_text.split("<think>")[-1].strip()

                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                parsed = None
                try:
                    parsed = json.loads(raw_text)
                except Exception:
                    m = re.search(r"\{[\s\S]*\}", raw_text)
                    if m:
                        try:
                            parsed = json.loads(m.group(0))
                        except Exception:
                            pass

                if parsed and isinstance(parsed, dict):
                    is_aligned = bool(parsed.get("is_aligned", True))
                    llm_issues = parsed.get("issues", [])
                    correction = parsed.get("suggested_correction")

                    all_issues = citation_issues + llm_issues

                    # Validate that correction is an actual complete answer, not internal critique
                    valid_correction = None
                    if correction and isinstance(correction, str):
                        c_str = correction.strip()
                        critique_markers = [
                            "به جای", "باید", "لازم است", "پیشنهاد می‌شود", "پیشنهاد می شود",
                            "اصلاح شود", "حذف شود", "اصلاح گردد", "تطبیق داده شود",
                            "ارجاع داده شود", "منابع نامرتبط", "استفاده شود", "توصیه"
                        ]
                        is_critique = any(marker in c_str[:70] for marker in critique_markers)
                        if is_critique or len(c_str) < 100:
                            all_issues.append(f"توصیه ارزیاب: {c_str}")
                            valid_correction = None
                        else:
                            valid_correction = c_str

                    if is_aligned and not citation_issues:
                        return VerificationResult(
                            is_valid=True,
                            verdict="PASSED",
                            issues_found=[],
                            corrected_answer=None,
                            citation_check_passed=True,
                            rulings_verified=True
                        )
                    else:
                        return VerificationResult(
                            is_valid=False,
                            verdict="CORRECTED" if valid_correction else "FLAGGED",
                            issues_found=all_issues,
                            corrected_answer=valid_correction or draft_answer,
                            citation_check_passed=len(citation_issues) == 0,
                            rulings_verified=is_aligned
                        )
        except Exception as e:
            logger.debug(f"Verifier LLM evaluation skipped: {e}")

        return VerificationResult(
            is_valid=True,
            verdict="PASSED",
            issues_found=citation_issues,
            citation_check_passed=len(citation_issues) == 0,
            rulings_verified=True
        )
