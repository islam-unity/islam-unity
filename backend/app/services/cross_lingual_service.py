import re
import logging
from typing import List, Dict, Set, Optional

logger = logging.getLogger(__name__)


class CrossLingualService:
    """
    Cross-Lingual Arabic & Persian Bridge Service for Islamic RAG:
    - Unifies orthographic differences (Alef, Yeh, Kaf, Heh/Ta Marbuta, Tashkeel, Tanween, Tatweel).
    - Bridges linguistic divergence between user Persian queries and classical Arabic source books.
    - Generates multi-angle cross-lingual queries (Original, Classical Arabic Fiqh, Thematic Chapter, Lexical Lemmas).
    - Enables high-accuracy cross-lingual tokenization for vector embeddings and JEV decision scoring.
    """

    # Comprehensive Islamic and Fiqh semantic dictionary mapping Persian terms to Classical Arabic
    FIQH_FA_TO_AR_DICTIONARY: Dict[str, List[str]] = {
        "طهارت": ["طهارة", "تطهير", "نظافة", "طهورية"],
        "طهاره": ["طهارة", "تطهير", "نظافة"],
        "تطهیر": ["تطهير", "إزالة النجاسة"],
        "لغت": ["لغة", "في اللغة", "لغةً"],
        "لغوی": ["لغوي", "لغة"],
        "شرع": ["شرع", "شرعا", "شرعاً", "في الشرع", "اصطلاحا", "في الاصطلاح"],
        "شرعی": ["شرعي", "في الشرع", "أحكام شرعية"],
        "معناست": ["معنى", "تعريف", "حقيقة"],
        "معنا": ["معنى", "تعريف", "دلالة"],
        "معنی": ["معنى", "تعريف"],
        "چیست": ["ما هو", "تعريف", "معنى", "حقيقة"],
        "تعریف": ["تعريف", "معنى", "حد", "حقيقة"],
        "نماز": ["صلاة", "الصلاة", "أركان الصلاة", "شروط الصلاة"],
        "روزه": ["صوم", "الصيام", "أحكام الصيام"],
        "وضو": ["وضوء", "الوضوء", "فرائض الوضوء", "سنن الوضوء"],
        "غسل": ["غسل", "الاغتسال", "موجبات الغسل"],
        "پاکی": ["طهارة", "طاهر", "نظافة"],
        "پاک": ["طاهر", "طهارة", "طهور"],
        "نجاست": ["نجاسة", "الأعيان النجسة", "قذارة"],
        "نجس": ["نجس", "متنجس", "نجاسة"],
        "آب": ["ماء", "مياه", "طهورية الماء"],
        "آبها": ["مياه", "أقسام المياه"],
        "حکم": ["حكم", "أحكام", "مشروعية"],
        "احکام": ["أحكام", "فروع"],
        "شرط": ["شرط", "شروط"],
        "شرایط": ["شروط", "أركان"],
        "رکن": ["ركن", "أركان", "فرائض"],
        "ارکان": ["أركان", "فرائض"],
        "واجب": ["واجب", "فرض", "فرائض"],
        "واجبات": ["واجبات", "فرائض", "أركان"],
        "مستحب": ["مستحب", "سنة", "سنن", "مندوب"],
        "مستحبات": ["مستحبات", "سنن", "مندوبات"],
        "حرام": ["حرام", "محرمات", "معصية"],
        "مکروه": ["مكروه", "مكروهات"],
        "باطل": ["باطل", "مبطلات", "نواقض"],
        "مبطلات": ["مبطلات", "نواقض", "مفسدات"],
        "شک": ["شك", "سجود السهو"],
        "شکیات": ["شروط السهو", "أحكام الشك"],
        "خمس": ["خمس", "أموال الخمس"],
        "زکات": ["زكاة", "أهل الزكاة", "صدقة"],
        "حج": ["حج", "مناسك الحج", "عمرة"],
        "ازدواج": ["نكاح", "عقد النكاح", "زواج"],
        "نکاح": ["نكاح", "عقد النكاح"],
        "طلاق": ["طلاق", "أحكام الطلاق", "عدة"],
        "خرید و فروش": ["بيع", "بيوع", "معاملات"],
        "معامله": ["بيع", "معاملة", "عقد"],
        "سود": ["ربا", "مرابحة"],
        "قرض": ["قرض", "دين", "أحكام الدين"],
        "وصیت": ["وصية", "أحكام الوصية"],
        "ارث": ["ميراث", "فرائض", "تركة"],
        "کتاب": ["كتاب", "باب"],
        "فصل": ["فصل", "مبحث", "باب"],
        "حدیث": ["حديث", "رواية", "سنة", "خبر"],
        "روایت": ["رواية", "أثر", "خبر"],
        "پیامبر": ["النبي", "رسول الله", "المصطفى"],
        "امام": ["الإمام", "الأئمة"],
        "فتوا": ["فتوى", "حكم", "رأي"],
        "مذهب": ["مذهب", "فقهاء", "مذاهب"]
    }

    # Combined Arabic and Persian stopwords
    STOPWORDS: Set[str] = {
        # Persian
        "در", "به", "از", "که", "این", "آن", "با", "برای", "و", "یا", "است", "شد", "می", "هم", "تا", "بر",
        "چه", "چیست", "کدام", "چگونه", "چرا", "آیا", "درباره", "پیرامون", "معناست", "بود", "یک", "نیز", "چند",
        "بین", "همه", "خود", "وی", "ما", "شما", "ایشان", "آنها", "کرده", "شده", "باشد",
        # Arabic
        "في", "من", "إلى", "على", "عن", "أن", "إن", "ما", "هو", "هي", "لا", "كان", "قال", "ثم", "أو", "كل",
        "مع", "حيث", "بين", "إذا", "قد", "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "الذين", "له", "لها", "بها"
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalizes Arabic and Persian text to a unified orthographic representation:
        - Unifies Alef variants (آ, أ, إ, ٱ -> ا)
        - Unifies Yeh variants (ي, ى -> ی)
        - Unifies Kaf variants (ك -> ک)
        - Unifies Heh / Ta Marbuta (ة -> ه)
        - Removes Tashkeel (harakat), Tanween, and Tatweel (kashida)
        """
        if not text:
            return ""
        t = text.lower()
        t = re.sub(r"[آأإٱ]", "ا", t)
        t = t.replace("ي", "ی").replace("ى", "ی")
        t = t.replace("ك", "ک")
        t = t.replace("ة", "ه")
        t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)
        return t.strip()

    @classmethod
    def get_canonical_token(cls, token: str) -> str:
        """
        Strips prefixes and suffixes to find the root canonical form of a word.
        Handles Persian/Arabic cross-lingual variations like:
          - طهارت <-> طهاره
          - لغت <-> لغه
          - معناست <-> معنا
          - الطهارة <-> طهاره
        """
        t = cls.normalize_text(token)
        if not t:
            return ""

        # Remove Arabic definite article
        if t.startswith("ال") and len(t) > 3:
            t = t[2:]

        # Persian verbal/copula suffixes (e.g. معناست -> معنا)
        if t.endswith("ست") and len(t) > 4:
            t = t[:-2]

        # Normalize ending 'ت' vs 'ه' (e.g. طهارت -> طهاره, لغت -> لغه)
        if t.endswith("ت") and len(t) > 2:
            t = t[:-1] + "ه"

        # Persian plural suffixes
        if t.endswith("ها") and len(t) > 3:
            t = t[:-2]
        elif t.endswith("ان") and len(t) > 4:
            t = t[:-2]

        # Arabic dual/plural suffixes
        if (t.endswith("ین") or t.endswith("ون")) and len(t) > 4:
            t = t[:-2]
        elif t.endswith("ات") and len(t) > 4:
            t = t[:-2] + "ه"

        return t

    @classmethod
    def extract_keywords(cls, text: str) -> List[str]:
        """
        Extracts clean, non-stopword tokens from query or context text.
        """
        raw_words = re.findall(r"[\w\u0600-\u06FF]+", text)
        clean = []
        for w in raw_words:
            w_str = w.strip()
            if len(w_str) > 1 and w_str.lower() not in cls.STOPWORDS:
                clean.append(w_str)
        return clean

    @classmethod
    def to_classical_arabic_query(cls, query: str) -> str:
        """
        Synthesizes a high-precision Classical Arabic search formulation from a Persian or mixed query.
        Example:
          'طهارت در لغت و شرع به چه معناست؟' -> 'معنى الطهارة لغة وشرعا تعريف وحكم'
          'حکم نماز مسافر چیست؟' -> 'حكم صلاة المسافر في الشريعة'
        """
        norm_q = cls.normalize_text(query)
        words = cls.extract_keywords(query)
        arabic_terms: List[str] = []

        is_definition_query = any(w in norm_q for w in ["معناست", "معنا", "معنی", "چیست", "تعریف", "حقیقت", "لغت", "شرع"])
        is_ruling_query = any(w in norm_q for w in ["حکم", "شرایط", "واجب", "حرام", "باطل", "صحیح", "احکام"])

        for w in words:
            norm_w = cls.normalize_text(w)
            canonical = cls.get_canonical_token(w)

            # Check direct dictionary
            if w in cls.FIQH_FA_TO_AR_DICTIONARY:
                arabic_terms.append(cls.FIQH_FA_TO_AR_DICTIONARY[w][0])
            elif norm_w in cls.FIQH_FA_TO_AR_DICTIONARY:
                arabic_terms.append(cls.FIQH_FA_TO_AR_DICTIONARY[norm_w][0])
            elif canonical in cls.FIQH_FA_TO_AR_DICTIONARY:
                arabic_terms.append(cls.FIQH_FA_TO_AR_DICTIONARY[canonical][0])
            else:
                # Morphological fallback: Arabic orthography
                ar_fallback = norm_w
                if ar_fallback.endswith("ت") and len(ar_fallback) > 3:
                    ar_fallback = ar_fallback[:-1] + "ة"
                arabic_terms.append(ar_fallback)

        # Structure the Classical Arabic query based on intent
        if is_definition_query:
            if "تعريف" not in arabic_terms and "معنى" not in arabic_terms:
                arabic_terms.insert(0, "معنى")
            # Ensure 'لغة وشرعا' phrasing is preserved if present
            if any("لغ" in t for t in arabic_terms) and any("شرع" in t for t in arabic_terms):
                filtered = [t for t in arabic_terms if "لغ" not in t and "شرع" not in t and t not in ["معنى", "تعريف"]]
                return f"معنى {' '.join(filtered)} لغة وشرعا تعريف"

        if is_ruling_query and "حكم" not in arabic_terms and "أحكام" not in arabic_terms:
            arabic_terms.insert(0, "حكم")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for t in arabic_terms:
            if t not in seen and len(t) > 1:
                seen.add(t)
                deduped.append(t)

        return " ".join(deduped) if deduped else query

    @classmethod
    def generate_multi_angle_queries(
        cls,
        query: str,
        domain: str = "FIQH",
        category: str = "احکام شرعی و فقهی"
    ) -> List[str]:
        """
        Produces 3-4 distinct multi-lingual search queries:
          1. Angle 1 (Original Clean Query): User's natural query
          2. Angle 2 (Classical Arabic Formulation): Exact Arabic fiqh terminology matching source books
          3. Angle 3 (Thematic & Structural Heading Formulation): Core topic + chapter/book context
          4. Angle 4 (Cross-Lingual Combined Lexical Set): Distinct lemma tokens for lexical retrieval
        """
        clean_q = query.replace("؟", "").replace("?", "").strip()
        if not clean_q:
            return [query]

        # 1. Original Clean Query
        angle1_orig = clean_q

        # 2. Classical Arabic Source Formulation
        angle2_arabic = cls.to_classical_arabic_query(clean_q)

        # 3. Thematic / Chapter Concept Formulation
        topic_words = cls.extract_keywords(clean_q)
        core_topic = topic_words[0] if topic_words else "احکام"
        canonical_topic = cls.get_canonical_token(core_topic)

        # Find Arabic equivalent of the main topic
        ar_topic = cls.FIQH_FA_TO_AR_DICTIONARY.get(canonical_topic, [core_topic])[0]
        angle3_thematic = f"كتاب {ar_topic} أحكام {ar_topic} وشروطه في {category}"

        # 4. Cross-Lingual Combined Lemmatized Keywords
        all_lemmas = set()
        for w in topic_words:
            all_lemmas.add(cls.normalize_text(w))
            canon = cls.get_canonical_token(w)
            all_lemmas.add(canon)
            if canon in cls.FIQH_FA_TO_AR_DICTIONARY:
                for ar_equiv in cls.FIQH_FA_TO_AR_DICTIONARY[canon]:
                    all_lemmas.add(cls.normalize_text(ar_equiv))

        angle4_lemmas = " ".join(sorted(all_lemmas))

        # Return unique non-empty angles
        angles = []
        for ang in [angle1_orig, angle2_arabic, angle3_thematic, angle4_lemmas]:
            cleaned_ang = ang.strip()
            if cleaned_ang and cleaned_ang not in angles:
                angles.append(cleaned_ang)

        return angles

    @classmethod
    def calculate_crosslingual_coverage(cls, query: str, context_text: str) -> float:
        """
        Measures bidirectional keyword match ratio between query and context,
        prioritizing core topic nouns over generic terms (like 'تعریف' or 'معنی').
        """
        q_tokens = cls.extract_keywords(query)
        if not q_tokens:
            return 0.5

        norm_ctx = cls.normalize_text(context_text)
        ctx_tokens = set(cls.extract_keywords(context_text))
        ctx_canonicals = {cls.get_canonical_token(ct) for ct in ctx_tokens}

        GENERIC_WORDS = {"معنى", "تعريف", "حكم", "احكام", "شرط", "شروط", "لغه", "شرع", "سبب", "بيان", "فصل", "باب", "كتاب", "چیست", "معناست"}
        topic_tokens = [t for t in q_tokens if cls.get_canonical_token(t) not in GENERIC_WORDS]
        has_topic = len(topic_tokens) > 0
        topic_matched = False

        matched = 0
        for token in q_tokens:
            norm_t = cls.normalize_text(token)
            canon_t = cls.get_canonical_token(token)
            is_topic = canon_t not in GENERIC_WORDS

            is_match = False
            # Direct substring or exact token match
            if norm_t in norm_ctx or canon_t in ctx_canonicals:
                is_match = True
            # Dictionary-based cross-lingual match
            elif canon_t in cls.FIQH_FA_TO_AR_DICTIONARY and any(cls.normalize_text(s) in norm_ctx for s in cls.FIQH_FA_TO_AR_DICTIONARY[canon_t]):
                is_match = True
            # Morphological alternate match (ت <-> ه/ة)
            elif norm_t.endswith("ت") and (norm_t[:-1] + "ه") in norm_ctx:
                is_match = True
            elif norm_t.endswith("ه") and (norm_t[:-1] + "ت") in norm_ctx:
                is_match = True

            if is_match:
                matched += 1
                if is_topic:
                    topic_matched = True

        raw_cov = matched / len(q_tokens)

        # Severe penalty if the candidate completely misses the core topic of the query
        if has_topic and not topic_matched:
            return round(min(0.25, raw_cov * 0.35), 3)

        # Reward if both core topic and supporting concepts are matched
        if has_topic and topic_matched and matched >= 2:
            raw_cov = min(1.0, raw_cov + 0.1)

        return round(raw_cov, 3)

    @classmethod
    def get_crosslingual_vector_tokens(cls, text: str) -> List[str]:
        """
        Generates enriched cross-lingual token set for deterministic fallback embeddings:
        Injects both Persian and Arabic canonical equivalents into the hashing vocabulary
        so that Persian and Arabic queries and books map to close spatial vectors.
        """
        tokens = cls.extract_keywords(text)
        enriched: List[str] = []

        for t in tokens:
            canon = cls.get_canonical_token(t)
            enriched.append(canon)

            # Inject Arabic synonyms if Persian word
            if canon in cls.FIQH_FA_TO_AR_DICTIONARY:
                for ar_term in cls.FIQH_FA_TO_AR_DICTIONARY[canon]:
                    enriched.append(cls.get_canonical_token(ar_term))

        return enriched if enriched else ["معارف"]
