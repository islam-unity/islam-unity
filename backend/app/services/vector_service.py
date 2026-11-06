import math
import hashlib
import logging
from typing import List, Dict, Any, Optional
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue, MatchText, MatchAny
)
from app.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """
    Manages vector embeddings and semantic search via Qdrant.
    Supports Google Gemini 'text-embedding-004' with deterministic fallback.
    """
    _client: Optional[QdrantClient] = None
    VECTOR_DIM: int = 768

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._client is None:
            # Try connecting to remote Qdrant server first
            try:
                if settings.QDRANT_HOST and not settings.QDRANT_HOST.startswith(":") and not settings.QDRANT_USE_MEMORY_FALLBACK:
                    cls._client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                        timeout=5.0
                    )
                    # Check health
                    cls._client.get_collections()
                    logger.info("Connected to remote Qdrant server.")
                else:
                    raise ConnectionError("Using in-memory Qdrant instance.")
            except Exception as e:
                logger.info(f"Using local in-memory Qdrant client (Fallback): {e}")
                cls._client = QdrantClient(":memory:")

            # Ensure collection exists
            cls._ensure_collection(cls._client, settings.QDRANT_COLLECTION)

        return cls._client

    @classmethod
    def _ensure_collection(cls, client: QdrantClient, collection_name: str):
        try:
            collections = [c.name for c in client.get_collections().collections]
            if collection_name not in collections:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=cls.VECTOR_DIM,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection '{collection_name}'.")
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    @classmethod
    async def generate_embedding(cls, text: str) -> List[float]:
        """
        Generates 768-dim vector embedding using configured section model & base URL (Gemini or OpenAI-compatible),
        or deterministic semantic hashing fallback.
        """
        try:
            from app.services.llm_provider_service import LLMProviderService
            emb = await LLMProviderService.call_embedding(text, section_key="embedding")
            if emb and len(emb) == cls.VECTOR_DIM:
                return emb
            elif emb and len(emb) > 0:
                if len(emb) > cls.VECTOR_DIM:
                    return emb[:cls.VECTOR_DIM]
                else:
                    return emb + [0.0] * (cls.VECTOR_DIM - len(emb))
        except Exception as e:
            logger.warning(f"Embedding generation via LLMProviderService failed: {e}. Falling back to deterministic vector.")

        # High-quality deterministic normalized pseudo-semantic vector
        return cls._generate_fallback_vector(text)

    @classmethod
    async def generate_embeddings_batch(cls, texts: List[str]) -> List[List[float]]:
        """
        Generates 768-dim vector embeddings for a list of texts in batch using configured LLM provider,
        falling back to deterministic semantic hashing for any text that fails or is empty.
        """
        if not texts:
            return []

        results: List[List[float]] = []
        try:
            from app.services.llm_provider_service import LLMProviderService
            raw_embs = await LLMProviderService.call_embeddings_batch(texts, section_key="embedding")
            if raw_embs and len(raw_embs) == len(texts):
                for idx, emb in enumerate(raw_embs):
                    if emb and len(emb) == cls.VECTOR_DIM:
                        results.append(emb)
                    elif emb and len(emb) > 0:
                        if len(emb) > cls.VECTOR_DIM:
                            results.append(emb[:cls.VECTOR_DIM])
                        else:
                            results.append(emb + [0.0] * (cls.VECTOR_DIM - len(emb)))
                    else:
                        results.append(cls._generate_fallback_vector(texts[idx]))
                return results
        except Exception as e:
            logger.warning(f"Batch embedding generation failed: {e}. Falling back to deterministic vectors.")

        # Complete fallback
        return [cls._generate_fallback_vector(t) for t in texts]

    @classmethod
    def _generate_fallback_vector(cls, text: str) -> List[float]:
        """
        Deterministic pseudo-semantic vector using cross-lingual token hashing and L2 normalization.
        Ensures high vector similarity across Arabic and Persian equivalent vocabularies.
        """
        dim = cls.VECTOR_DIM
        vector = [0.0] * dim
        try:
            from app.services.cross_lingual_service import CrossLingualService
            words = CrossLingualService.get_crosslingual_vector_tokens(text)
        except Exception:
            words = text.lower().split()
        if not words:
            words = ["empty"]

        for idx, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            pos = h % dim
            sign = 1.0 if ((h >> 4) % 2 == 0) else -1.0
            weight = 1.0 / (1.0 + math.log(idx + 1))
            vector[pos] += sign * weight

        # L2 Normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    @classmethod
    async def upsert_knowledge_chunk(
        cls,
        chunk_id: str,
        text: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Embeds and stores a knowledge chunk into Qdrant.
        """
        client = cls.get_client()
        vector = await cls.generate_embedding(text)
        point = PointStruct(
            id=abs(hash(chunk_id)) % (2**63 - 1),
            vector=vector,
            payload={
                "chunk_id": chunk_id,
                **payload
            }
        )
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[point]
        )
        return True

    @classmethod
    async def search_semantic(
        cls,
        query: str,
        limit: int = 5,
        madhhab: Optional[str] = None,
        major_topic: Optional[str] = None,
        category: Optional[str] = None,
        book_id: Optional[str] = None,
        book_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches Qdrant with cosine similarity and hierarchical metadata filtering.
        """
        client = cls.get_client()
        query_vector = await cls.generate_embedding(query)

        # Build hierarchical filter conditions
        must_conditions = []
        if madhhab:
            must_conditions.append(FieldCondition(key="madhhab", match=MatchValue(value=madhhab)))
        if major_topic:
            must_conditions.append(FieldCondition(key="majorTopic", match=MatchText(text=major_topic)))
        if category:
            must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        if book_ids and len(book_ids) > 0:
            if len(book_ids) == 1:
                must_conditions.append(FieldCondition(key="bookId", match=MatchValue(value=book_ids[0])))
            else:
                must_conditions.append(FieldCondition(key="bookId", match=MatchAny(any=book_ids)))
        elif book_id:
            must_conditions.append(FieldCondition(key="bookId", match=MatchValue(value=book_id)))

        query_filter = Filter(must=must_conditions) if must_conditions else None

        try:
            if hasattr(client, "query_points"):
                response = client.query_points(
                    collection_name=settings.QDRANT_COLLECTION,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit
                )
                hits = response.points
            else:
                hits = client.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=limit
                )
        except Exception as e:
            logger.warning(f"Qdrant search error: {e}")
            return []

        results = []
        seen_keys = set()
        for hit in hits:
            cid = hit.payload.get("chunk_id") or hit.payload.get("bookId")
            if not cid or cid in seen_keys:
                continue
            seen_keys.add(cid)
            results.append({
                "chunkId": cid,
                "score": round(hit.score, 4),
                "bookId": hit.payload.get("bookId"),
                "bookTitle": hit.payload.get("bookTitle", "منبع معارفی"),
                "author": hit.payload.get("author", ""),
                "chapterTitle": hit.payload.get("chapter", "") or hit.payload.get("chapterTitle", ""),
                "subchapterTitle": hit.payload.get("subchapter", ""),
                "madhhab": hit.payload.get("madhhab"),
                "topics": hit.payload.get("topics", []),
                "tags": hit.payload.get("tags", []),
                "pointType": hit.payload.get("point_type", "FULL_CHUNK"),
                "text": hit.payload.get("text") or hit.payload.get("summary") or hit.payload.get("indexed_text", ""),
                "textArabic": hit.payload.get("textArabic", ""),
                "pageNumber": hit.payload.get("pageNumber"),
                "payload": hit.payload
            })

        return results

    @classmethod
    async def sync_chunks_from_db(cls, db: Any, force: bool = False, use_neural: bool = True) -> int:
        """
        Synchronizes all KnowledgeChunk records from SQL database into Qdrant.
        When use_neural is True (default), generates 768-dim neural embeddings in batches
        via the configured embedding provider (Avalai text-embedding-3-small) to ensure
        high-precision cosine similarity across both Arabic and Persian queries.
        """
        client = cls.get_client()
        try:
            if not force:
                count_info = client.count(collection_name=settings.QDRANT_COLLECTION)
                if count_info.count > 0:
                    return count_info.count
            else:
                try:
                    client.delete_collection(collection_name=settings.QDRANT_COLLECTION)
                except Exception:
                    pass
                cls._ensure_collection(client, settings.QDRANT_COLLECTION)
        except Exception as e:
            logger.warning(f"Error checking Qdrant point count: {e}")

        from sqlalchemy import select
        from app.db.models import KnowledgeChunk, Book
        stmt = select(KnowledgeChunk)
        res = await db.execute(stmt)
        chunks = res.scalars().all()
        if not chunks:
            return 0

        books_res = await db.execute(select(Book))
        books = books_res.scalars().all()
        book_titles = {b.id: b.title for b in books}

        pending_items: List[Dict[str, Any]] = []

        # 1. Prepare BOOK_SHOWCASE points
        for b in books:
            topics_str = " ".join(b.topics or []) if isinstance(b.topics, list) else str(b.topics or "")
            tags_str = " ".join(b.tags or []) if isinstance(b.tags, list) else str(b.tags or "")
            book_corpus = f"{b.title} {b.author} {b.description or ''} {topics_str} {tags_str}".strip()
            if book_corpus:
                b_pid = int(hashlib.md5(f"book_showcase_{b.id}".encode("utf-8")).hexdigest()[:15], 16)
                pending_items.append({
                    "id": b_pid,
                    "text": book_corpus,
                    "payload": {
                        "bookId": b.id,
                        "bookTitle": b.title,
                        "author": b.author,
                        "coverUrl": b.cover_url,
                        "categoryId": b.category_id,
                        "topics": b.topics or [],
                        "tags": b.tags or [],
                        "description": b.description or "",
                        "text": b.description or b.title,
                        "point_type": "BOOK_SHOWCASE"
                    }
                })

        # 2. Prepare Chunks, Hypothetical Questions, and Core Concepts
        for ch in chunks:
            comb_text = f"{ch.full_text or ''} {ch.text_arabic or ''} {ch.summary or ''}".strip()
            if not comb_text:
                continue

            b_title = book_titles.get(ch.book_id, "منبع معارفی")
            p_id = abs(hash(ch.id)) % (2**63 - 1)

            pending_items.append({
                "id": p_id,
                "text": comb_text,
                "payload": {
                    "chunk_id": ch.id,
                    "bookId": ch.book_id,
                    "chapterId": ch.chapter_id,
                    "bookTitle": b_title,
                    "text": ch.full_text or "",
                    "textArabic": ch.text_arabic or "",
                    "summary": ch.summary or "",
                    "point_type": "FULL_CHUNK"
                }
            })

            # Multi-angle points from hypothetical questions
            if ch.hypothetical_questions and isinstance(ch.hypothetical_questions, list):
                for q_i, q_t in enumerate(ch.hypothetical_questions):
                    q_str = str(q_t).strip()
                    if q_str:
                        sub_id = int(hashlib.md5(f"{ch.id}_q_{q_i}".encode("utf-8")).hexdigest()[:15], 16)
                        pending_items.append({
                            "id": sub_id,
                            "text": q_str,
                            "payload": {
                                "chunk_id": ch.id,
                                "bookId": ch.book_id,
                                "chapterId": ch.chapter_id,
                                "bookTitle": b_title,
                                "text": ch.full_text or ch.summary or "",
                                "textArabic": ch.text_arabic or "",
                                "summary": ch.summary or "",
                                "point_type": "HYPOTHETICAL_QUESTION",
                                "indexed_text": q_str
                            }
                        })

            # Multi-angle points from core concepts
            if ch.core_concepts and isinstance(ch.core_concepts, list):
                c_str = " ، ".join([str(c) for c in ch.core_concepts if str(c).strip()])
                if c_str:
                    sub_id = int(hashlib.md5(f"{ch.id}_concepts".encode("utf-8")).hexdigest()[:15], 16)
                    pending_items.append({
                        "id": sub_id,
                        "text": c_str,
                        "payload": {
                            "chunk_id": ch.id,
                            "bookId": ch.book_id,
                            "chapterId": ch.chapter_id,
                            "bookTitle": b_title,
                            "text": ch.full_text or ch.summary or "",
                            "textArabic": ch.text_arabic or "",
                            "summary": ch.summary or "",
                            "point_type": "CORE_CONCEPTS",
                            "indexed_text": c_str
                        }
                    })

        # 3. Batch Embed using Neural Model (Avalai) or deterministic fallback
        points: List[PointStruct] = []
        batch_size = 25

        logger.info(f"Starting neural synchronization of {len(pending_items)} vector points into Qdrant...")

        for i in range(0, len(pending_items), batch_size):
            batch = pending_items[i : i + batch_size]
            batch_texts = [item["text"] for item in batch]

            vectors = []
            if use_neural:
                try:
                    vectors = await cls.generate_embeddings_batch(batch_texts)
                except Exception as e:
                    logger.warning(f"Batch neural embedding failed for batch {i//batch_size}: {e}")
                    vectors = []

            # Ensure all items get a valid vector
            for item_idx, item in enumerate(batch):
                vec = None
                if vectors and item_idx < len(vectors) and vectors[item_idx] and len(vectors[item_idx]) == cls.VECTOR_DIM:
                    vec = vectors[item_idx]
                else:
                    vec = cls._generate_fallback_vector(item["text"])

                points.append(PointStruct(
                    id=item["id"],
                    vector=vec,
                    payload=item["payload"]
                ))

        if points:
            for i in range(0, len(points), 100):
                sub_pts = points[i : i + 100]
                client.upsert(collection_name=settings.QDRANT_COLLECTION, points=sub_pts)
            logger.info(f"Successfully auto-synchronized {len(points)} neural vector points into Qdrant collection '{settings.QDRANT_COLLECTION}'.")

        return len(points)

    @classmethod
    async def upsert_chunk_representations(
        cls,
        chunk_id: str,
        representation: Dict[str, Any],
        base_payload: Dict[str, Any]
    ) -> bool:
        """
        Multi-Vector Indexing:
        Indexes each synthetic hypothetical question and core concepts as distinct vector points
        in Qdrant, all referencing the parent chunk_id and carrying the compact summary.
        """
        client = cls.get_client()
        points: List[PointStruct] = []
        questions = representation.get("hypothetical_questions", [])
        concepts = representation.get("core_concepts", [])
        summary = representation.get("summary", "")

        # 1. Index each hypothetical question
        for idx, q_text in enumerate(questions):
            q_clean = str(q_text).strip()
            if not q_clean:
                continue
            vec = await cls.generate_embedding(q_clean)
            p_id = int(hashlib.md5(f"{chunk_id}_q_{idx}".encode("utf-8")).hexdigest()[:15], 16)
            points.append(PointStruct(
                id=p_id,
                vector=vec,
                payload={
                    **base_payload,
                    "chunk_id": chunk_id,
                    "point_type": "HYPOTHETICAL_QUESTION",
                    "indexed_text": q_clean,
                    "summary": summary
                }
            ))

        # 2. Index core concepts as an aggregated vector point
        if concepts:
            concepts_text = " ، ".join([str(c).strip() for c in concepts if str(c).strip()])
            if concepts_text:
                vec = await cls.generate_embedding(concepts_text)
                p_id = int(hashlib.md5(f"{chunk_id}_concepts".encode("utf-8")).hexdigest()[:15], 16)
                points.append(PointStruct(
                    id=p_id,
                    vector=vec,
                    payload={
                        **base_payload,
                        "chunk_id": chunk_id,
                        "point_type": "CORE_CONCEPTS",
                        "indexed_text": concepts_text,
                        "summary": summary
                    }
                ))

        if points:
            client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points
            )
            return True
        return False

    @classmethod
    async def upsert_batch_chunks(
        cls,
        batch_items: List[Dict[str, Any]]
    ) -> int:
        """
        Multi-Vector Batch Indexing:
        Indexes an entire batch of chunks into Qdrant in a single bulk request:
        1. Standard point for the full chunk text
        2. Representation points for each hypothetical question
        3. Representation point for core concepts
        """
        if not batch_items:
            return 0

        client = cls.get_client()

        embedding_requests: List[str] = []
        builder_callbacks = []
        ready_points: List[PointStruct] = []

        for item in batch_items:
            chunk_id = item["chunk_id"]
            combined_text = item.get("combined_text", "")
            repr_data = item.get("repr_data", {})
            base_payload = item.get("payload", {})
            questions = repr_data.get("hypothetical_questions", [])
            concepts = repr_data.get("core_concepts", [])
            summary = repr_data.get("summary", "")
            pre_vecs = item.get("precomputed_vectors") or base_payload.get("vectors")

            # Check for precomputed vectors to completely bypass API calls
            if pre_vecs and isinstance(pre_vecs, dict):
                main_v = pre_vecs.get("main_vector") or pre_vecs.get("vector")
                if main_v and combined_text:
                    ready_points.append(PointStruct(
                        id=abs(hash(chunk_id)) % (2**63 - 1),
                        vector=main_v,
                        payload={"chunk_id": chunk_id, **base_payload}
                    ))
                q_vecs = pre_vecs.get("question_vectors") or pre_vecs.get("questions_vectors") or []
                for q_idx, q_text in enumerate(questions):
                    q_clean = str(q_text).strip()
                    if not q_clean:
                        continue
                    if q_idx < len(q_vecs) and q_vecs[q_idx]:
                        p_id = int(hashlib.md5(f"{chunk_id}_q_{q_idx}".encode("utf-8")).hexdigest()[:15], 16)
                        ready_points.append(PointStruct(
                            id=p_id,
                            vector=q_vecs[q_idx],
                            payload={
                                **base_payload,
                                "chunk_id": chunk_id,
                                "point_type": "HYPOTHETICAL_QUESTION",
                                "indexed_text": q_clean,
                                "summary": summary
                            }
                        ))
                conc_v = pre_vecs.get("concepts_vector")
                if conc_v and concepts:
                    concepts_text = " ، ".join([str(c).strip() for c in concepts if str(c).strip()])
                    if concepts_text:
                        p_id = int(hashlib.md5(f"{chunk_id}_concepts".encode("utf-8")).hexdigest()[:15], 16)
                        ready_points.append(PointStruct(
                            id=p_id,
                            vector=conc_v,
                            payload={
                                **base_payload,
                                "chunk_id": chunk_id,
                                "point_type": "CORE_CONCEPTS",
                                "indexed_text": concepts_text,
                                "summary": summary
                            }
                        ))
                continue

            # 1. Main chunk text point
            if combined_text:
                embedding_requests.append(combined_text)
                def make_main_point(vec, c_id=chunk_id, pl=base_payload):
                    return PointStruct(
                        id=abs(hash(c_id)) % (2**63 - 1),
                        vector=vec,
                        payload={"chunk_id": c_id, **pl}
                    )
                builder_callbacks.append(make_main_point)

            # 2. Hypothetical question points
            for q_idx, q_text in enumerate(questions):
                q_clean = str(q_text).strip()
                if not q_clean:
                    continue
                embedding_requests.append(q_clean)
                def make_q_point(vec, c_id=chunk_id, q_i=q_idx, q_c=q_clean, s=summary, pl=base_payload):
                    p_id = int(hashlib.md5(f"{c_id}_q_{q_i}".encode("utf-8")).hexdigest()[:15], 16)
                    return PointStruct(
                        id=p_id,
                        vector=vec,
                        payload={
                            **pl,
                            "chunk_id": c_id,
                            "point_type": "HYPOTHETICAL_QUESTION",
                            "indexed_text": q_c,
                            "summary": s
                        }
                    )
                builder_callbacks.append(make_q_point)

            # 3. Core concepts point
            if concepts:
                concepts_text = " ، ".join([str(c).strip() for c in concepts if str(c).strip()])
                if concepts_text:
                    embedding_requests.append(concepts_text)
                    def make_c_point(vec, c_id=chunk_id, c_t=concepts_text, s=summary, pl=base_payload):
                        p_id = int(hashlib.md5(f"{c_id}_concepts".encode("utf-8")).hexdigest()[:15], 16)
                        return PointStruct(
                            id=p_id,
                            vector=vec,
                            payload={
                                **pl,
                                "chunk_id": c_id,
                                "point_type": "CORE_CONCEPTS",
                                "indexed_text": c_t,
                                "summary": s
                            }
                        )
                    builder_callbacks.append(make_c_point)

        points: List[PointStruct] = list(ready_points)
        if embedding_requests:
            # Batch compute all embeddings in a single operation
            vectors = await cls.generate_embeddings_batch(embedding_requests)
            for i, cb in enumerate(builder_callbacks):
                points.append(cb(vectors[i]))

        # Bulk upsert into Qdrant
        if points:
            client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points
            )

        return len(points)

    @classmethod
    async def search_by_representations(
        cls,
        query: str,
        limit_chunks: int = 15,
        madhhab: Optional[str] = None,
        major_topic: Optional[str] = None,
        category: Optional[str] = None,
        book_id: Optional[str] = None,
        book_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches Qdrant against multi-vector representations (questions & concepts),
        groups/deduplicates by parent chunk_id, and returns top unique chunk representations.
        """
        client = cls.get_client()
        query_vector = await cls.generate_embedding(query)

        must_conditions = []
        if madhhab:
            must_conditions.append(FieldCondition(key="madhhab", match=MatchValue(value=madhhab)))
        if major_topic:
            must_conditions.append(FieldCondition(key="majorTopic", match=MatchText(text=major_topic)))
        if category:
            must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        if book_ids and len(book_ids) > 0:
            if len(book_ids) == 1:
                must_conditions.append(FieldCondition(key="bookId", match=MatchValue(value=book_ids[0])))
            else:
                must_conditions.append(FieldCondition(key="bookId", match=MatchAny(any=book_ids)))
        elif book_id:
            must_conditions.append(FieldCondition(key="bookId", match=MatchValue(value=book_id)))

        query_filter = Filter(must=must_conditions) if must_conditions else None

        fetch_limit = min(limit_chunks * 3, 60)
        try:
            if hasattr(client, "query_points"):
                response = client.query_points(
                    collection_name=settings.QDRANT_COLLECTION,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=fetch_limit
                )
                hits = response.points
            else:
                hits = client.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=fetch_limit
                )
        except Exception as e:
            logger.warning(f"Qdrant representation search error: {e}")
            return []

        # Deduplicate by parent chunk_id, preserving highest score
        chunk_map: Dict[str, Dict[str, Any]] = {}
        for hit in hits:
            cid = hit.payload.get("chunk_id")
            if not cid:
                continue

            score = round(hit.score, 4)
            if cid not in chunk_map or score > chunk_map[cid]["score"]:
                chunk_map[cid] = {
                    "chunkId": cid,
                    "score": score,
                    "matchedText": hit.payload.get("indexed_text", ""),
                    "pointType": hit.payload.get("point_type", "UNKNOWN"),
                    "summary": hit.payload.get("summary", ""),
                    "bookId": hit.payload.get("bookId"),
                    "bookTitle": hit.payload.get("bookTitle", "منبع معارفی"),
                    "chapterTitle": hit.payload.get("chapter", ""),
                    "subchapterTitle": hit.payload.get("subchapter", ""),
                    "madhhab": hit.payload.get("madhhab"),
                    "pageNumber": hit.payload.get("pageNumber")
                }

        # Sort deduplicated chunks by score descending
        sorted_chunks = sorted(chunk_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_chunks[:limit_chunks]

