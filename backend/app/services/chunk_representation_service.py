import re
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChunkRepresentationService:
    """
    Handles intelligent chunking (Human Delimiters + Semantic Paragraphs)
    and generates Enriched Representations (Summary for Jev, Multi-Angle Hypothetical Questions for Qdrant, Concepts).
    """

    HUMAN_DELIMITERS = [
        re.compile(r"\n?\s*---\s*chunk\s*---\s*\n?", re.IGNORECASE),
        re.compile(r"\n?\s*\[\[\s*chunk\s*\]\]\s*\n?", re.IGNORECASE),
        re.compile(r"\n?\s*<!--\s*chunk\s*-->\s*\n?", re.IGNORECASE),
        re.compile(r"\n(?=###\s+)", re.UNICODE)
    ]

    @classmethod
    def segment_text(
        cls,
        text: str,
        arabic_text: Optional[str] = None,
        content_type: str = "GENERAL",
        context_header: str = "",
        max_words_per_chunk: int = 700,
        overlap_words: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Splits text into coherent chunks based on hierarchy:
        1. If content_type is 'HADITH', the entire text is kept as a single unified chunk.
        2. If human delimiters exist (---chunk---, [[chunk]], etc.), split precisely on markers.
        3. Fallback: Intelligent semantic paragraph splitting with sliding overlap and context header injection.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            clean_text = (arabic_text or "").strip()
        if not clean_text:
            return []

        is_arabic_source = bool(arabic_text and (arabic_text.strip() == clean_text or not (text or "").strip()))

        # 1. Check for human delimiters (Highest Priority - human intervention overrides defaults)
        for delim_pattern in cls.HUMAN_DELIMITERS:
            parts = [p.strip() for p in delim_pattern.split(clean_text) if p.strip()]
            if len(parts) > 1:
                chunks = []
                for idx, part in enumerate(parts):
                    chunks.append({
                        "text": part,
                        "textArabic": part if is_arabic_source else (arabic_text if idx == 0 else ""),
                        "delimiter_type": "HUMAN_MARKER"
                    })
                return chunks

        # 2. If no human delimiter, Hadiths are preserved as unified chunks
        if content_type.upper() == "HADITH":
            return [{
                "text": clean_text,
                "textArabic": clean_text if is_arabic_source else (arabic_text or ""),
                "delimiter_type": "HADITH_WHOLE"
            }]

        # 3. Check length: If within word cap, return single chunk
        words = clean_text.split()
        if len(words) <= max_words_per_chunk:
            return [{
                "text": clean_text,
                "textArabic": clean_text if is_arabic_source else (arabic_text or ""),
                "delimiter_type": "SINGLE"
            }]

        # 4. Fallback: Semantic paragraph chunking with overlap
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in clean_text.split("\n") if p.strip()]

        chunks = []
        current_paragraphs: List[str] = []
        current_word_count = 0
        overlap_prefix = ""

        for p in paragraphs:
            p_words = len(p.split())
            if current_word_count + p_words > max_words_per_chunk and current_paragraphs:
                # Flush current chunk
                body = "\n\n".join(current_paragraphs)
                if overlap_prefix:
                    body = f"{overlap_prefix}\n\n{body}"

                chunks.append({
                    "text": body,
                    "textArabic": body if is_arabic_source else (arabic_text if len(chunks) == 0 else ""),
                    "delimiter_type": "SEMANTIC_PARAGRAPH"
                })

                # Calculate overlap prefix from end of current chunk
                last_words = body.split()
                if len(last_words) > overlap_words:
                    overlap_prefix = "... " + " ".join(last_words[-overlap_words:])
                else:
                    overlap_prefix = ""

                current_paragraphs = [p]
                current_word_count = p_words
            else:
                current_paragraphs.append(p)
                current_word_count += p_words

        if current_paragraphs:
            body = "\n\n".join(current_paragraphs)
            if overlap_prefix:
                body = f"{overlap_prefix}\n\n{body}"

            chunks.append({
                "text": body,
                "textArabic": body if is_arabic_source else (arabic_text if len(chunks) == 0 else ""),
                "delimiter_type": "SEMANTIC_PARAGRAPH"
            })

        return chunks

    @classmethod
    async def generate_representation(
        cls,
        text: str,
        arabic_text: Optional[str] = None,
        context_header: str = "",
        content_type: str = "GENERAL",
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Uses LLM (or robust heuristic fallback) to extract:
        - summary: 30-50 words maximum for Jev batch ranking
        - hypothetical_questions: 3-5 multi-angle synthetic queries (practical, conceptual, narrative)
        - core_concepts: key conceptual keywords
        - domain_insights: practical rulings, morals or takeaways
        """
        from app.services.llm_provider_service import LLMProviderService

        prompt = f"""You are an expert multilingual knowledge indexing and semantic representation engine.
Analyze the provided source text chunk and extract a high-density, structured semantic representation for semantic search and retrieval.

SOURCE CONTEXT: {context_header or 'Scholarly Reference'}
CONTENT CATEGORY: {content_type}

SOURCE CHUNK TEXT (Persian / Arabic / English):
\"\"\"{text[:2800]}\"\"\"
{f'AUTHENTIC / VOCALIZED SOURCE: {arabic_text[:1000]}' if arabic_text and arabic_text.strip() != text.strip() else ''}

EXTRACTION SPECIFICATIONS:
1. "summary": A dense, objective, standalone summary (30 to 50 words) capturing the primary proposition, ruling, finding, or argument directly. Do NOT include meta-phrases such as "This text discusses", "در این متن آمده است", or book/chapter titles.
2. "hypothetical_questions": Exactly 3 to 4 realistic, distinct search questions that a researcher or user would ask, for which THIS SPECIFIC CHUNK provides the definitive answer. Do NOT use boilerplate templates:
   - Question 1 (Direct / Practical / Factual): Targets the concrete ruling, immediate answer, or specific fact established in the text.
   - Question 2 (Conceptual / Analytical / Rationale): Inquires about the underlying principle, definition, mechanism, or cause explained in the text.
   - Question 3 (Evidential / Source / Citation): Focuses on the textual proof, argument, narration, or scholarly reasoning cited in the text.
3. "core_concepts": 3 to 6 essential normalized key terms, technical domain concepts, or named entities occurring in the chunk.
4. "domain_insights": 2 to 3 substantive, high-value conclusions, actionable takeaways, legal rulings, or ethical principles directly deduced from the chunk.

LANGUAGE GUIDELINES:
- For Persian or Arabic texts, formulate questions and summaries in Persian for optimal regional accessibility, while preserving authentic Arabic technical terms and lemmas in `core_concepts`.
- For English texts, formulate the questions and summaries in English, including key Persian/Arabic equivalents in `core_concepts` if applicable.
- The output must be directly searchable by researchers in Persian, Arabic, or English.

OUTPUT FORMAT:
Return strictly a valid JSON object matching this schema (no markdown formatting outside the JSON, no extra explanation):
CRITICAL OUTPUT REQUIREMENT:
You must output strictly a raw, parseable JSON object matching this schema. Do NOT output any internal monologue, reasoning, thinking process, markdown commentary, or introductory text outside the JSON.

OUTPUT FORMAT:
{{
  "summary": "...",
  "hypothetical_questions": ["...", "...", "..."],
  "core_concepts": ["...", "..."],
  "domain_insights": ["...", "..."]
}}"""

        error_detail = None
        try:
            # 1. Prefer dedicated chunk representation section (NVIDIA NIM for background/offline tasks)
            cfg = await LLMProviderService.get_section_config(db, "chunk_representation")
            target_section = "chunk_representation"
            has_key = cfg.get("api_key") and len(cfg["api_key"].strip()) > 5

            # 2. Fallback to library AI section (DeepSeek) if chunk_representation key is absent
            if not has_key:
                cfg = await LLMProviderService.get_section_config(db, "library")
                target_section = "library"
                has_key = cfg.get("api_key") and len(cfg["api_key"].strip()) > 5

            if not has_key:
                error_detail = "کلید API برای پردازش چانک‌ها (chunk_representation / library) در تنظیمات یا متغیرهای محیطی ثبت نشده است."
                logger.warning(error_detail)
            else:
                resp = await LLMProviderService.call_chat(
                    prompt=prompt,
                    system_instruction="You are an expert multilingual knowledge indexing and semantic representation engine. Respond strictly in valid JSON. Do not output any conversational or reasoning text.",
                    section_key=target_section,
                    db=db,
                    max_tokens=4000,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                raw_text = ""
                if isinstance(resp, dict):
                    raw_text = str(resp.get("text", "")).strip()
                elif isinstance(resp, str):
                    raw_text = resp.strip()

                # If all Nvidia models in chunk_representation failed, fall back to DeepSeek (library section)
                if not raw_text and target_section == "chunk_representation":
                    logger.info("Nvidia chunk representation models exhausted. Falling back to DeepSeek (library)...")
                    lib_cfg = await LLMProviderService.get_section_config(db, "library")
                    if lib_cfg.get("api_key") and len(lib_cfg["api_key"].strip()) > 5:
                        lib_resp = await LLMProviderService.call_chat(
                            prompt=prompt,
                            system_instruction="You are an expert multilingual knowledge indexing and semantic representation engine. Respond strictly in valid JSON. Do not output any conversational or reasoning text.",
                            section_key="library",
                            db=db,
                            max_tokens=4000,
                            temperature=0.1,
                            response_format={"type": "json_object"}
                        )
                        if isinstance(lib_resp, dict):
                            raw_text = str(lib_resp.get("text", "")).strip()
                        elif isinstance(lib_resp, str):
                            raw_text = lib_resp.strip()

                if not raw_text:
                    error_detail = "پاسخ دریافتی از مدل‌های هوش مصنوعی خالی بود (احتمال خطای شبکه یا پایان سقف توکن‌ها)."
                else:
                    parsed = cls._parse_and_repair_json(raw_text)

                    if parsed and (parsed.get("summary") or parsed.get("hypothetical_questions")):
                        raw_summary = str(parsed.get("summary", "")).strip()
                        if not raw_summary:
                            raw_summary = cls._summarize_sentences(text, max_words=45)

                        raw_questions = parsed.get("hypothetical_questions", [])
                        valid_questions = [
                            str(q).strip() for q in raw_questions
                            if str(q).strip() and not str(q).startswith("<") and len(str(q).strip()) > 8
                        ]
                        if not valid_questions:
                            valid_questions = cls._generate_heuristic_questions(text, context_header, content_type)

                        raw_concepts = [
                            str(c).strip() for c in parsed.get("core_concepts", [])
                            if str(c).strip() and len(str(c).strip()) > 1
                        ]
                        if not raw_concepts:
                            raw_concepts = cls._extract_heuristic_concepts(text, arabic_text)

                        raw_insights = [
                            str(i).strip() for i in parsed.get("domain_insights", [])
                            if str(i).strip() and len(str(i).strip()) > 5
                        ]
                        if not raw_insights:
                            raw_insights = cls._extract_heuristic_insights(text, content_type)

                        return {
                            "summary": raw_summary,
                            "hypothetical_questions": valid_questions[:4],
                            "core_concepts": raw_concepts[:6],
                            "domain_insights": raw_insights[:3],
                            "is_ai_generated": True,
                            "llm_error": None
                        }
                    else:
                        error_detail = f"مدل پاسخ داد اما خروجی آن به درستی در قالب JSON استخراج نشد: {raw_text[:120]}..."
        except Exception as e:
            error_detail = f"خطا در ارتباط با ارائه‌دهنده مدل هوش مصنوعی: {str(e)}"
            logger.warning(f"LLM representation extraction failed: {e}. Using deterministic fallback.")

        # High-quality Deterministic Fallback Representation with captured connection error
        return cls._generate_fallback_representation(
            text=text,
            arabic_text=arabic_text,
            context_header=context_header,
            content_type=content_type,
            error_message=error_detail
        )

    @classmethod
    def _parse_and_repair_json(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Robustly parses JSON responses from LLMs, stripping reasoning/think tags,
        markdown fences, and handling slightly truncated JSON strings gracefully.
        """
        if not raw_text or not raw_text.strip():
            return None

        text = raw_text.strip()

        # 1. Strip reasoning / think tags if present (e.g. DeepSeek-R1)
        if "<think>" in text:
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            else:
                text = text.split("<think>")[-1].strip()

        # 2. Strip markdown codeblocks
        cleaned = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.rstrip("`").strip()

        # 3. Direct JSON load attempt
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and ("summary" in data or "hypothetical_questions" in data):
                return data
        except Exception:
            pass

        # 4. Search for outermost matching { ... }
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and ("summary" in data or "hypothetical_questions" in data):
                    return data
            except Exception:
                pass

        # 5. Robust regex-based recovery for truncated or partially-formed JSON
        recovered: Dict[str, Any] = {}

        # Extract "summary" (handles unclosed strings gracefully)
        sum_match = re.search(r'"summary"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', cleaned)
        if not sum_match:
            sum_match = re.search(r'"summary"\s*:\s*"([^"\n\r]*)', cleaned)
        if sum_match:
            val = sum_match.group(1).replace(r'\"', '"').strip()
            if len(val) > 10:
                recovered["summary"] = val

        # Extract "hypothetical_questions"
        q_section = re.search(r'"hypothetical_questions"\s*:\s*\[([\s\S]*?)(\]|\Z)', cleaned)
        if q_section:
            qs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', q_section.group(1))
            valid_qs = [q.replace(r'\"', '"').strip() for q in qs if len(q.strip()) > 8 and not q.startswith("<")]
            if valid_qs:
                recovered["hypothetical_questions"] = valid_qs

        # Extract "core_concepts"
        c_section = re.search(r'"core_concepts"\s*:\s*\[([\s\S]*?)(\]|\Z)', cleaned)
        if c_section:
            cs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', c_section.group(1))
            valid_cs = [c.replace(r'\"', '"').strip() for c in cs if c.strip() and len(c.strip()) > 1]
            if valid_cs:
                recovered["core_concepts"] = valid_cs

        # Extract "domain_insights"
        i_section = re.search(r'"domain_insights"\s*:\s*\[([\s\S]*?)(\]|\Z)', cleaned)
        if i_section:
            ins = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', i_section.group(1))
            valid_ins = [i.replace(r'\"', '"').strip() for i in ins if i.strip() and len(i.strip()) > 5]
            if valid_ins:
                recovered["domain_insights"] = valid_ins

        if "summary" in recovered or "hypothetical_questions" in recovered:
            return recovered

        return None

    @classmethod
    def _generate_fallback_representation(
        cls,
        text: str,
        arabic_text: Optional[str],
        context_header: str,
        content_type: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic heuristic extraction for offline or unconfigured environments.
        Supports Persian, Arabic, and English with extensive stopword filtering and robust phrase synthesis.
        """
        clean = text.replace("\n", " ").strip()
        sentences = [s.strip() for s in re.split(r"[.!?؟]\s+", clean) if len(s.strip()) > 15]

        # 1. Summary: First 1-2 key sentences
        summary = " ".join(sentences[:2]) if sentences else clean[:180]
        words = summary.split()
        if len(words) > 45:
            summary = " ".join(words[:45]) + "..."

        # 2. Comprehensive Multilingual Stopwords (Arabic, Persian, English)
        stopwords = {
            # Persian
            "است", "بود", "شد", "شدند", "که", "از", "به", "در", "با", "برای", "این", "آن", "یک", "تا", "بر", "یا", "هم", "نیز",
            "چون", "اگر", "اما", "ولی", "لیکن", "پس", "چرا", "چگونه", "چه", "کدام", "آیا", "همه", "هیچ", "هر", "بین", "میان",
            "روی", "زیر", "پشت", "نزد", "پیش", "دیگر", "بلکه", "تنها", "فقط", "همچنین", "بنابراین", "کرده", "می‌شود", "می‌باشد",
            "دارد", "دارند", "کنند", "کند", "شود", "شوند", "شده", "باشند", "باشد",
            # Arabic Pronouns, Prepositions, Relatives, Particles
            "من", "على", "في", "إلى", "عن", "أن", "إن", "ما", "هو", "هي", "هم", "هن", "لا", "كان", "كانت", "يكون", "تكون",
            "قال", "قالت", "ثم", "أو", "أم", "كل", "مع", "حيث", "حيثما", "بين", "نحو", "دون", "قبل", "بعد", "فوق", "تحت",
            "التي", "الذي", "الذين", "اللاتي", "اللواتي", "اللذان", "اللتان", "التی", "الذی", "الذین", "اللاتی", "اللواتی",
            "ذلك", "تلك", "هذا", "هذه", "هؤلاء", "أولئك", "ذلک", "تلک", "لأن", "لان", "إذ", "إذا", "اذ", "اذا",
            "كأن", "لكن", "ليت", "لعل", "حتى", "ليس", "صار", "أصبح", "عنه", "عنها", "منه", "منها", "فيه", "فيها", "به", "بها",
            "له", "لها", "عليه", "عليها", "إليه", "إليها", "فإن", "وإن", "فقد", "وقد", "أما", "إما", "بل", "غير", "سوى", "فقط",
            "أيضا", "أيضاً", "كذلك", "هنالك", "هنا", "البصري", "البصری", "فقال", "فقالوا", "وقيل", "قيل", "بما", "عما", "مما",
            # English
            "the", "and", "is", "are", "was", "were", "in", "on", "at", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "of", "off", "over",
            "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "can", "will", "just", "should", "now", "which", "that", "this", "these", "those"
        }

        # Tokenize and strictly clean punctuation
        raw_tokens = re.findall(r"[\w\u0600-\u06FF]{3,}", clean)
        cleaned_tokens = []
        for t in raw_tokens:
            w = t.strip("،.,;:!?؟«»()[]{}—_\"' ")
            if len(w) >= 3 and w.lower() not in stopwords and not w.isdigit():
                cleaned_tokens.append(w)

        freq = {}
        for t in cleaned_tokens:
            freq[t] = freq.get(t, 0) + 1
        sorted_tokens = sorted(freq.keys(), key=lambda k: freq[k], reverse=True)
        top_concepts = sorted_tokens[:4] if sorted_tokens else [context_header.split(" - ")[-1] if context_header else "مبانی منبع"]

        topic_label = top_concepts[0] if top_concepts else "مفاهیم کلیدی"

        # 3. Multi-angle 3 synthetic questions (grammatically sound and non-overfitted)
        q1 = f"مفاهیم و تبیین اصلی پیرامون {topic_label}"
        q2 = f"نکات کلیدی و شواهد مطرح‌شده در خصوص {', '.join(top_concepts[:2])}"
        q3 = f"شواهد، استنادات و تحلیل‌های مرتبط با {topic_label}"

        insights = [f"آموزه و گزاره کلیدی در خصوص {topic_label}"]
        if content_type.upper() == "FIQH":
            insights.append("رعایت شرایط، احکام و استنادات مطرح‌شده در متن منبع")
        elif content_type.upper() in ("HADITH", "TAFSIR"):
            insights.append("دلالت‌های روایی و ارشادات مستند به منبع")
        else:
            insights.append("نکات تحلیلی و مبانی مفهومی تبیین‌شده در این بخش")

        return {
            "summary": summary,
            "hypothetical_questions": [q1, q2, q3],
            "core_concepts": top_concepts,
            "domain_insights": insights,
            "is_ai_generated": False,
            "llm_error": error_message or "عدم برقراری ارتباط با مدل هوش مصنوعی (استفاده از الگوریتم پشتیبان)"
        }
