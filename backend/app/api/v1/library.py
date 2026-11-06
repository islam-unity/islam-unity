import os
import uuid
import shutil
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, Body, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.db.models import User
from app.services.library_service import LibraryService
from app.schemas.library import (
    ReadingProgressRequest, CreateShelfRequest, CreateHighlightRequest,
    BookChatRequest, ChapterAnalysisRequest, SemanticSearchRequest,
    ReaderContextualAIRequest, BookSubmissionCreateRequest, BookSubmissionResponse,
    BookAICategoryCreateRequest, BookAISessionCreateRequest, MasterAgentCrossBookQueryRequest,
    CreateBookReviewRequest
)
from app.core.exceptions import ValidationException, AttachmentOversizeException
from app.core.response import success_response
from app.config import settings

router = APIRouter()



# 3.1 Showcase & Categories
@router.get("/posters", summary="دریافت پوسترهای ویترین کتابخانه")
async def get_posters(
    db: AsyncSession = Depends(get_db)
):
    posters = await LibraryService.get_posters(db)
    return success_response(data=[p.model_dump() for p in posters])


@router.get("/categories", summary="فهرست دسته‌بندی‌های هشت‌گانه کتابخانه")
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    cats = await LibraryService.get_categories(db)
    return success_response(data=[c.model_dump() for c in cats])


# 3.2 Books Catalog & Reader
@router.get("/books", summary="فهرست کتاب‌ها با فیلتر دسته‌بندی، تگ و جستجو")
async def get_books(
    categoryId: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    isFeatured: Optional[bool] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await LibraryService.get_books(
        db=db,
        category_id=categoryId,
        q=q,
        is_featured=isFeatured,
        tag=tag,
        page=page,
        limit=limit
    )
    return success_response(
        data=[b.model_dump() for b in result["items"]],
        meta=result["meta"]
    )


@router.get("/books/{bookId}", summary="شناسنامه کامل کتاب، مشخصات نشر و فهرست فصول (TOC)")
async def get_book_detail(
    bookId: str,
    db: AsyncSession = Depends(get_db)
):
    book = await LibraryService.get_book_detail(db, bookId)
    return success_response(data=book.model_dump())


@router.get("/books/{bookId}/reviews", summary="دریافت نظرات کاربران پیرامون کتاب")
async def get_book_reviews(
    bookId: str,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    reviews = await LibraryService.get_book_reviews(db, bookId, limit)
    return success_response(data=[r.model_dump() for r in reviews])


@router.post("/books/{bookId}/reviews", summary="ثبت نظر و امتیاز برای کتاب")
async def create_book_review(
    bookId: str,
    data: CreateBookReviewRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    author_name = current_user.full_name if current_user else (data.authorName or "کاربر گرامی")
    review = await LibraryService.create_book_review(
        db=db,
        book_id=bookId,
        user_id=user_id,
        author_name=author_name,
        rating=data.rating,
        content=data.content
    )
    return success_response(data=review.model_dump())



@router.get("/books/{bookId}/chapters/{chapterId}", summary="متن کامل فصل، زمان مطالعه و پاراگراف‌ها")
async def get_chapter_detail(
    bookId: str,
    chapterId: str,
    db: AsyncSession = Depends(get_db)
):
    chapter = await LibraryService.get_chapter_detail(db, bookId, chapterId)
    return success_response(data=chapter.model_dump())


# 3.3 User Shelves & Progress
@router.put("/books/{bookId}/progress", summary="ثبت درصد مطالعه و موقعیت پاراگراف کاربر")
async def save_progress(
    bookId: str,
    data: ReadingProgressRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    res = await LibraryService.save_progress(db, uid, bookId, data)
    return success_response(data=res)


@router.post("/books/{bookId}/favorite", summary="افزودن / حذف کتاب از علاقه‌مندی‌ها")
async def toggle_favorite(
    bookId: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    res = await LibraryService.toggle_favorite(db, uid, bookId)
    return success_response(data=res)


@router.get("/user/shelves", summary="دریافت قفسه‌های شخصی کاربر به همراه کتاب‌ها")
async def get_user_shelves(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    shelves = await LibraryService.get_user_shelves(db, uid)
    return success_response(data=[s.model_dump() for s in shelves])


@router.post("/user/shelves", summary="ایجاد قفسه شخصی جدید")
async def create_user_shelf(
    data: CreateShelfRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    shelf = await LibraryService.create_shelf(db, uid, data)
    return success_response(data=shelf.model_dump())


@router.delete("/user/shelves/{shelfId}", summary="حذف کامل یک قفسه شخصی")
async def delete_user_shelf(
    shelfId: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    deleted = await LibraryService.delete_shelf(db, uid, shelfId)
    return success_response(data={"shelfId": shelfId, "deleted": deleted})


@router.post("/user/shelves/{shelfId}/books", summary="افزودن کتاب به قفسه مشخص")
async def add_book_to_shelf(
    shelfId: str,
    bookId: str = Query(..., description="شناسه کتاب"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    res = await LibraryService.add_book_to_shelf(db, uid, shelfId, bookId)
    return success_response(data=res)


@router.delete("/user/shelves/{shelfId}/books/{bookId}", summary="حذف کتاب از قفسه")
async def remove_book_from_shelf(
    shelfId: str,
    bookId: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else "usr_seeker_1"
    res = await LibraryService.remove_book_from_shelf(db, uid, shelfId, bookId)
    return success_response(data=res)



# 3.4 Highlights & Annotations
@router.get("/user/highlights", summary="دریافت هایلایت‌ها و یادداشت‌های کاربر")
async def get_highlights(
    bookId: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    hl = await LibraryService.get_highlights(db, current_user.id, bookId)
    return success_response(data=[h.model_dump() for h in hl])


@router.post("/books/{bookId}/highlights", summary="ثبت هایلایت و یادداشت حاشیه‌ای برای کتاب")
async def create_highlight(
    bookId: str,
    data: CreateHighlightRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    hl = await LibraryService.create_highlight(db, current_user.id, bookId, data)
    return success_response(data=hl.model_dump())


@router.delete("/user/highlights/{highlightId}", summary="حذف هایلایت")
async def delete_highlight(
    highlightId: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.delete_highlight(db, current_user.id, highlightId)
    return success_response(data=res)


# 3.5 AI Book Chat & Research Tools
@router.post("/books/{bookId}/ai/reader-stream", summary="استریم زنده دستیار هوشمند کتابخوان برای متن انتخابی و پرسش‌ها (SSE)")
async def stream_reader_ai(
    bookId: str,
    data: ReaderContextualAIRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    return StreamingResponse(
        LibraryService.stream_reader_contextual_ai(
            db=db,
            book_id=bookId,
            request=data,
            user_id=user_id
        ),
        media_type="text/event-stream"
    )


@router.post("/books/{bookId}/ai/chat-stream", summary="استریم زنده گفتگوی هوشمند چندمرحله‌ای با کتاب بر مبنای RAG (SSE)")
async def stream_book_chat(
    bookId: str,
    data: BookChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    return StreamingResponse(
        LibraryService.stream_book_details_ai_chat(
            db=db,
            book_id=bookId,
            query=data.query,
            conversation_id=data.conversationId,
            history=data.history,
            user_id=user_id
        ),
        media_type="text/event-stream"
    )


@router.post("/books/{bookId}/ai/chat", summary="گفتگوی هوشمند با کتاب به همراه ارجاع به جلد و صفحه")
async def chat_with_book(
    bookId: str,
    data: BookChatRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.ai_chat_with_book(
        db=db,
        book_id=bookId,
        query=data.query,
        conversation_id=data.conversationId,
        history=data.history
    )
    return success_response(data=res.model_dump())


@router.post("/ai/analyze", summary="ابزارهای تحلیلی هوش مصنوعی فصل (خلاصه، اصطلاحات، آزمون تدبر و...)")
async def analyze_chapter(
    data: ChapterAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.ai_analyze_chapter(db, data.bookId, data.chapterId, data.analysisType)
    return success_response(data=res.model_dump())


@router.post("/ai/semantic-search", summary="کاوش معنایی برداری و پیشنهاد هوشمند کتاب در ویترین کتابخانه")
async def semantic_search(
    data: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.semantic_search(db, data.query, data.limit or 5, data.categoryId)
    return success_response(data=[r.model_dump() for r in res])


@router.post("/ingest-json", summary="ورود ساختاریافته منبع/کتاب در دیتابیس رابطه‌ای و پایگاه برداری Qdrant")
async def ingest_book_json(
    book_data: Dict[str, Any] = Body(...),
    batch_size: Optional[int] = Query(None, alias="batchSize"),
    db: AsyncSession = Depends(get_db)
):
    eff_batch = batch_size or book_data.get("batchSize") or 5
    res = await LibraryService.ingest_hierarchical_book(db, book_data, batch_size=eff_batch)
    return success_response(data=res)


@router.post("/upload-json", summary="آپلود فایل JSON/JSONL داده‌ها و نمایه‌سازی هوشمند در پایگاه داده و Qdrant")
async def upload_library_json(
    file: UploadFile = File(...),
    batch_size: Optional[int] = Query(5, alias="batchSize"),
    db: AsyncSession = Depends(get_db)
):
    valid_ext = file.filename and (file.filename.lower().endswith(".json") or file.filename.lower().endswith(".jsonl"))
    if not valid_ext and file.content_type not in ["application/json", "text/plain", "application/octet-stream"]:
        raise ValidationException("فرمت فایل نامعتبر است. لطفاً یک فایل با پسوند .json یا .jsonl ارسال نمایید.")

    file_bytes = await file.read()
    if not file_bytes:
        raise ValidationException("فایل بارگذاری‌شده خالی است.")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise AttachmentOversizeException(
            message=f"حجم فایل بیش از سقف مجاز ({settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} مگابایت) است."
        )

    res = await LibraryService.ingest_from_json_file(db, file_bytes, filename=file.filename, batch_size=batch_size or 5)
    return success_response(
        data=res,
        meta={"message": f"فایل '{file.filename}' با موفقیت به صورت دسته‌ای پردازش و نمایه‌سازی شد."}
    )


# 3.4 Book Submissions & Requests (ارسال اثر و درخواست کتاب)
@router.post("/requests", summary="ثبت ارسال کتاب جدید یا درخواست کتاب ناموجود")
async def create_book_request(
    data: BookSubmissionCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    res = await LibraryService.create_submission(db, data, user_id=user_id)
    return success_response(
        data=res.model_dump(),
        meta={"message": "درخواست شما با موفقیت ثبت شد و کد رهگیری اختصاص یافت."}
    )


@router.get("/requests/track/{tracking_code}", summary="پیگیری وضعیت درخواست یا کتاب ارسالی با کد رهگیری")
async def track_book_request(
    tracking_code: str,
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.get_submission_by_tracking_code(db, tracking_code)
    if not res:
        raise ValidationException("درخواستی با این کد رهگیری یافت نشد.")
    return success_response(data=res.model_dump())


@router.get("/requests/my", summary="دریافت فهرست درخواست‌ها و کتاب‌های ارسالی کاربر")
async def get_my_book_requests(
    contact: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    if not user_id and not contact:
        return success_response(data=[])
    items = await LibraryService.get_submissions_by_user_or_contact(db, user_id=user_id, contact=contact)
    return success_response(data=[i.model_dump() for i in items])


@router.post("/upload-file", summary="آپلود فایل اثر (PDF/EPUB) یا تصویر جلد برای ارسال کتاب")
async def upload_submission_file(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    filename = file.filename or "file"
    ext = os.path.splitext(filename)[1].lower()

    allowed_exts = {".pdf", ".epub", ".doc", ".docx", ".zip", ".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed_exts:
        raise ValidationException(f"فرمت فایل مجاز نیست. فرمت‌های مجاز: {', '.join(allowed_exts)}")

    upload_folder = os.path.join(settings.UPLOAD_DIR, "library_submissions")
    os.makedirs(upload_folder, exist_ok=True)

    safe_name = f"sub_{uuid.uuid4().hex[:12]}{ext}"
    target_path = os.path.join(upload_folder, safe_name)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_url = f"{settings.STATIC_URL_PREFIX}/uploads/library_submissions/{safe_name}"
    return success_response(data={
        "file_url": file_url,
        "filename": filename,
        "size": os.path.getsize(target_path)
    })


# 3.7 Book AI Categories, Sessions & Master Agent Cross-Book Intelligence

@router.get("/ai/categories", summary="دریافت دسته‌بندی‌های هوش مصنوعی کتابخوان")
async def get_book_ai_categories(
    db: AsyncSession = Depends(get_db)
):
    cats = await LibraryService.get_book_ai_categories(db)
    return success_response(data=[c.model_dump() for c in cats])


@router.post("/ai/categories", summary="افزودن دسته‌بندی جدید به هوش مصنوعی کتابخوان")
async def create_book_ai_category(
    data: BookAICategoryCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    cat = await LibraryService.create_book_ai_category(db, data)
    return success_response(data=cat.model_dump())


@router.get("/books/{bookId}/ai/sessions", summary="دریافت تاریخچه نشست‌های گفت‌وگوی هوش مصنوعی برای این کتاب")
async def get_book_ai_sessions(
    bookId: str,
    category: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    sessions = await LibraryService.get_book_ai_sessions(db, bookId, user_id=user_id, category=category)
    return success_response(data=[s.model_dump() for s in sessions])


@router.post("/books/{bookId}/ai/sessions", summary="ایجاد نشست گفت‌وگوی جدید هوش مصنوعی در یک دسته‌بندی خاص")
async def create_book_ai_session(
    bookId: str,
    data: BookAISessionCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else "guest_user"
    session = await LibraryService.create_book_ai_session(db, bookId, user_id=user_id, data=data)
    return success_response(data=session.model_dump())


@router.get("/ai/master-agent/cross-book-sessions", summary="دسترسی ایجنت مادر به تمام پرسش‌ها، تاریخچه‌ها و دسته‌بندی‌های کتب")
async def get_master_agent_cross_book_sessions(
    category: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    history = await LibraryService.get_master_agent_cross_book_history(db, category=category, user_id=user_id)
    return success_response(data=history)


@router.post("/ai/master-agent/query", summary="پرسش کلان و فرارشته‌ای از ایجنت مادر در سراسر کتب و دسته‌بندی‌ها")
async def query_master_agent(
    data: MasterAgentCrossBookQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await LibraryService.query_master_agent_cross_books(
        db=db,
        query=data.query,
        category=data.category,
        book_ids=data.bookIds
    )
    return success_response(data=res.model_dump())


