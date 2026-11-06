import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import or_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings

from app.core.response import success_response
from app.db.models import (
    LibraryCategory, LibraryPoster, Book, BookChapter, KnowledgeChunk, ReadingProgress, RAGEvaluationReport,
    BookSubmissionRequest
)
from app.db.session import get_db
from app.api.v1.admin.common import paginate
from app.services.library_service import LibraryService
from app.services.rag_evaluator_service import RAGEvaluatorService
from app.services.vector_service import VectorService

router = APIRouter()


class BenchmarkRequest(BaseModel):
    bookId: Optional[str] = None
    customQueries: Optional[List[str]] = None
    limitQueries: Optional[int] = 15


class TestQueryRequest(BaseModel):
    query: str
    bookId: Optional[str] = None


class CreateCategoryRequest(BaseModel):
    id: Optional[str] = None
    title: str
    iconName: Optional[str] = "menu_book"
    icon_name: Optional[str] = None
    orderIndex: Optional[int] = 0
    order_index: Optional[int] = None
    parentId: Optional[str] = None
    parent_id: Optional[str] = None


class CreatePosterRequest(BaseModel):
    id: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    imageUrl: Optional[str] = None
    image_url: Optional[str] = None
    targetBookId: Optional[str] = None
    target_book_id: Optional[str] = None
    orderIndex: Optional[int] = 0
    order_index: Optional[int] = None


class CreateBookRequest(BaseModel):
    id: Optional[str] = None
    title: str
    author: str
    translator: Optional[str] = None
    publisher: Optional[str] = None
    publicationYear: Optional[str] = None
    publication_year: Optional[str] = None
    coverUrl: Optional[str] = None
    cover_url: Optional[str] = None
    categoryId: Optional[str] = None
    category_id: Optional[str] = None
    isFeatured: Optional[bool] = False
    is_featured: Optional[bool] = False
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    language: Optional[str] = "fa"
    pageCount: Optional[int] = 100
    page_count: Optional[int] = None
    rating: Optional[float] = 4.8


def serialize_poster(poster: LibraryPoster) -> Dict[str, Any]:
    return {
        "id": poster.id,
        "title": poster.title,
        "subtitle": poster.subtitle,
        "imageUrl": poster.image_url,
        "image_url": poster.image_url,
        "targetBookId": poster.target_book_id,
        "target_book_id": poster.target_book_id,
        "orderIndex": poster.order_index,
        "order_index": poster.order_index
    }



def serialize_category(cat: LibraryCategory) -> Dict[str, Any]:
    return {
        "id": cat.id,
        "title": cat.title,
        "iconName": cat.icon_name,
        "icon_name": cat.icon_name,
        "orderIndex": cat.order_index,
        "order_index": cat.order_index,
        "parentId": getattr(cat, "parent_id", None),
        "parent_id": getattr(cat, "parent_id", None)
    }


def serialize_book(book: Book) -> Dict[str, Any]:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "translator": book.translator,
        "publisher": book.publisher,
        "publicationYear": book.publication_year,
        "publication_year": book.publication_year,
        "coverUrl": book.cover_url,
        "cover_url": book.cover_url,
        "categoryId": book.category_id,
        "category_id": book.category_id,
        "isFeatured": book.is_featured,
        "is_featured": book.is_featured,
        "tags": book.tags or [],
        "description": book.description,
        "language": book.language,
        "pageCount": book.page_count,
        "page_count": book.page_count,
        "rating": book.rating
    }


def serialize_chapter(chapter: BookChapter) -> Dict[str, Any]:
    return {
        "id": chapter.id,
        "bookId": chapter.book_id,
        "book_id": chapter.book_id,
        "chapterNumber": chapter.chapter_number,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "readingTimeMinutes": chapter.reading_time_minutes,
        "reading_time_minutes": chapter.reading_time_minutes,
        "content": chapter.content,
        "paragraphs": chapter.paragraphs or []
    }


def serialize_chunk(chunk: KnowledgeChunk) -> Dict[str, Any]:
    return {
        "id": chunk.id,
        "bookId": chunk.book_id,
        "book_id": chunk.book_id,
        "chapterId": chunk.chapter_id,
        "chapter_id": chunk.chapter_id,
        "chunkOrder": chunk.chunk_order,
        "chunk_order": chunk.chunk_order,
        "fullText": chunk.full_text,
        "full_text": chunk.full_text,
        "textArabic": chunk.text_arabic,
        "text_arabic": chunk.text_arabic,
        "summary": chunk.summary,
        "hypotheticalQuestions": chunk.hypothetical_questions or [],
        "hypothetical_questions": chunk.hypothetical_questions or [],
        "coreConcepts": chunk.core_concepts or [],
        "core_concepts": chunk.core_concepts or [],
        "domainInsights": chunk.domain_insights or [],
        "domain_insights": chunk.domain_insights or [],
        "pageNumber": chunk.page_number,
        "page_number": chunk.page_number,
        "contentType": chunk.content_type,
        "content_type": chunk.content_type,
        "language": chunk.language,
        "isProcessed": chunk.is_processed,
        "is_processed": chunk.is_processed,
        "createdAt": chunk.created_at.isoformat() if chunk.created_at else None,
        "created_at": chunk.created_at.isoformat() if chunk.created_at else None
    }


def serialize_reading_progress(prog: ReadingProgress) -> Dict[str, Any]:
    return {
        "id": prog.id,
        "userId": prog.user_id,
        "user_id": prog.user_id,
        "bookId": prog.book_id,
        "book_id": prog.book_id,
        "currentChapterId": prog.current_chapter_id,
        "current_chapter_id": prog.current_chapter_id,
        "currentParagraphIndex": prog.current_paragraph_index,
        "current_paragraph_index": prog.current_paragraph_index,
        "percentage": prog.percentage,
        "updatedAt": prog.updated_at.isoformat() if prog.updated_at else None,
        "updated_at": prog.updated_at.isoformat() if prog.updated_at else None
    }


@router.get("/categories", summary="فهرست دسته‌بندی‌های کتابخانه")
async def list_categories(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(LibraryCategory).order_by(LibraryCategory.order_index.asc())
    categories, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_category(c) for c in categories],
        meta=meta
    )


@router.post("/categories", summary="ثبت دسته‌بندی جدید در کتابخانه")
async def create_category(
    payload: CreateCategoryRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    cat_id = payload.id or f"cat_{uuid.uuid4().hex[:8]}"
    existing = await db.scalar(select(LibraryCategory).where(LibraryCategory.id == cat_id))
    if existing:
        raise HTTPException(status_code=400, detail="دسته‌بندی با این شناسه قبلاً ثبت شده است.")

    icon = payload.iconName or payload.icon_name or "menu_book"
    order = payload.orderIndex if payload.orderIndex is not None else (payload.order_index or 0)
    parent_id = payload.parentId or payload.parent_id

    category = LibraryCategory(
        id=cat_id,
        title=payload.title.strip(),
        icon_name=icon,
        order_index=order,
        parent_id=parent_id
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return success_response(
        data=serialize_category(category),
        meta={"message": f"دسته‌بندی '{category.title}' با موفقیت ایجاد شد."}
    )


@router.delete("/categories/{cat_id}", summary="حذف دسته‌بندی کتابخانه")
async def delete_category(
    cat_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    category = await db.scalar(select(LibraryCategory).where(LibraryCategory.id == cat_id))
    if not category:
        raise HTTPException(status_code=404, detail="دسته‌بندی مورد نظر یافت نشد.")
    await db.delete(category)
    await db.commit()
    return success_response(data={"deleted": True, "id": cat_id})


# -------------------------------------------------------------
# Admin Posters / Banners Endpoints (مدیریت بنرها و پوسترهای ویترین)
# -------------------------------------------------------------

@router.get("/posters", summary="فهرست پوسترهای ویترین کتابخانه")
async def list_posters(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(LibraryPoster).order_by(LibraryPoster.order_index.asc())
    posters = (await db.scalars(stmt)).all()
    return success_response(data=[serialize_poster(p) for p in posters])


@router.post("/posters", summary="بارگذاری و ثبت پوستر جدید در ویترین کتابخانه")
async def create_poster(
    payload: CreatePosterRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    poster_id = payload.id or f"poster_{uuid.uuid4().hex[:8]}"
    existing = await db.scalar(select(LibraryPoster).where(LibraryPoster.id == poster_id))
    if existing:
        raise HTTPException(status_code=400, detail="پوستر با این شناسه قبلاً ثبت شده است.")

    img = payload.imageUrl or payload.image_url or "https://cdn.ettehad.app/library/posters/poster_default.jpg"
    target_id = payload.targetBookId or payload.target_book_id
    order = payload.orderIndex if payload.orderIndex is not None else (payload.order_index or 0)

    poster = LibraryPoster(
        id=poster_id,
        title=payload.title.strip(),
        subtitle=payload.subtitle,
        image_url=img,
        target_book_id=target_id,
        order_index=order
    )
    db.add(poster)
    await db.commit()
    await db.refresh(poster)
    return success_response(
        data=serialize_poster(poster),
        meta={"message": f"پوستر '{poster.title}' با موفقیت در ویترین ثبت شد."}
    )


@router.delete("/posters/{poster_id}", summary="حذف پوستر از ویترین کتابخانه")
async def delete_poster(
    poster_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    poster = await db.scalar(select(LibraryPoster).where(LibraryPoster.id == poster_id))
    if not poster:
        raise HTTPException(status_code=404, detail="پوستر مورد نظر یافت نشد.")
    await db.delete(poster)
    await db.commit()
    return success_response(data={"deleted": True, "id": poster_id})


@router.post("/books", summary="افزودن کتاب جدید به کتابخانه")
async def create_book(
    payload: CreateBookRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    b_id = payload.id or f"book_{uuid.uuid4().hex[:8]}"
    existing = await db.scalar(select(Book).where(Book.id == b_id))
    if existing:
        raise HTTPException(status_code=400, detail="کتابی با این شناسه قبلاً ثبت شده است.")

    cat_id = payload.categoryId or payload.category_id
    feat = payload.isFeatured if payload.isFeatured is not None else bool(payload.is_featured)
    cov = payload.coverUrl or payload.cover_url or "https://cdn.ettehad.app/books/covers/cover_default.jpg"
    pg = payload.pageCount or payload.page_count or 100
    py = payload.publicationYear or payload.publication_year or "1402"

    book = Book(
        id=b_id,
        title=payload.title.strip(),
        author=payload.author.strip(),
        translator=payload.translator,
        publisher=payload.publisher,
        publication_year=py,
        cover_url=cov,
        category_id=cat_id,
        is_featured=feat,
        tags=payload.tags or [],
        description=payload.description or "",
        language=payload.language or "fa",
        page_count=pg,
        rating=payload.rating or 4.8
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return success_response(
        data=serialize_book(book),
        meta={"message": f"کتاب '{book.title}' با موفقیت به کتابخانه افزوده شد."}
    )


@router.delete("/books/{book_id}", summary="حذف کتاب از کتابخانه")
async def delete_book(
    book_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    book = await db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="کتاب مورد نظر یافت نشد.")
    await db.delete(book)
    await db.commit()
    return success_response(data={"deleted": True, "id": book_id})


@router.get("/books", summary="فهرست صفحه‌بندی‌شده کتب کتابخانه با فیلترها")
async def list_books(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    category_id: Optional[str] = Query(None),
    categoryId: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    isFeatured: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(Book)

    cat_id = category_id or categoryId
    if cat_id:
        stmt = stmt.where(Book.category_id == cat_id)

    featured = is_featured if is_featured is not None else isFeatured
    if featured is not None:
        stmt = stmt.where(Book.is_featured == featured)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.publisher.ilike(pattern)
            )
        )

    sort_col = Book.id
    if sortBy:
        lower = sortBy.lower()
        if lower in ["title"]:
            sort_col = Book.title
        elif lower in ["author"]:
            sort_col = Book.author
        elif lower in ["rating"]:
            sort_col = Book.rating

    if sortOrder.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    books, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_book(b) for b in books],
        meta=meta
    )


@router.get("/books/{id}/chapters", summary="فهرست فصول کتاب")
async def list_book_chapters(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    book = await db.scalar(select(Book).where(Book.id == id))
    if not book:
        raise HTTPException(status_code=404, detail="کتاب مورد نظر یافت نشد.")

    stmt = select(BookChapter).where(BookChapter.book_id == id).order_by(BookChapter.chapter_number.asc())
    chapters = (await db.scalars(stmt)).all()

    return success_response(data=[serialize_chapter(c) for c in chapters])


@router.get("/chunks", summary="فهرست صفحه‌بندی‌شده چانک‌های دانشی معنایی RAG")
async def list_knowledge_chunks(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    book_id: Optional[str] = Query(None),
    bookId: Optional[str] = Query(None),
    chapter_id: Optional[str] = Query(None),
    chapterId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(KnowledgeChunk)

    b_id = book_id or bookId
    if b_id:
        stmt = stmt.where(KnowledgeChunk.book_id == b_id)

    c_id = chapter_id or chapterId
    if c_id:
        stmt = stmt.where(KnowledgeChunk.chapter_id == c_id)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                KnowledgeChunk.full_text.ilike(pattern),
                KnowledgeChunk.summary.ilike(pattern)
            )
        )

    stmt = stmt.order_by(KnowledgeChunk.chunk_order.asc(), KnowledgeChunk.created_at.desc())

    chunks, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_chunk(c) for c in chunks],
        meta=meta
    )


@router.get("/reading-progress", summary="آمار و پیشرفت مطالعه کاربران")
@router.get("/reading-stats", summary="آمار و پیشرفت مطالعه کاربران (آلیاس)")
async def list_reading_progress(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    book_id: Optional[str] = Query(None),
    bookId: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(ReadingProgress)

    u_id = user_id or userId
    if u_id:
        stmt = stmt.where(ReadingProgress.user_id == u_id)

    b_id = book_id or bookId
    if b_id:
        stmt = stmt.where(ReadingProgress.book_id == b_id)

    stmt = stmt.order_by(ReadingProgress.updated_at.desc())

    items, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_reading_progress(p) for p in items],
        meta=meta
    )


def serialize_evaluation_report(rep: RAGEvaluationReport, include_details: bool = True) -> Dict[str, Any]:
    data = {
        "id": rep.id,
        "bookId": rep.book_id,
        "title": rep.title,
        "totalQueries": rep.total_queries,
        "avgRelevanceScore": rep.avg_relevance_score,
        "hitRateAt3": rep.hit_rate_at_3,
        "passingRate": rep.passing_rate,
        "status": rep.status,
        "createdAt": rep.created_at.isoformat() if rep.created_at else None,
    }
    if include_details:
        data["details"] = rep.details or {}
    return data


class ConfirmIngestRequest(BaseModel):
    bookData: Optional[Dict[str, Any]] = None
    booksData: Optional[List[Dict[str, Any]]] = None
    batchSize: Optional[int] = 5


@router.post("/ingest", summary="ورود داده ساختاریافته درختی کتاب/مقاله و نمایه‌سازی در دیتابیس و Qdrant")
async def ingest_book(
    book_data: Dict[str, Any] = Body(...),
    batch_size: Optional[int] = Query(None, alias="batchSize"),
    force_save: Optional[bool] = Query(False, alias="forceSave"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    if not book_data or not book_data.get("title"):
        raise HTTPException(status_code=400, detail="اطلاعات ساختاریافته کتاب شامل عنوان الزامی است.")
    effective_batch = batch_size or book_data.get("batchSize") or 5
    effective_force = bool(force_save or book_data.get("forceSave", False))
    result = await LibraryService.ingest_hierarchical_book(
        db,
        book_data,
        batch_size=effective_batch,
        force_save=effective_force
    )
    if result.get("isSavedToDatabase"):
        msg = f"کتاب '{book_data.get('title')}' با موفقیت وارد و نمایه‌سازی شد."
    else:
        msg = f"پردازش منبع انجام شد اما به دلیل عدم اتصال هوش مصنوعی، برای جلوگیری از آلودگی پایگاه دانش در دیتابیس ذخیره نشد. پیش‌نمایش در دسترس است."
    return success_response(
        data=result,
        meta={"message": msg}
    )


@router.post("/upload-json", summary="آپلود فایل JSON/JSONL کتب و منابع و نمایه‌سازی در دیتابیس و پایگاه برداری Qdrant")
async def upload_admin_library_json(
    file: UploadFile = File(...),
    batch_size: Optional[int] = Query(5, alias="batchSize"),
    force_save: Optional[bool] = Query(False, alias="forceSave"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    valid_ext = file.filename and (file.filename.lower().endswith(".json") or file.filename.lower().endswith(".jsonl"))
    if not valid_ext and file.content_type not in ["application/json", "text/plain", "application/octet-stream"]:
        raise HTTPException(status_code=400, detail="فرمت فایل نامعتبر است. لطفاً یک فایل با پسوند .json یا .jsonl ارسال کنید.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="فایل بارگذاری‌شده خالی است.")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"حجم فایل بیش از سقف مجاز ({settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} مگابایت) است."
        )

    res = await LibraryService.ingest_from_json_file(
        db,
        file_bytes,
        filename=file.filename,
        batch_size=batch_size or 5,
        force_save=force_save or False
    )
    if res.get("isSavedToDatabase"):
        msg = f"فایل '{file.filename}' با موفقیت به صورت دسته‌ای پردازش و نمایه‌سازی شد."
    else:
        msg = f"پردازش فایل '{file.filename}' انجام شد اما به دلیل عدم اتصال هوش مصنوعی در دیتابیس ذخیره نشد. پیش‌نمایش در دسترس است."
    return success_response(
        data=res,
        meta={"message": msg}
    )


@router.post("/confirm-ingest", summary="تایید دستی و ذخیره‌سازی داده‌های پردازش‌شده در پایگاه داده و برداری")
async def confirm_ingest_book(
    payload: ConfirmIngestRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    if payload.bookData:
        res = await LibraryService.ingest_hierarchical_book(
            db,
            payload.bookData,
            batch_size=payload.batchSize or 5,
            force_save=True
        )
        return success_response(
            data=res,
            meta={"message": f"کتاب '{payload.bookData.get('title')}' با تایید دستی در پایگاه داده و Qdrant ذخیره شد."}
        )
    elif payload.booksData:
        results = []
        for b in payload.booksData:
            r = await LibraryService.ingest_hierarchical_book(
                db,
                b,
                batch_size=payload.batchSize or 5,
                force_save=True
            )
            results.append(r)
        return success_response(
            data={"success": True, "books": results, "isSavedToDatabase": True},
            meta={"message": "تمام منابع با تایید دستی در پایگاه داده و برداری ذخیره شدند."}
        )
    else:
        raise HTTPException(status_code=400, detail="داده‌های منبع جهت تایید و ذخیره‌سازی ارسال نشده است.")



@router.post("/evaluation/benchmark", summary="اجرای بنچ‌مارک ارزیابی دسته‌ای تناسب بازیابی (RAG Benchmark)")
async def run_evaluation_benchmark(
    payload: BenchmarkRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    result = await RAGEvaluatorService.run_batch_benchmark(
        db=db,
        book_id=payload.bookId,
        custom_queries=payload.customQueries,
        limit_queries=payload.limitQueries or 15
    )
    return success_response(
        data=result,
        meta={"message": f"آزمون ارزیابی با موفقیت اجرا شد. نمره میانگین: {result.get('avgRelevanceScore')}%"}
    )


@router.get("/evaluation/reports", summary="فهرست گزارش‌های ارزیابی ذخیره‌شده")
async def list_evaluation_reports(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    book_id: Optional[str] = Query(None),
    bookId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(RAGEvaluationReport)
    b_id = book_id or bookId
    if b_id:
        stmt = stmt.where(RAGEvaluationReport.book_id == b_id)
    if status:
        stmt = stmt.where(RAGEvaluationReport.status == status)
    stmt = stmt.order_by(RAGEvaluationReport.created_at.desc())

    items, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_evaluation_report(r, include_details=False) for r in items],
        meta=meta
    )


@router.get("/evaluation/reports/{report_id}", summary="جزئیات کامل یک گزارش ارزیابی")
async def get_evaluation_report(
    report_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    report = await db.scalar(select(RAGEvaluationReport).where(RAGEvaluationReport.id == report_id))
    if not report:
        raise HTTPException(status_code=404, detail="گزارش ارزیابی یافت نشد.")
    return success_response(
        data=serialize_evaluation_report(report, include_details=True)
    )


@router.post("/evaluation/test-query", summary="سنجش آنی تناسب بازیابی برای یک پرسش دلخواه (Ad-hoc Query Test)")
async def test_single_query_evaluation(
    payload: TestQueryRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    clean_q = payload.query.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="متن پرسش الزامی است.")

    try:
        await VectorService.sync_chunks_from_db(db)
    except Exception:
        pass

    hits = await VectorService.search_semantic(query=clean_q, limit=3, book_id=payload.bookId)
    if not hits:
        book_title = "کتابخانه"
        if payload.bookId:
            b_obj = await db.scalar(select(Book).where(Book.id == payload.bookId))
            if b_obj:
                book_title = b_obj.title
        hits = await RAGEvaluatorService.search_database_chunks_smart(
            db=db,
            query=clean_q,
            book_id=payload.bookId,
            book_title=book_title,
            limit=3
        )

    eval_result = await RAGEvaluatorService.evaluate_retrieval_set(clean_q, hits)
    return success_response(
        data={
            "query": clean_q,
            "topScore": eval_result.get("top_relevance_score"),
            "meanScore": eval_result.get("mean_relevance_score"),
            "hitAt3": eval_result.get("hit_at_3"),
            "isSufficient": eval_result.get("is_sufficient"),
            "retrievedCount": len(hits),
            "contexts": eval_result.get("evaluated_contexts", [])
        }
    )


# ==========================================
# 7. BOOK SUBMISSIONS & REQUESTS MANAGEMENT
# ==========================================
class UpdateSubmissionStatusRequest(BaseModel):
    status: str  # PENDING, IN_REVIEW, APPROVED, AVAILABLE, REJECTED
    adminNotes: Optional[str] = None


@router.get("/submissions", summary="فهرست کتاب‌های ارسالی و درخواست‌های کتاب ناموجود")
async def list_submissions(
    type: Optional[str] = Query(None),  # SUBMIT_NEW, REQUEST_EXISTING
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(BookSubmissionRequest)
    if type:
        stmt = stmt.where(BookSubmissionRequest.type == type)
    if status:
        stmt = stmt.where(BookSubmissionRequest.status == status)
    if q:
        pat = f"%{q}%"
        stmt = stmt.where(or_(
            BookSubmissionRequest.title.ilike(pat),
            BookSubmissionRequest.author.ilike(pat),
            BookSubmissionRequest.tracking_code.ilike(pat),
            BookSubmissionRequest.user_name.ilike(pat),
            BookSubmissionRequest.user_contact.ilike(pat)
        ))

    stmt = stmt.order_by(desc(BookSubmissionRequest.created_at))
    items, meta = await paginate(db, stmt, page=page, limit=limit)
    return success_response(
        data=[
            {
                "id": s.id,
                "title": s.title,
                "author": s.author,
                "publisher": s.publisher,
                "description": s.description,
                "fileUrl": s.file_url,
                "type": s.type,
                "status": s.status,
                "trackingCode": s.tracking_code,
                "tracking_code": s.tracking_code,
                "userName": s.user_name,
                "user_name": s.user_name,
                "userContact": s.user_contact,
                "user_contact": s.user_contact,
                "adminNotes": s.admin_notes,
                "admin_notes": s.admin_notes,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in items
        ],
        meta=meta
    )


@router.put("/submissions/{sub_id}/status", summary="تغییر وضعیت درخواست یا ارسال کتاب")
async def update_submission_status(
    sub_id: str,
    payload: UpdateSubmissionStatusRequest,
    db: AsyncSession = Depends(get_db)
):
    sub = await db.scalar(select(BookSubmissionRequest).where(BookSubmissionRequest.id == sub_id))
    if not sub:
        raise HTTPException(status_code=404, detail="درخواست مورد نظر یافت نشد.")

    sub.status = payload.status
    if payload.adminNotes is not None:
        sub.admin_notes = payload.adminNotes

    await db.commit()
    await db.refresh(sub)
    return success_response(
        data={
            "id": sub.id,
            "status": sub.status,
            "adminNotes": sub.admin_notes,
            "trackingCode": sub.tracking_code
        },
        meta={"message": f"وضعیت درخواست به '{sub.status}' تغییر یافت."}
    )


@router.delete("/submissions/{sub_id}", summary="حذف درخواست یا ارسال کتاب")
async def delete_submission(
    sub_id: str,
    db: AsyncSession = Depends(get_db)
):
    sub = await db.scalar(select(BookSubmissionRequest).where(BookSubmissionRequest.id == sub_id))
    if not sub:
        raise HTTPException(status_code=404, detail="درخواست مورد نظر یافت نشد.")

    await db.delete(sub)
    await db.commit()
    return success_response(meta={"message": "درخواست با موفقیت حذف شد."})

