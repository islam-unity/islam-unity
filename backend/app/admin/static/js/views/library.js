/**
 * View 4: Library & Knowledge Base (کتابخانه و دانش معنایی)
 * Books, Chapters drawer, RAG Knowledge Chunks, Categories, and Reading Progress.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderLibrary(container) {
  let activeTab = 'books'; // 'books' | 'chunks' | 'categories' | 'stats' | 'eval'

  let booksState = { page: 1, pageSize: 10, search: '', data: [], meta: null };
  let chunksState = { page: 1, pageSize: 10, search: '', data: [], meta: null };
  let catsState = { page: 1, pageSize: 25, data: [], meta: null };
  let statsState = { page: 1, pageSize: 10, data: [], meta: null };
  let evalReportsState = { page: 1, pageSize: 10, data: [], meta: null };
  let submissionsState = { page: 1, pageSize: 10, search: '', status: '', data: [], meta: null };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">📚 کتابخانه معارفی و پایگاه دانش معنایی (RAG)</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-lib-books" class="subtab-btn active">کتاب‌ها و فصول</button>
          <button id="tab-lib-chunks" class="subtab-btn">چانک‌های پایگاه دانش (RAG)</button>
          <button id="tab-lib-cats" class="subtab-btn">دسته‌بندی‌های کتب</button>
          <button id="tab-lib-posters" class="subtab-btn">🖼️ مجموعه‌های ویژه و ویترین</button>
          <button id="tab-lib-stats" class="subtab-btn">آمار و پیشرفت مطالعه</button>
          <button id="tab-lib-eval" class="subtab-btn">⚖️ ورود داده و ارزیابی RAG</button>
          <button id="tab-lib-submissions" class="subtab-btn">📬 کتاب‌های پیشنهادی و ارسالی کاربران</button>
        </div>


        <!-- Books Tab -->
        <div id="section-lib-books">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="books-search" type="text" class="search-input" placeholder="جستجو بر اساس عنوان یا نویسنده کتاب...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-add-book" class="btn btn-primary btn-sm">➕ افزودن سریع کتاب</button>
              <button id="btn-refresh-books" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="books-table-container"></div>
        </div>

        <!-- Chunks Tab -->
        <div id="section-lib-chunks" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="chunks-search" type="text" class="search-input" placeholder="جستجوی متنی در متن یا چکیده چانک‌ها...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-chunks" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="chunks-table-container"></div>
        </div>

        <!-- Categories Tab -->
        <div id="section-lib-cats" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <button id="btn-add-cat" class="btn btn-primary btn-sm">➕ افزودن دسته‌بندی جدید</button>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-cats" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="cats-table-container"></div>
        </div>

        <!-- Posters Tab -->
        <div id="section-lib-posters" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <button id="btn-add-poster" class="btn btn-primary btn-sm">➕ ایجاد پوستر یا مجموعه جدید ویترین</button>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-posters" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="posters-table-container"></div>
        </div>

        <!-- Reading Stats Tab -->
        <div id="section-lib-stats" style="display: none;">
          <div id="stats-table-container"></div>
        </div>

        <!-- RAG Ingestion & Evaluation Tab -->
        <div id="section-lib-eval" style="display: none;">
          <!-- Section 1: Ingestion Card -->
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <h3 style="margin: 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
                <span>📥</span> ورود داده‌های درختی کتاب و نمایه‌سازی هوشمند (Data Ingestion)
              </h3>
              <button id="btn-load-sample-json" class="btn btn-secondary btn-sm">📋 درج نمونه JSON معارفی</button>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
              فایل JSON یا ساختار درختی کتاب (شامل فصول، زیرفصول و بندها) را انتخاب یا وارد کنید تا چانک‌بندی هوشمند، استخراج مفاهیم کلیدی، تولید پرسش‌های فرضی و ذخیره در دیتابیس و Qdrant به صورت خودکار انجام شود. داده‌های جدید بلافاصله در آزمون‌های ارزیابی زیر قابل آزمایش خواهند بود.
            </p>

            <!-- File Upload Bar -->
            <div style="display: flex; align-items: center; gap: 0.75rem; background: var(--bg-body); border: 1px dashed var(--border-color); border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.85rem; flex-wrap: wrap;">
              <span style="font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 0.35rem;">
                <span>📁</span> آپلود مستقیم فایل JSON / JSONL:
              </span>
              <input type="file" id="ingest-file-input" accept=".json,.jsonl,application/json,text/plain" class="search-input" style="flex: 1; min-width: 220px; padding: 0.35rem 0.5rem; font-size: 0.82rem;">
              <button id="btn-upload-file-ingest" class="btn btn-primary btn-sm">📤 آپلود فایل و نمایه‌سازی</button>
            </div>

            <div style="margin-bottom: 0.75rem;">
              <label style="display: block; font-size: 0.82rem; margin-bottom: 0.35rem; color: var(--text-muted);">یا متن دستی JSON را مستقیماً در این کادر جای‌گذاری کنید:</label>
              <textarea id="ingest-json-input" class="search-input" style="width: 100%; height: 120px; font-family: monospace; font-size: 0.82rem; direction: ltr; text-align: left; resize: vertical;" placeholder='{\n  "title": "کتاب طهارت و صلاة",\n  "author": "شهید اول",\n  "category": "فقه و احکام",\n  "sections": [...]\n}'></textarea>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
              <button id="btn-submit-ingest" class="btn btn-secondary btn-sm">⚡ بارگذاری از متن کادر</button>
            </div>
          </div>

          <!-- Section 1.5: Live Ingestion Execution Pipeline & Chunk Representations Results -->
          <div id="ingest-results-container" style="display: none; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
              <div>
                <h3 style="margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; color: var(--primary);">
                  <span>🔍</span> فرآیندهای اجرا شده و نمایندگان معنایی استخراج‌شده از چانک‌ها
                </h3>
                <span id="ingest-meta-subtitle" style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem; display: block;"></span>
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <button id="btn-copy-ingest-json" class="btn btn-secondary btn-sm">📋 کپی ساختار JSON</button>
                <button id="btn-close-ingest-results" class="btn btn-secondary btn-sm">✕ بستن</button>
              </div>
            </div>

            <!-- Ingest Status Alert Banner (AI Connection & Persistence Status) -->
            <div id="ingest-status-alert-container" style="margin-bottom: 1.25rem;"></div>

            <!-- Stages Timeline -->
            <div style="margin-bottom: 1.5rem;">
              <h4 style="font-size: 0.88rem; margin: 0 0 0.75rem 0; color: var(--text-main); display: flex; align-items: center; gap: 0.4rem;">
                <span>⚙️</span> مراحل پایپ‌لاین اجرا شده (Execution Pipeline Stages):
              </h4>
              <div id="ingest-stages-timeline" class="ingest-timeline-grid"></div>
            </div>

            <!-- Chunk Representations Explorer -->
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; flex-wrap: wrap; gap: 0.5rem;">
                <h4 style="font-size: 0.88rem; margin: 0; color: var(--text-main); display: flex; align-items: center; gap: 0.4rem;">
                  <span>📑</span> پرسش‌ها و نمایندگان معنایی استخراج‌شده از هر چانک:
                  <span id="ingest-chunks-badge" class="badge badge-info" style="margin-inline-start: 0.35rem;">۰ چانک</span>
                </h4>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                  <input type="text" id="filter-ingest-chunks" class="search-input" placeholder="فیلتر در متن یا سوالات چانک‌ها..." style="padding: 0.25rem 0.6rem; font-size: 0.8rem; width: 220px;">
                  <select id="filter-ingest-chapter" class="search-input" style="padding: 0.25rem 0.6rem; font-size: 0.8rem;">
                    <option value="">همه فصول</option>
                  </select>
                </div>
              </div>
              <div id="ingest-chunks-list" style="display: flex; flex-direction: column; gap: 0.85rem;"></div>
            </div>
          </div>

          <!-- Section 2: Batch Benchmark Runner & Scorecard -->
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <h3 style="margin: 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
                <span>📊</span> بنچ‌مارک ارزیابی تناسب بازیابی (RAG Retrieval Benchmark)
              </h3>
              <button id="btn-run-benchmark" class="btn btn-primary btn-sm">🚀 اجرای آزمون ارزیابی</button>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
              <div>
                <label style="display: block; font-size: 0.82rem; margin-bottom: 0.35rem; color: var(--text-muted);">کتاب هدف برای ارزیابی:</label>
                <select id="benchmark-book-select" class="search-input" style="width: 100%;">
                  <option value="">همه کتب و چانک‌های سامانه</option>
                </select>
              </div>
              <div>
                <label style="display: block; font-size: 0.82rem; margin-bottom: 0.35rem; color: var(--text-muted);">پرسش‌های تستی دلخواه (اختیاری - هر خط یک سوال):</label>
                <textarea id="benchmark-custom-queries" class="search-input" style="width: 100%; height: 42px; font-size: 0.82rem; resize: vertical;" placeholder="مثال: احکام مطهرات آب جاری چیست؟"></textarea>
              </div>
            </div>

            <!-- Scorecards -->
            <div id="benchmark-scorecard-container" style="display: none; margin-top: 1rem;">
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.25rem;">
                <div style="background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; text-align: center;">
                  <div style="font-size: 0.78rem; color: var(--text-muted);">میانگین امتیاز تناسب</div>
                  <div id="metric-avg-relevance" style="font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-top: 0.25rem;">--</div>
                </div>
                <div style="background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; text-align: center;">
                  <div style="font-size: 0.78rem; color: var(--text-muted);">نرخ موفقیت ۳ نتیجه (Hit@3)</div>
                  <div id="metric-hit-rate" style="font-size: 1.4rem; font-weight: 700; color: var(--info); margin-top: 0.25rem;">--</div>
                </div>
                <div style="background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; text-align: center;">
                  <div style="font-size: 0.78rem; color: var(--text-muted);">درصد قبولی (>= ۶۵٪)</div>
                  <div id="metric-passing-rate" style="font-size: 1.4rem; font-weight: 700; color: var(--purple); margin-top: 0.25rem;">--</div>
                </div>
                <div style="background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; text-align: center;">
                  <div style="font-size: 0.78rem; color: var(--text-muted);">وضعیت آزمون</div>
                  <div id="metric-overall-status" style="font-size: 1.1rem; font-weight: 700; margin-top: 0.4rem;">--</div>
                </div>
              </div>
              <div id="benchmark-results-table"></div>
            </div>
          </div>

          <!-- Section 3: Live Query Tester -->
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <h3 style="margin: 0 0 0.75rem 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>🧪</span> آزمایشگر آنی تناسب بازیابی (Live Query Relevance Tester)
            </h3>
            <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
              <input id="test-query-input" type="text" class="search-input" style="flex: 1;" placeholder="هر سوال فقهی یا معارفی را وارد کنید (مثال: شرایط مبطلات وضو چیست؟)...">
              <button id="btn-run-test-query" class="btn btn-secondary btn-sm">سنجش تناسب بازیابی</button>
            </div>
            <div id="test-query-result-box" style="display: none; background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 1rem;"></div>
          </div>

          <!-- Section 4: Reports History -->
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
              <h3 style="margin: 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
                <span>📜</span> تاریخچه گزارش‌های ارزیابی بنچ‌مارک
              </h3>
              <button id="btn-refresh-eval-reports" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
            <div id="eval-reports-table-container"></div>
          </div>
        </div>

        <!-- Submissions Tab -->
        <div id="section-lib-submissions" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="submissions-search" type="text" class="search-input" placeholder="جستجو بر اساس عنوان، نویسنده، کد پیگیری یا متقاضی...">
              </div>
              <select id="submissions-filter-status" class="select-control">
                <option value="">همه وضعیت‌ها</option>
                <option value="PENDING">در انتظار بررسی (PENDING)</option>
                <option value="IN_REVIEW">در حال بررسی (IN_REVIEW)</option>
                <option value="APPROVED">تأیید شده (APPROVED)</option>
                <option value="AVAILABLE">موجود شده در کتابخانه (AVAILABLE)</option>
                <option value="REJECTED">رد شده (REJECTED)</option>
              </select>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-submissions" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="submissions-table-container"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabs = [
    { btn: '#tab-lib-books', sec: '#section-lib-books', name: 'books', load: fetchBooks },
    { btn: '#tab-lib-chunks', sec: '#section-lib-chunks', name: 'chunks', load: fetchChunks },
    { btn: '#tab-lib-cats', sec: '#section-lib-cats', name: 'categories', load: fetchCategories },
    { btn: '#tab-lib-posters', sec: '#section-lib-posters', name: 'posters', load: fetchPosters },
    { btn: '#tab-lib-stats', sec: '#section-lib-stats', name: 'stats', load: fetchStats },
    { btn: '#tab-lib-eval', sec: '#section-lib-eval', name: 'eval', load: fetchEvalReports },
    { btn: '#tab-lib-submissions', sec: '#section-lib-submissions', name: 'submissions', load: fetchSubmissions }
  ];

  tabs.forEach(t => {
    container.querySelector(t.btn).addEventListener('click', () => {
      activeTab = t.name;
      tabs.forEach(o => {
        container.querySelector(o.btn).classList.toggle('active', o.name === activeTab);
        container.querySelector(o.sec).style.display = o.name === activeTab ? 'block' : 'none';
      });
      t.load();
    });
  });

  // Books Search
  let bookSearchTimeout = null;
  container.querySelector('#books-search').addEventListener('input', (e) => {
    clearTimeout(bookSearchTimeout);
    bookSearchTimeout = setTimeout(() => {
      booksState.search = e.target.value.trim();
      booksState.page = 1;
      fetchBooks();
    }, 300);
  });
  container.querySelector('#btn-refresh-books').addEventListener('click', fetchBooks);

  // Chunks Search
  let chunkSearchTimeout = null;
  container.querySelector('#chunks-search').addEventListener('input', (e) => {
    clearTimeout(chunkSearchTimeout);
    chunkSearchTimeout = setTimeout(() => {
      chunksState.search = e.target.value.trim();
      chunksState.page = 1;
      fetchChunks();
    }, 300);
  });
  container.querySelector('#btn-refresh-chunks').addEventListener('click', fetchChunks);

  // Books Columns
  const bookColumns = [
    {
      header: 'عنوان کتاب',
      render: (b) => `
        <div>
          <div style="font-weight: 700;">${b.title || 'بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${b.author || 'نویسنده نامشخص'} ${b.publicationYear ? `(${b.publicationYear})` : ''}</div>
        </div>
      `
    },
    {
      header: 'دسته‌بندی',
      render: (b) => `<span class="badge badge-info">${b.categoryId || b.category_id || 'عمومی'}</span>`
    },
    {
      header: 'تعداد صفحات',
      render: (b) => formatNum(b.pageCount || b.page_count || 0)
    },
    {
      header: 'ویژه',
      render: (b) => (b.isFeatured ?? b.is_featured)
        ? `<span class="badge badge-success">⭐ ویژه</span>`
        : `<span class="badge badge-neutral">عادی</span>`
    },
    {
      header: 'امتیاز',
      render: (b) => `<span class="badge badge-warning">★ ${b.rating || '—'}</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (b) => `
        <div style="display: flex; gap: 0.35rem; justify-content: flex-end;">
          <button class="btn btn-primary btn-sm btn-view-chapters" data-book-id="${b.id}" data-book-title="${b.title || ''}">
            📖 فصول کتاب
          </button>
          <button class="btn btn-outline btn-sm btn-delete-book" data-book-id="${b.id}" data-book-title="${b.title || ''}" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.4);" title="حذف کتاب">
            🗑️
          </button>
        </div>
      `
    }
  ];

  async function fetchBooks() {
    renderTable({
      container: container.querySelector('#books-table-container'),
      columns: bookColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/books', {
        page: booksState.page,
        pageSize: booksState.pageSize,
        search: booksState.search
      });
      booksState.data = res.data || [];
      booksState.meta = res.meta;

      renderTable({
        container: container.querySelector('#books-table-container'),
        columns: bookColumns,
        data: booksState.data,
        meta: booksState.meta,
        currentPage: booksState.page,
        pageSize: booksState.pageSize,
        emptyMessage: 'کتابی یافت نشد.',
        onPageChange: (newPage) => {
          booksState.page = newPage;
          fetchBooks();
        },
        onPageSizeChange: (newSize) => {
          booksState.pageSize = newSize;
          booksState.page = 1;
          fetchBooks();
        }
      });

      // Attach Chapters drawer
      container.querySelectorAll('.btn-view-chapters').forEach(btn => {
        btn.addEventListener('click', async () => {
          const bookId = btn.getAttribute('data-book-id');
          const bookTitle = btn.getAttribute('data-book-title');
          openChaptersDrawer(bookId, bookTitle);
        });
      });

      // Attach Delete Book
      container.querySelectorAll('.btn-delete-book').forEach(btn => {
        btn.addEventListener('click', async () => {
          const bookId = btn.getAttribute('data-book-id');
          const bookTitle = btn.getAttribute('data-book-title');
          if (!confirm(`آیا از حذف کتاب «${bookTitle}» و تمامی چانک‌ها و فصول آن مطمئن هستید؟`)) return;

          btn.disabled = true;
          try {
            await ApiClient.delete(`/library/books/${bookId}`);
            Toast.success(`کتاب «${bookTitle}» با موفقیت حذف گردید.`);
            fetchBooks();
          } catch (err) {
            btn.disabled = false;
          }
        });
      });
    } catch (err) {
      container.querySelector('#books-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت کتب: ${err.message}</div></div>
      `;
    }
  }

  async function openChaptersDrawer(bookId, bookTitle) {
    Drawer.open({
      title: `فصول کتاب: ${bookTitle}`,
      subtitle: `در حال دریافت لیست فصول کتاب ${bookId}...`,
      contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
    });

    try {
      const res = await ApiClient.get(`/library/books/${bookId}/chapters`);
      const chapters = res.data || [];

      let contentHtml = chapters.length === 0
        ? '<div class="empty-state"><div class="empty-state-title">فصلی برای این کتاب ثبت نشده است.</div></div>'
        : chapters.map(c => `
            <div class="detail-section" style="margin-bottom: 0.75rem;">
              <div class="detail-section-title" style="display: flex; justify-content: space-between;">
                <span>فصل ${formatNum(c.chapterNumber || c.chapter_number || 1)}: ${c.title || 'بدون عنوان'}</span>
                <span class="badge badge-info">⏱ ${formatNum(c.readingTimeMinutes || c.reading_time_minutes || 0)} دقیقه</span>
              </div>
              <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
                ${c.content ? (c.content.slice(0, 300) + '...') : 'متن فصل بارگذاری نشده است.'}
              </div>
            </div>
          `).join('');

      Drawer.open({
        title: `فصول کتاب: ${bookTitle}`,
        subtitle: `تعداد کل فصول: ${formatNum(chapters.length)}`,
        contentHtml,
        footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
      });
    } catch (err) {
      Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت فصول: ${err.message}</div></div>`);
    }
  }

  // Chunks Columns
  const chunkColumns = [
    {
      header: 'شناسه چانک',
      render: (c) => `<span style="font-family: monospace; font-size: 0.78rem;">${c.id}</span>`
    },
    {
      header: 'ترتیب / صفحه',
      render: (c) => `<span>ترتیب: ${formatNum(c.chunkOrder ?? c.chunk_order ?? 0)} | ص ${formatNum(c.pageNumber || c.page_number || '—')}</span>`
    },
    {
      header: 'پیش‌نمایش متن',
      render: (c) => {
        const text = c.fullText || c.full_text || c.summary || '';
        return `<div style="max-width: 380px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${text}</div>`;
      }
    },
    {
      header: 'وضعیت پردازش',
      render: (c) => (c.isProcessed ?? c.is_processed)
        ? `<span class="badge badge-success">ایندکس شده ✓</span>`
        : `<span class="badge badge-warning">در حال پردازش</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (c, idx) => `
        <button class="btn btn-outline btn-sm btn-view-chunk" data-chunk-idx="${idx}">
          🔍 متن کامل و مفاهیم
        </button>
      `
    }
  ];

  async function fetchChunks() {
    renderTable({
      container: container.querySelector('#chunks-table-container'),
      columns: chunkColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/chunks', {
        page: chunksState.page,
        pageSize: chunksState.pageSize,
        search: chunksState.search
      });
      chunksState.data = res.data || [];
      chunksState.meta = res.meta;

      renderTable({
        container: container.querySelector('#chunks-table-container'),
        columns: chunkColumns,
        data: chunksState.data,
        meta: chunksState.meta,
        currentPage: chunksState.page,
        pageSize: chunksState.pageSize,
        emptyMessage: 'چانکی یافت نشد.',
        onPageChange: (newPage) => {
          chunksState.page = newPage;
          fetchChunks();
        },
        onPageSizeChange: (newSize) => {
          chunksState.pageSize = newSize;
          chunksState.page = 1;
          fetchChunks();
        }
      });

      container.querySelectorAll('.btn-view-chunk').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = Number(btn.getAttribute('data-chunk-idx'));
          const c = chunksState.data[idx];
          if (!c) return;

          const concepts = c.coreConcepts || c.core_concepts || [];
          const questions = c.hypotheticalQuestions || c.hypothetical_questions || [];

          Drawer.open({
            title: `چانک دانش: ${c.id}`,
            subtitle: `کتاب: ${c.bookId || c.book_id} | صفحه: ${c.pageNumber || c.page_number || '—'}`,
            contentHtml: `
              <div class="detail-section">
                <div class="detail-section-title">📄 متن کامل چانک معنایی</div>
                <div style="background: white; border: 1px solid var(--border-color); border-radius: 6px; padding: 1rem; line-height: 1.8; font-size: 0.9rem; max-height: 250px; overflow-y: auto;">
                  ${c.fullText || c.full_text || 'متنی موجود نیست.'}
                </div>
              </div>

              ${c.summary ? `
                <div class="detail-section">
                  <div class="detail-section-title">💡 چکیده و عصاره</div>
                  <div style="font-size: 0.85rem; line-height: 1.6; color: var(--text-secondary);">${c.summary}</div>
                </div>
              ` : ''}

              <div class="detail-section">
                <div class="detail-section-title">🏷️ مفاهیم کلیدی (Core Concepts)</div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                  ${concepts.length ? concepts.map(x => `<span class="badge badge-purple">${x}</span>`).join('') : '<span style="color: var(--text-muted);">مفهومی استخراج نشده</span>'}
                </div>
              </div>

              <div class="detail-section">
                <div class="detail-section-title">❓ سوالات فرضی مرتبط (Hypothetical Questions)</div>
                <ul style="padding-right: 1.25rem; font-size: 0.85rem; color: var(--text-secondary);">
                  ${questions.length ? questions.map(q => `<li style="margin-bottom: 0.35rem;">${q}</li>`).join('') : '<li>سوالی ثبت نشده است.</li>'}
                </ul>
              </div>
            `,
            footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
          });
        });
      });
    } catch (err) {
      container.querySelector('#chunks-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت چانک‌ها: ${err.message}</div></div>
      `;
    }
  }

  // Categories
  async function fetchCategories() {
    renderTable({
      container: container.querySelector('#cats-table-container'),
      columns: [
        { header: 'شناسه', render: (c) => `<span style="font-family: monospace;">${c.id}</span>` },
        { header: 'عنوان دسته‌بندی', field: 'title' },
        { header: 'آیکون', render: (c) => c.iconName || c.icon_name || '📚' },
        { header: 'ترتیب نمایش', render: (c) => formatNum(c.orderIndex ?? c.order_index ?? 0) },
        {
          header: 'عملیات',
          render: (c) => `
            <button class="btn btn-sm btn-outline btn-delete-cat" data-id="${c.id}" data-title="${c.title}" style="color: var(--danger); border-color: var(--danger); padding: 0.2rem 0.5rem;" title="حذف دسته‌بندی">
              🗑️
            </button>
          `
        }
      ],
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/categories');
      catsState.data = res.data || [];
      renderTable({
        container: container.querySelector('#cats-table-container'),
        columns: [
          { header: 'شناسه', render: (c) => `<span style="font-family: monospace;">${c.id}</span>` },
          { header: 'عنوان دسته‌بندی', field: 'title' },
          { header: 'سطح و والد', render: (c) => (c.parentId || c.parent_id) ? `<span class="badge badge-warning" style="font-size: 0.75rem;">↳ زیرمجموعه (${c.parentId || c.parent_id})</span>` : `<span class="badge badge-success" style="font-size: 0.75rem;">📁 دسته‌بندی اصلی</span>` },
          { header: 'آیکون', render: (c) => c.iconName || c.icon_name || '📚' },
          { header: 'ترتیب نمایش', render: (c) => formatNum(c.orderIndex ?? c.order_index ?? 0) },
          {
            header: 'عملیات',
            render: (c) => `
              <button class="btn btn-sm btn-outline btn-delete-cat" data-id="${c.id}" data-title="${c.title}" style="color: var(--danger); border-color: var(--danger); padding: 0.2rem 0.5rem;" title="حذف دسته‌بندی">
                🗑️
              </button>
            `
          }
        ],
        data: catsState.data,
        emptyMessage: 'دسته‌بندی یافت نشد.'
      });
    } catch (err) {
      container.querySelector('#cats-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // Posters
  let postersState = { data: [] };
  async function fetchPosters() {
    renderTable({
      container: container.querySelector('#posters-table-container'),
      columns: [
        { header: 'شناسه', render: (p) => `<span style="font-family: monospace;">${p.id}</span>` },
        { header: 'عنوان بنر / مجموعه', field: 'title' },
        { header: 'زیرعنوان / برچسب', render: (p) => p.subtitle || '—' },
        { header: 'تصویر / آیکون', render: (p) => {
          const img = p.imageUrl || p.image_url;
          if (!img) return '—';
          if (img.startsWith('http') || img.startsWith('/')) {
            return `<img src="${img}" style="width: 48px; height: 30px; object-fit: cover; border-radius: 4px;" alt="poster">`;
          }
          return `<span class="badge badge-info" style="font-family: monospace;">${img}</span>`;
        }},
        { header: 'کتاب یا دسته‌بندی مقصد', render: (p) => (p.targetBookId || p.target_book_id) ? `<span class="badge badge-info">${p.targetBookId || p.target_book_id}</span>` : 'عمومی' },
        { header: 'ترتیب', render: (p) => formatNum(p.orderIndex ?? p.order_index ?? 0) },
        {
          header: 'عملیات',
          render: (p) => `
            <button class="btn btn-sm btn-outline btn-delete-poster" data-id="${p.id}" data-title="${p.title}" style="color: var(--danger); border-color: var(--danger); padding: 0.2rem 0.5rem;" title="حذف">
              🗑️
            </button>
          `
        }
      ],
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/posters');
      postersState.data = res.data || [];
      renderTable({
        container: container.querySelector('#posters-table-container'),
        columns: [
          { header: 'شناسه', render: (p) => `<span style="font-family: monospace;">${p.id}</span>` },
          { header: 'عنوان بنر / مجموعه', field: 'title' },
          { header: 'زیرعنوان / برچسب', render: (p) => p.subtitle || '—' },
          { header: 'تصویر / آیکون', render: (p) => {
            const img = p.imageUrl || p.image_url;
            if (!img) return '—';
            if (img.startsWith('http') || img.startsWith('/')) {
              return `<img src="${img}" style="width: 48px; height: 30px; object-fit: cover; border-radius: 4px;" alt="poster">`;
            }
            return `<span class="badge badge-info" style="font-family: monospace;">${img}</span>`;
          }},
          { header: 'کتاب یا دسته‌بندی مقصد', render: (p) => (p.targetBookId || p.target_book_id) ? `<span class="badge badge-info">${p.targetBookId || p.target_book_id}</span>` : 'عمومی' },
          { header: 'ترتیب', render: (p) => formatNum(p.orderIndex ?? p.order_index ?? 0) },
          {
            header: 'عملیات',
            render: (p) => `
              <button class="btn btn-sm btn-outline btn-delete-poster" data-id="${p.id}" data-title="${p.title}" style="color: var(--danger); border-color: var(--danger); padding: 0.2rem 0.5rem;" title="حذف">
                🗑️
              </button>
            `
          }
        ],
        data: postersState.data,
        emptyMessage: 'پوستر یا مجموعه ویترینی یافت نشد.'
      });
    } catch (err) {
      container.querySelector('#posters-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت اطلاعات: ${err.message}</div></div>
      `;
    }
  }

  // Categories & Posters Refresh Handlers
  container.querySelector('#btn-refresh-cats')?.addEventListener('click', fetchCategories);
  container.querySelector('#btn-refresh-posters')?.addEventListener('click', fetchPosters);

  // Add Category Handler
  container.querySelector('#btn-add-cat')?.addEventListener('click', () => {
    Drawer.open({
      title: '➕ افزودن دسته‌بندی جدید کتابخانه',
      subtitle: 'دسته‌بندی موضوعی کتب جهت پژوهش تقریبی و فریقین',
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: 0.85rem; font-size: 0.85rem;">
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">دسته‌بندی والد (اختیاری):</label>
            <select id="drawer-cat-parent" class="search-input" style="width: 100%;">
              <option value="">-- بدون والد (دسته‌بندی اصلی/ریشه) --</option>
              ${catsState.data.filter(c => !c.parentId && !c.parent_id).map(c => `<option value="${c.id}">${c.title}</option>`).join('')}
            </select>
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">عنوان دسته‌بندی:</label>
            <input id="drawer-cat-title" type="text" class="search-input" style="width: 100%;" placeholder="مثال: فقه و احکام مقارن">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">نام آیکون (Material Symbols):</label>
            <input id="drawer-cat-icon" type="text" class="search-input" style="width: 100%;" value="menu_book" placeholder="menu_book, gavel, auto_stories, etc.">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">ترتیب نمایش:</label>
            <input id="drawer-cat-order" type="number" class="search-input" style="width: 100%;" value="${catsState.data.length + 1}">
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button id="btn-cancel-cat" class="btn btn-secondary btn-sm">انصراف</button>
          <button id="btn-submit-cat" class="btn btn-primary btn-sm">ذخیره دسته‌بندی</button>
        </div>
      `
    });

    document.getElementById('btn-cancel-cat')?.addEventListener('click', () => Drawer.close());
    document.getElementById('btn-submit-cat')?.addEventListener('click', async () => {
      const title = document.getElementById('drawer-cat-title').value.trim();
      const iconName = document.getElementById('drawer-cat-icon').value.trim() || 'menu_book';
      const orderIndex = parseInt(document.getElementById('drawer-cat-order').value) || 0;
      const parentId = document.getElementById('drawer-cat-parent')?.value.trim() || null;

      if (!title) {
        Toast.error('عنوان دسته‌بندی الزامی است.');
        return;
      }

      try {
        await ApiClient.post('/library/categories', { title, iconName, orderIndex, parentId });
        Toast.success(`دسته‌بندی '${title}' با موفقیت ایجاد شد.`);
        Drawer.close();
        fetchCategories();
      } catch (err) {
        Toast.error(`خطا در ایجاد دسته‌بندی: ${err.message}`);
      }
    });
  });

  // Delegate Delete Category
  container.querySelector('#cats-table-container')?.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-delete-cat');
    if (!btn) return;
    const catId = btn.dataset.id;
    const catTitle = btn.dataset.title || 'دسته‌بندی';
    if (!confirm(`آیا از حذف دسته‌بندی '${catTitle}' اطمینان دارید؟`)) return;

    try {
      await ApiClient.delete('/library/categories/' + catId);
      Toast.success(`دسته‌بندی '${catTitle}' حذف شد.`);
      fetchCategories();
    } catch (err) {
      Toast.error(`خطا در حذف دسته‌بندی: ${err.message}`);
    }
  });

  // Add Poster Handler
  container.querySelector('#btn-add-poster')?.addEventListener('click', () => {
    Drawer.open({
      title: '➕ ایجاد پوستر یا کارت مجموعه ویترین',
      subtitle: 'مدیریت بنرهای اسلایدر بالای ویترین و کارت‌های افقی مجموعه‌های ویژه (فقه، حدیث، تفسیر، اخلاق)',
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: 0.85rem; font-size: 0.85rem;">
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">عنوان بنر یا کارت مجموعه:</label>
            <input id="drawer-poster-title" type="text" class="search-input" style="width: 100%;" placeholder="مثال: پربازدیدترین آثار فقهی / همایش وحدت">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">زیرعنوان یا برچسب کوتاه:</label>
            <input id="drawer-poster-subtitle" type="text" class="search-input" style="width: 100%;" placeholder="مثال: مقایسه احکام و ادله استنباط فریقین">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">آدرس تصویر یا نماد آیکون (مثال: gavel, format_quote, menu_book یا URL):</label>
            <input id="drawer-poster-img" type="text" class="search-input" style="width: 100%;" placeholder="gavel یا https://cdn.ettehad.app/posters/unity.jpg">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">شناسه کتاب یا دسته‌بندی مقصد (اختیاری):</label>
            <input id="drawer-poster-book" type="text" class="search-input" style="width: 100%;" placeholder="مثال: fiqh, hadith, tafsir یا book_nahj">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">ترتیب نمایش:</label>
            <input id="drawer-poster-order" type="number" class="search-input" style="width: 100%;" value="${postersState.data.length + 1}">
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button id="btn-cancel-poster" class="btn btn-secondary btn-sm">انصراف</button>
          <button id="btn-submit-poster" class="btn btn-primary btn-sm">ذخیره در ویترین</button>
        </div>
      `
    });

    document.getElementById('btn-cancel-poster')?.addEventListener('click', () => Drawer.close());
    document.getElementById('btn-submit-poster')?.addEventListener('click', async () => {
      const title = document.getElementById('drawer-poster-title').value.trim();
      const subtitle = document.getElementById('drawer-poster-subtitle').value.trim();
      const imageUrl = document.getElementById('drawer-poster-img').value.trim();
      const targetBookId = document.getElementById('drawer-poster-book').value.trim();
      const orderIndex = parseInt(document.getElementById('drawer-poster-order').value) || 0;

      if (!title) {
        Toast.error('عنوان پوستر الزامی است.');
        return;
      }

      try {
        await ApiClient.post('/library/posters', {
          title,
          subtitle,
          imageUrl: imageUrl || 'https://cdn.ettehad.app/library/posters/poster_unity.jpg',
          targetBookId: targetBookId || null,
          orderIndex
        });
        Toast.success(`پوستر '${title}' با موفقیت در ویترین ثبت شد.`);
        Drawer.close();
        fetchPosters();
      } catch (err) {
        Toast.error(`خطا در ثبت پوستر: ${err.message}`);
      }
    });
  });

  // Delegate Delete Poster
  container.querySelector('#posters-table-container')?.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-delete-poster');
    if (!btn) return;
    const pId = btn.dataset.id;
    const pTitle = btn.dataset.title || 'پوستر';
    if (!confirm(`آیا از حذف پوستر '${pTitle}' از ویترین اطمینان دارید؟`)) return;

    try {
      await ApiClient.delete('/library/posters/' + pId);
      Toast.success(`پوستر '${pTitle}' حذف شد.`);
      fetchPosters();
    } catch (err) {
      Toast.error(`خطا در حذف پوستر: ${err.message}`);
    }
  });

  // Add Book Quick Modal Handler
  container.querySelector('#btn-add-book')?.addEventListener('click', () => {
    Drawer.open({
      title: '➕ افزودن سریع کتاب به کتابخانه',
      subtitle: 'ثبت اطلاعات کتاب‌شناختی جدید در پایگاه داده کتابخانه',
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: 0.85rem; font-size: 0.85rem;">
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">عنوان کتاب:</label>
            <input id="drawer-book-title" type="text" class="search-input" style="width: 100%;" placeholder="مثال: تفسیر المیزان فی تفسیر القرآن">
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">نویسنده / مؤلف:</label>
              <input id="drawer-book-author" type="text" class="search-input" style="width: 100%;" placeholder="علامه طباطبایی">
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">مترجم (اختیاری):</label>
              <input id="drawer-book-translator" type="text" class="search-input" style="width: 100%;" placeholder="سید محمدباقر موسوی همدانی">
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">ناشر / انتشارات:</label>
              <input id="drawer-book-publisher" type="text" class="search-input" style="width: 100%;" placeholder="دفتر انتشارات اسلامی">
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">دسته‌بندی:</label>
              <select id="drawer-book-cat" class="search-input" style="width: 100%;">
                <option value="cat_quran">قرآن و تفسیر</option>
                <option value="cat_hadith">حدیث و کلام</option>
                <option value="cat_fiqh">فقه و احکام</option>
                <option value="cat_akhlaq">اخلاق و عرفان</option>
                <option value="cat_history">تاریخ و سیره</option>
              </select>
            </div>
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">آدرس تصویر جلد (URL):</label>
            <input id="drawer-book-cover" type="text" class="search-input" style="width: 100%;" placeholder="https://cdn.ettehad.app/covers/al-mizan.jpg">
          </div>
          <div>
            <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">چکیده و معرفی کتاب:</label>
            <textarea id="drawer-book-desc" class="search-input" style="width: 100%; height: 70px; resize: vertical;" placeholder="توضیحات درباره سبک تفسیر، رویکرد و اهمیت کتاب..."></textarea>
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button id="btn-cancel-book" class="btn btn-secondary btn-sm">انصراف</button>
          <button id="btn-submit-book" class="btn btn-primary btn-sm">ذخیره کتاب در کتابخانه</button>
        </div>
      `
    });

    document.getElementById('btn-cancel-book')?.addEventListener('click', () => Drawer.close());
    document.getElementById('btn-submit-book')?.addEventListener('click', async () => {
      const title = document.getElementById('drawer-book-title').value.trim();
      const author = document.getElementById('drawer-book-author').value.trim();
      const translator = document.getElementById('drawer-book-translator').value.trim();
      const publisher = document.getElementById('drawer-book-publisher').value.trim();
      const categoryId = document.getElementById('drawer-book-cat').value;
      const coverUrl = document.getElementById('drawer-book-cover').value.trim();
      const description = document.getElementById('drawer-book-desc').value.trim();

      if (!title || !author) {
        Toast.error('عنوان و نویسنده کتاب الزامی هستند.');
        return;
      }

      try {
        await ApiClient.post('/library/books', {
          title,
          author,
          translator: translator || null,
          publisher: publisher || 'دار الکتب الاسلامیة',
          categoryId,
          coverUrl: coverUrl || 'https://cdn.ettehad.app/books/covers/cover_default.jpg',
          description: description || 'کتاب جامع معارفی در خدمت پژوهشگران و عموم علاقه‌مندان علوم اسلامی.',
          isFeatured: true
        });
        Toast.success(`کتاب '${title}' با موفقیت به کتابخانه افزوده شد.`);
        Drawer.close();
        fetchBooks();
      } catch (err) {
        Toast.error(`خطا در ثبت کتاب: ${err.message}`);
      }
    });
  });

  // Stats
  async function fetchStats() {
    renderTable({
      container: container.querySelector('#stats-table-container'),
      columns: [
        { header: 'کاربر', render: (s) => s.userId || s.user_id },
        { header: 'شناسه کتاب', render: (s) => s.bookId || s.book_id },
        { header: 'درصد پیشرفت', render: (s) => `<span class="badge badge-success">${s.percentage || 0}٪</span>` },
        { header: 'آخرین مطالعه', render: (s) => formatDateTime(s.updatedAt || s.updated_at) }
      ],
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/reading-progress', {
        page: statsState.page,
        pageSize: statsState.pageSize
      });
      statsState.data = res.data || [];
      statsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#stats-table-container'),
        columns: [
          { header: 'کاربر', render: (s) => s.userId || s.user_id },
          { header: 'شناسه کتاب', render: (s) => s.bookId || s.book_id },
          { header: 'درصد پیشرفت', render: (s) => `<span class="badge badge-success">${s.percentage || 0}٪</span>` },
          { header: 'آخرین مطالعه', render: (s) => formatDateTime(s.updatedAt || s.updated_at) }
        ],
        data: statsState.data,
        meta: statsState.meta,
        currentPage: statsState.page,
        pageSize: statsState.pageSize,
        emptyMessage: 'آمار مطالعه‌ای ثبت نشده است.',
        onPageChange: (p) => { statsState.page = p; fetchStats(); },
        onPageSizeChange: (s) => { statsState.pageSize = s; statsState.page = 1; fetchStats(); }
      });
    } catch (err) {
      container.querySelector('#stats-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // --- RAG Ingestion & Evaluation Handlers ---
  const sampleHierarchicalBook = {
    title: "مبانی احکام و طهارت در فقه تطبیقی",
    author: "جمعی از پژوهشگران معارفی",
    category: "فقه و احکام",
    madhhab: "مذاهب اسلامی",
    language: "fa",
    tags: ["طهارت", "احکام", "فقه"],
    sections: [
      {
        majorTopic: "احکام طهارت و نجاسات",
        chapters: [
          {
            title: "فصل اول: احکام آب‌ها و مطهرات",
            chapterNumber: 1,
            subchapters: [
              {
                title: "آب قلیل و آب کثیر",
                chunks: [
                  {
                    textPersian: "آب مطلق بر دو قسم است: آب کثیر و آب قلیل. آب کثیر آبی است که به اندازه کرّ باشد، یعنی وزن آن دست‌کم سیصد و هشتاد و چهار کیلوگرم یا اندازه آن سه وجب و نیم در سه وجب و نیم در سه وجب و نیم باشد. آب کرّ با برخورد نجاست تا زمانی که رنگ، بو یا مزه آن تغییر نکرده باشد نجس نمی‌شود.",
                    textArabic: "الماء المطلق إما كثير كالكُرّ أو قليل. والكرّ لا ينجس بملاقاة النجاسة إلا إذا تغيّر أحد أوصافه الثلاثة.",
                    pageNumber: 12
                  },
                  {
                    textPersian: "آب قلیل آبی است که کمتر از کرّ باشد و از زمین نجوشد. آب قلیل به محض برخورد با نجاست نجس می‌شود، هرچند اوصاف سه‌گانه آن تغییر نکرده باشد. برای تطهیر شیء متنجس با آب قلیل، زوال عین نجاست و شستن به دفعات معین شرط است.",
                    textArabic: "الماء القليل ينجس بمجرد ملاقاة النجاسة وإن لم يتغيّر.",
                    pageNumber: 13
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  };

  // Sample JSON Button
  container.querySelector('#btn-load-sample-json')?.addEventListener('click', () => {
    container.querySelector('#ingest-json-input').value = JSON.stringify(sampleHierarchicalBook, null, 2);
    Toast.show('نمونه داده معارفی در کادر درج شد.', 'info');
  });

  let currentIngestData = null;
  let currentIngestChunks = [];

  function displayIngestExecutionResults(data) {
    if (!data) return;
    currentIngestData = data;
    currentIngestChunks = data.chunkRepresentations || [];

    const resultsPanel = container.querySelector('#ingest-results-container');
    if (!resultsPanel) return;
    resultsPanel.style.display = 'block';

    // Subtitle meta
    const title = data.title || data.filename || (data.books && data.books[0]?.title) || 'منبع ورودی';
    const chaptersCount = data.totalChapters || 0;
    const isSaved = Boolean(data.isSavedToDatabase);
    const chunksCount = isSaved ? (data.totalChunksIndexed || currentIngestChunks.length) : currentIngestChunks.length;
    const batchSize = data.batchSize || 5;
    const saveStatusLabel = isSaved ? 'ذخیره شده در دیتابیس ✓' : 'پیش‌نمایش موقت (عدم ذخیره در دیتابیس) ⏸';

    container.querySelector('#ingest-meta-subtitle').textContent =
      `منبع: «${title}» | فصول: ${formatNum(chaptersCount)} | چانک‌ها: ${formatNum(chunksCount)} | دسته (Batch): ${batchSize} | وضعیت: ${saveStatusLabel}`;

    // Ingest Status Alert Banner
    const alertContainer = container.querySelector('#ingest-status-alert-container');
    const llmErrors = data.llmErrors || [];
    const aiCount = data.aiSuccessCount ?? currentIngestChunks.filter(c => c.isAiGenerated !== false && !c.llmError).length;
    const fallbackCount = data.fallbackCount ?? currentIngestChunks.filter(c => c.isAiGenerated === false || c.llmError).length;

    if (!isSaved) {
      const errDetailsHtml = llmErrors.length > 0
        ? `<div style="background: rgba(0,0,0,0.06); border-radius: 6px; padding: 0.6rem 0.8rem; font-family: monospace; font-size: 0.78rem; color: var(--danger); direction: ltr; text-align: left; margin-top: 0.6rem; word-break: break-all;">
            <strong>پیام خطای اتصال هوش مصنوعی (LLM Connection Error):</strong><br>${llmErrors.map(e => `• ${e}`).join('<br>')}
           </div>`
        : '';

      alertContainer.innerHTML = `
        <div class="ingest-alert-banner alert-warning" style="border: 2px solid var(--warning); background: var(--warning-bg); border-radius: 8px; padding: 1.1rem; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);">
          <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 280px;">
              <div style="font-weight: 700; font-size: 1.05rem; color: var(--warning-text); display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                <span>⚠️</span> عدم برقراری ارتباط با مدل هوش مصنوعی (استفاده از الگوریتم جایگزین)
              </div>
              <div style="font-size: 0.85rem; color: var(--text-main); line-height: 1.6;">
                به دلیل عدم پاسخگویی یا بروز خطا در مدل هوش مصنوعی، سوالات و چکیده‌ها با الگوریتم پشتیبان تولید شدند (${formatNum(fallbackCount)} چانک).
                <br>
                <strong style="color: var(--danger-text);">جهت جلوگیری از آلودگی پایگاه دانش، داده‌ها به صورت خودکار در دیتابیس و پایگاه برداری (Qdrant) ذخیره نشدند.</strong>
                می‌توانید پیش‌نمایش چانک‌ها را در زیر بازبینی کنید و در صورت تمایل تایید دستی را صادر کنید یا تنظیمات مدل هوش مصنوعی را بازبینی نمایید.
              </div>
              ${errDetailsHtml}
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; min-width: 220px;">
              <button id="btn-confirm-save-db" class="btn btn-warning btn-sm" style="font-weight: 700; padding: 0.6rem 0.9rem; font-size: 0.84rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem;">
                <span>💾</span> تایید و ذخیره دستی در دیتابیس
              </button>
              <button id="btn-retest-llm" class="btn btn-secondary btn-sm" style="font-size: 0.78rem;">
                🔄 بررسی تنظیمات هوش مصنوعی
              </button>
            </div>
          </div>
        </div>
      `;

      // Attach confirmation listener
      alertContainer.querySelector('#btn-confirm-save-db')?.addEventListener('click', async () => {
        const btn = alertContainer.querySelector('#btn-confirm-save-db');
        btn.disabled = true;
        btn.textContent = '⏳ در حال ذخیره‌سازی در دیتابیس و Qdrant...';

        try {
          const payload = {
            bookData: currentIngestData.rawBookData || null,
            booksData: currentIngestData.booksData || null,
            batchSize: currentIngestData.batchSize || 5
          };
          const res = await ApiClient.post('/library/confirm-ingest', payload);
          Toast.show(res.meta?.message || 'داده‌ها با موفقیت در پایگاه داده و کیودرانت ثبت شدند.', 'success');

          currentIngestData.isSavedToDatabase = true;
          currentIngestData.needsConfirmation = false;
          currentIngestData.totalChunksIndexed = currentIngestChunks.length;

          // Update stage 4 to completed
          if (currentIngestData.stages && currentIngestData.stages[3]) {
            currentIngestData.stages[3].status = 'completed';
            currentIngestData.stages[3].title = 'بردارسازی چندوجهی و ثبت در Qdrant و SQL';
            currentIngestData.stages[3].details = `نمایه‌سازی ${currentIngestChunks.length} چانک با تایید دستی در دیتابیس و پایگاه برداری ذخیره شد.`;
          }

          displayIngestExecutionResults(currentIngestData);
          fetchBooks();
        } catch (err) {
          Toast.show('خطا در ذخیره‌سازی: ' + err.message, 'error');
          btn.disabled = false;
          btn.textContent = '💾 تایید و ذخیره دستی در دیتابیس';
        }
      });

      alertContainer.querySelector('#btn-retest-llm')?.addEventListener('click', () => {
        Toast.show('موتور هوش مصنوعی برای بخش کتابخانه فعال است. کلید API و تنظیمات شبکه سرور را بازبینی فرمایید.', 'info');
      });
    } else {
      alertContainer.innerHTML = `
        <div class="ingest-alert-banner alert-success" style="border: 1px solid var(--success-border); background: var(--success-bg); border-radius: 8px; padding: 0.85rem 1.1rem;">
          <div style="font-weight: 700; font-size: 0.95rem; color: var(--success-text); display: flex; align-items: center; gap: 0.5rem;">
            <span>🟢</span> پردازش موفق و ذخیره‌سازی کامل در پایگاه داده
          </div>
          <div style="font-size: 0.83rem; color: var(--text-main); margin-top: 0.25rem;">
            چانک‌های منبع با موفقیت تحلیل شده و در جداول SQL و پایگاه برداری Qdrant ذخیره شدند (${formatNum(chunksCount)} چانک).
          </div>
        </div>
      `;
    }

    // Stages Timeline
    const stagesContainer = container.querySelector('#ingest-stages-timeline');
    const stages = data.stages || [
      { step: 1, title: 'اعتبارسنجی ساختار و فراداده‌های منبع', status: 'completed', details: `عنوان: «${title}»` },
      { step: 2, title: 'تفکیک درختی فصول و قطعه‌بندی معنایی', status: 'completed', details: `فصول: ${chaptersCount} | قطعات: ${chunksCount}` },
      { step: 3, title: 'استخراج هوشمند بازنمایی و پرسش‌های فرضی', status: 'completed', details: `پردازش چندوجهی مفاهیم، سوالات و چکیده‌ها` },
      { step: 4, title: 'بردارسازی چندبعدی و ثبت پایگاه دانش', status: 'completed', details: `ثبت نهایی در Qdrant و جداول SQL` }
    ];

    stagesContainer.innerHTML = stages.map(st => {
      let badgeHtml = '<span class="stage-badge-completed">✓ انجام شد</span>';
      let cardClass = 'status-completed';
      if (st.status === 'warning') {
        badgeHtml = '<span class="stage-badge-warning">⚠️ خطای اتصال LLM</span>';
        cardClass = 'status-warning';
      } else if (st.status === 'paused') {
        badgeHtml = '<span class="stage-badge-paused">⏸ توقف ذخیره در دیتابیس</span>';
        cardClass = 'status-paused';
      }
      return `
        <div class="ingest-stage-card ${cardClass}">
          <div class="ingest-stage-header">
            <span class="ingest-stage-step-pill">گام ${st.step}</span>
            ${badgeHtml}
          </div>
          <div class="ingest-stage-title">${st.title}</div>
          <div class="ingest-stage-details">${st.details || ''}</div>
        </div>
      `;
    }).join('');

    // Populate Chapter Filter dropdown
    const chapterSelect = container.querySelector('#filter-ingest-chapter');
    const uniqueChapters = [...new Set(currentIngestChunks.map(c => c.chapter).filter(Boolean))];
    chapterSelect.innerHTML = '<option value="">همه فصول (' + currentIngestChunks.length + ' چانک)</option>' +
      uniqueChapters.map(ch => `<option value="${ch}">${ch}</option>`).join('');

    renderIngestChunksList();

    // Smooth scroll to results
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderIngestChunksList() {
    const listEl = container.querySelector('#ingest-chunks-list');
    const badgeEl = container.querySelector('#ingest-chunks-badge');
    const filterText = (container.querySelector('#filter-ingest-chunks')?.value || '').trim().toLowerCase();
    const filterChapter = container.querySelector('#filter-ingest-chapter')?.value || '';

    let filtered = currentIngestChunks.filter(c => {
      if (filterChapter && c.chapter !== filterChapter) return false;
      if (filterText) {
        const hay = `${c.chunkId} ${c.summary} ${(c.hypotheticalQuestions || []).join(' ')} ${(c.coreConcepts || []).join(' ')} ${(c.domainInsights || []).join(' ')} ${c.fullText}`.toLowerCase();
        if (!hay.includes(filterText)) return false;
      }
      return true;
    });

    if (badgeEl) {
      badgeEl.textContent = `${filtered.length} از ${currentIngestChunks.length} چانک`;
    }

    if (!filtered.length) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-muted); background: var(--bg-body); border-radius: 6px;">
          هیچ چانکی با معیارهای جستجو یا فیلتر جاری یافت نشد.
        </div>
      `;
      return;
    }

    listEl.innerHTML = filtered.map((c, idx) => {
      const isAi = (c.isAiGenerated !== false && !c.llmError);
      const aiBadge = isAi
        ? `<span class="badge badge-success" style="font-size: 0.72rem; font-weight: 600;">🟢 هوش مصنوعی</span>`
        : `<span class="badge badge-danger" title="${c.llmError || 'خطای اتصال به مدل هوش مصنوعی'}" style="font-size: 0.72rem; font-weight: 600;">⚠️ فال‌بک (عدم اتصال LLM)</span>`;

      const errorNotice = (!isAi && c.llmError)
        ? `<div style="background: rgba(239, 68, 68, 0.08); border-right: 3px solid var(--danger); padding: 0.4rem 0.7rem; font-size: 0.76rem; color: var(--danger-text); margin-bottom: 0.65rem; border-radius: 4px; direction: ltr; text-align: left; font-family: monospace; word-break: break-all;">
             <strong>Connection Error:</strong> ${c.llmError}
           </div>`
        : '';

      const questionsHtml = (c.hypotheticalQuestions && c.hypotheticalQuestions.length > 0)
        ? c.hypotheticalQuestions.map((q, qIdx) => `
            <div class="hypo-question-chip">
              <span class="hypo-q-index">${qIdx + 1}</span>
              <span class="hypo-q-text">${q}</span>
              <button class="btn-try-q" data-query="${encodeURIComponent(q)}" title="آزمایش این پرسش در ارزیابی آنی">🔍 تست</button>
            </div>
          `).join('')
        : '<span style="color: var(--text-muted); font-size: 0.8rem;">پرسش فرضی تولید نشده است.</span>';

      const conceptsHtml = (c.coreConcepts && c.coreConcepts.length > 0)
        ? c.coreConcepts.map(cp => `<span class="concept-tag"># ${cp}</span>`).join('')
        : '<span style="color: var(--text-muted); font-size: 0.8rem;">-</span>';

      const insightsHtml = (c.domainInsights && c.domainInsights.length > 0)
        ? `<ul class="insights-list">${c.domainInsights.map(ins => `<li>${ins}</li>`).join('')}</ul>`
        : '<span style="color: var(--text-muted); font-size: 0.8rem;">-</span>';

      return `
        <div class="chunk-repr-card" data-chunk-id="${c.chunkId}">
          <div class="chunk-repr-header">
            <div class="chunk-badges-group">
              <span class="badge badge-secondary" style="font-weight: 700;">چانک #${c.chunkOrder || idx + 1}</span>
              <code style="font-size: 0.75rem; background: var(--bg-surface); padding: 0.15rem 0.4rem; border-radius: 4px; border: 1px solid var(--border-color);">${c.chunkId}</code>
              ${aiBadge}
              <span class="badge badge-primary">${c.chapter || 'فصل کلی'}</span>
              ${c.subchapter ? `<span class="badge badge-outline" style="border: 1px solid var(--border-color);">${c.subchapter}</span>` : ''}
              ${c.pageNumber ? `<span class="badge badge-warning">صفحه ${c.pageNumber}</span>` : ''}
            </div>
            <div style="display: flex; gap: 0.4rem;">
              <button class="btn btn-secondary btn-sm btn-copy-chunk" data-chunk-idx="${idx}" style="font-size: 0.74rem; padding: 0.2rem 0.5rem;">📋 کپی JSON</button>
            </div>
          </div>

          ${errorNotice}

          <!-- Summary Box -->
          <div class="chunk-section-block">
            <span class="chunk-section-label">📌 چکیده فشرده معنایی (Summary - ۳۰ تا ۵۰ کلمه):</span>
            <div class="chunk-summary-box">${c.summary || '<span style="color: var(--text-muted);">بدون خلاصه</span>'}</div>
          </div>

          <!-- Hypothetical Questions -->
          <div class="chunk-section-block">
            <span class="chunk-section-label">❓ پرسش‌های فرضی استخراج‌شده برای جستجوی معنایی (Hypothetical Questions):</span>
            <div class="questions-chips-container">${questionsHtml}</div>
          </div>

          <!-- Core Concepts & Insights Grid -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.85rem;">
            <div>
              <span class="chunk-section-label">🏷️ مفاهیم کلیدی (Core Concepts):</span>
              <div class="concepts-tags-container">${conceptsHtml}</div>
            </div>
            <div>
              <span class="chunk-section-label">💡 احکام، حکمت‌ها و بینش‌ها (Domain Insights):</span>
              ${insightsHtml}
            </div>
          </div>

          <!-- Primary Text Preview -->
          <details class="chunk-text-preview-details">
            <summary>📖 مشاهده متن کامل چانک (فارسی / استنادی)</summary>
            <div class="chunk-text-preview-content">
              <div style="margin-bottom: 0.4rem;"><strong>متن اصلی:</strong> ${c.fullText || ''}</div>
              ${c.textArabic ? `<div style="margin-top: 0.4rem; color: var(--primary); font-family: 'Amiri', serif; font-size: 0.88rem; direction: rtl;"><strong>متن عربی / استنادی:</strong> ${c.textArabic}</div>` : ''}
            </div>
          </details>
        </div>
      `;
    }).join('');

    // Attach listeners for testing query in live query tester
    listEl.querySelectorAll('.btn-try-q').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const rawQ = decodeURIComponent(btn.getAttribute('data-query') || '');
        if (!rawQ) return;
        const testInput = container.querySelector('#test-query-input');
        if (testInput) {
          testInput.value = rawQ;
          testInput.scrollIntoView({ behavior: 'smooth' });
          testInput.focus();
          Toast.show(`پرسش «${rawQ.slice(0, 30)}...» به آزمایشگر آنی منتقل شد. در حال ارسال...`, 'info');
          container.querySelector('#btn-run-test-query')?.click();
        }
      });
    });

    // Attach copy chunk JSON
    listEl.querySelectorAll('.btn-copy-chunk').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.getAttribute('data-chunk-idx'), 10);
        const chunk = filtered[idx];
        if (chunk) {
          navigator.clipboard.writeText(JSON.stringify(chunk, null, 2));
          Toast.show(`اطلاعات چانک ${chunk.chunkId} در کلیپ‌بورد کپی شد.`, 'success');
        }
      });
    });
  }

  // Filter events
  container.querySelector('#filter-ingest-chunks')?.addEventListener('input', () => renderIngestChunksList());
  container.querySelector('#filter-ingest-chapter')?.addEventListener('change', () => renderIngestChunksList());

  // Copy All Ingestion JSON
  container.querySelector('#btn-copy-ingest-json')?.addEventListener('click', () => {
    if (!currentIngestData) {
      Toast.show('داده‌ای برای کپی وجود ندارد.', 'warning');
      return;
    }
    navigator.clipboard.writeText(JSON.stringify(currentIngestData, null, 2));
    Toast.show('کل ساختار خروجی نمایه‌سازی و بازنمایی‌ها کپی شد.', 'success');
  });

  // Close results panel
  container.querySelector('#btn-close-ingest-results')?.addEventListener('click', () => {
    const resultsPanel = container.querySelector('#ingest-results-container');
    if (resultsPanel) resultsPanel.style.display = 'none';
  });

  // File Upload Ingestion
  container.querySelector('#btn-upload-file-ingest')?.addEventListener('click', async () => {
    const fileInput = container.querySelector('#ingest-file-input');
    const file = fileInput?.files?.[0];
    if (!file) {
      Toast.show('لطفاً ابتدا یک فایل با پسوند .json یا .jsonl انتخاب نمایید.', 'error');
      return;
    }

    const btn = container.querySelector('#btn-upload-file-ingest');
    btn.disabled = true;
    btn.textContent = '⏳ در حال آپلود و نمایه‌سازی هوشمند...';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await ApiClient.upload('/library/upload-json', formData);
      const isSaved = Boolean(res.data?.isSavedToDatabase);
      const totalIndexed = res.data?.totalChunksIndexed || 0;
      const count = res.data?.booksProcessed || 1;

      if (isSaved) {
        const msg = res.meta?.message || `فایل با موفقیت پردازش و ذخیره شد (${count} کتاب، ${totalIndexed} چانک).`;
        Toast.show(msg, 'success');
      } else {
        Toast.show(res.meta?.message || 'پردازش پایان یافت اما به دلیل عدم اتصال هوش مصنوعی در دیتابیس ذخیره نشد. پیش‌نمایش را بررسی کنید.', 'warning');
      }
      fileInput.value = '';

      // Display live execution stages and extracted chunk representations
      displayIngestExecutionResults(res.data);

      if (isSaved) {
        // Find first book ID to auto-select in benchmark
        let newBookId = null;
        if (res.data?.books && Array.isArray(res.data.books) && res.data.books.length > 0) {
          newBookId = res.data.books[0].bookId;
        } else if (res.data?.bookId) {
          newBookId = res.data.bookId;
        }

        await populateBenchmarkBooks(newBookId);
        fetchBooks();
      }
    } catch (err) {
      Toast.show('خطا در آپلود فایل: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '📤 آپلود فایل و نمایه‌سازی';
    }
  });

  // Submit Ingestion from Text
  container.querySelector('#btn-submit-ingest')?.addEventListener('click', async () => {
    const rawJson = container.querySelector('#ingest-json-input').value.trim();
    if (!rawJson) {
      Toast.show('لطفاً اطلاعات JSON کتاب را وارد کنید.', 'error');
      return;
    }

    let parsed;
    try {
      parsed = JSON.parse(rawJson);
    } catch (e) {
      Toast.show('قالب JSON نامعتبر است: ' + e.message, 'error');
      return;
    }

    const btn = container.querySelector('#btn-submit-ingest');
    btn.disabled = true;
    btn.textContent = '⏳ در حال چانک‌بندی و نمایه‌سازی هوشمند...';

    try {
      const res = await ApiClient.post('/library/ingest', parsed);
      const isSaved = Boolean(res.data?.isSavedToDatabase);
      if (isSaved) {
        Toast.show(res.meta?.message || 'کتاب با موفقیت وارد و نمایه‌سازی شد.', 'success');
      } else {
        Toast.show(res.meta?.message || 'پردازش پایان یافت اما به دلیل عدم اتصال هوش مصنوعی ذخیره نشد.', 'warning');
      }
      container.querySelector('#ingest-json-input').value = '';

      // Display live execution stages and extracted chunk representations
      displayIngestExecutionResults(res.data);

      if (isSaved) {
        const newBookId = res.data?.bookId || null;
        populateBenchmarkBooks(newBookId);
        fetchBooks();
      }
    } catch (err) {
      Toast.show('خطا در بارگذاری داده: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ بارگذاری از متن کادر';
    }
  });

  // Populate Books Dropdown for Benchmark
  async function populateBenchmarkBooks(selectedBookId = null) {
    try {
      const res = await ApiClient.get('/library/books', { pageSize: 50 });
      const select = container.querySelector('#benchmark-book-select');
      if (!select) return;
      const currentVal = selectedBookId || select.value;
      select.innerHTML = '<option value="">همه کتب و چانک‌های سامانه</option>';
      (res.data || []).forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${b.title} (${b.author || 'ناشناس'})`;
        select.appendChild(opt);
      });
      if (currentVal) select.value = currentVal;
    } catch (_) {}
  }

  // Run Benchmark Handler
  container.querySelector('#btn-run-benchmark')?.addEventListener('click', async () => {
    const bookId = container.querySelector('#benchmark-book-select').value || null;
    const rawQueries = container.querySelector('#benchmark-custom-queries').value.trim();
    const customQueries = rawQueries ? rawQueries.split('\n').map(q => q.trim()).filter(Boolean) : null;

    const btn = container.querySelector('#btn-run-benchmark');
    btn.disabled = true;
    btn.textContent = '⏳ در حال اجرای آزمون و سنجش تناسب...';

    try {
      const res = await ApiClient.post('/library/evaluation/benchmark', {
        bookId,
        customQueries,
        limitQueries: 15
      });

      const data = res.data;
      displayBenchmarkResults(data);
      Toast.show('آزمون ارزیابی با موفقیت به پایان رسید.', 'success');
      fetchEvalReports();
    } catch (err) {
      Toast.show('خطا در اجرای بنچ‌مارک: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '🚀 اجرای آزمون ارزیابی';
    }
  });

  function displayBenchmarkResults(data) {
    const cardWrap = container.querySelector('#benchmark-scorecard-container');
    if (!cardWrap) return;
    cardWrap.style.display = 'block';

    // Metrics
    container.querySelector('#metric-avg-relevance').textContent = `${data.avgRelevanceScore || 0}٪`;
    container.querySelector('#metric-hit-rate').textContent = `${data.hitRateAt3 || 0}٪`;
    container.querySelector('#metric-passing-rate').textContent = `${data.passingRate || 0}٪`;

    const statusEl = container.querySelector('#metric-overall-status');
    const isPassed = data.status === 'PASSED';
    statusEl.textContent = isPassed ? 'قبول (تایید کیفیت)' : (data.status === 'NEEDS_IMPROVEMENT' ? 'نیاز به بهینه‌سازی' : 'رد (کیفیت ناکافی)');
    statusEl.style.color = isPassed ? 'var(--success)' : (data.status === 'NEEDS_IMPROVEMENT' ? 'var(--warning)' : 'var(--danger)');

    // Query Results Table
    const queryResults = data.details?.query_results || [];
    renderTable({
      container: container.querySelector('#benchmark-results-table'),
      columns: [
        { header: 'پرسش آزمون', render: (q) => `<span style="font-weight: 500;">${q.query}</span>` },
        {
          header: 'امتیاز تناسب',
          render: (q) => {
            const score = q.top_score || 0;
            const badgeClass = score >= 65 ? 'badge-success' : (score >= 45 ? 'badge-warning' : 'badge-danger');
            return `<span class="badge ${badgeClass}">${score}٪</span>`;
          }
        },
        {
          header: 'وضعیت در ۳ نتیجه',
          render: (q) => q.hit_at_3 ? '<span class="badge badge-success">موفق (Hit@3)</span>' : '<span class="badge badge-danger">ناموفق</span>'
        },
        {
          header: 'تعداد چانک بازیافتی',
          render: (q) => formatNum(q.retrieved_count || 0)
        }
      ],
      data: queryResults,
      emptyMessage: 'نتیجه‌ای برای نمایش موجود نیست.'
    });
  }

  // Live Query Tester Handler
  container.querySelector('#btn-run-test-query')?.addEventListener('click', async () => {
    const query = container.querySelector('#test-query-input').value.trim();
    if (!query) {
      Toast.show('لطفاً متن پرسش را وارد کنید.', 'error');
      return;
    }

    const btn = container.querySelector('#btn-run-test-query');
    btn.disabled = true;
    btn.textContent = '⏳ در حال ارزیابی...';

    const resultBox = container.querySelector('#test-query-result-box');
    resultBox.style.display = 'block';
    resultBox.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">در حال جستجو در وکتورها و ارزیابی تطابق معنایی با مدل...</div>';

    try {
      const res = await ApiClient.post('/library/evaluation/test-query', { query });
      const d = res.data;

      let chunksHtml = (d.contexts || []).map((c, i) => {
        const badgeColor = c.is_passed ? 'var(--success)' : (c.relevance_score >= 45 ? 'var(--warning)' : 'var(--danger)');
        return `
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; margin-top: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.35rem;">
              <div style="display: flex; align-items: center; gap: 0.35rem;">
                <span style="font-weight: 600; font-size: 0.85rem;">[${i + 1}] ${c.title || c.bookTitle || 'منبع دانشی'}</span>
                ${c.chapterTitle ? `<span class="badge" style="background: var(--bg-surface); border: 1px solid var(--border-color); font-size: 0.72rem;">📖 ${c.chapterTitle}</span>` : ''}
                ${c.pageNumber ? `<span class="badge" style="background: var(--bg-surface); border: 1px solid var(--border-color); font-size: 0.72rem;">صفحه ${c.pageNumber}</span>` : ''}
              </div>
              <span style="font-weight: 700; color: ${badgeColor}; font-size: 0.85rem;">امتیاز تناسب: ${c.relevance_score}٪ (${c.verdict})</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-main); margin-bottom: 0.4rem; line-height: 1.5;">${c.excerpt}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); display: flex; gap: 1rem; border-top: 1px dashed var(--border-subtle); padding-top: 0.35rem;">
              <span>تشابه برداری: ${(c.vector_similarity * 100).toFixed(1)}٪</span>
              <span>قضاوت معنایی: ${(c.semantic_score * 100).toFixed(1)}٪</span>
              <span>پوشش کلمات کلیدی: ${(c.keyword_coverage * 100).toFixed(0)}٪</span>
            </div>
            ${c.reasoning ? `<div style="font-size: 0.75rem; color: var(--primary); margin-top: 0.25rem;">💡 استدلال: ${c.reasoning}</div>` : ''}
          </div>
        `;
      }).join('');

      resultBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
          <div>
            <strong>پرسش:</strong> "${d.query}"
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <span class="badge ${d.isSufficient ? 'badge-success' : 'badge-danger'}">
              ${d.isSufficient ? 'کفایت و تطابق تایید شد' : 'عدم تطابق یا فقر منبع'}
            </span>
            <span style="font-weight: 700; font-size: 0.95rem;">نمره برتر: ${d.topScore}%</span>
          </div>
        </div>
        <div>
          <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.25rem;">منابع بازیابی‌شده و نمرات تفکیکی:</div>
          ${chunksHtml || '<div style="color: var(--danger); font-size: 0.85rem;">هیچ چانکی برای این پرسش یافت نشد.</div>'}
        </div>
      `;
    } catch (err) {
      resultBox.innerHTML = `<div style="color: var(--danger); font-size: 0.85rem;">خطا در ارزیابی پرسش: ${err.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = 'سنجش تناسب بازیابی';
    }
  });

  // Fetch Reports History
  async function fetchEvalReports() {
    populateBenchmarkBooks();

    renderTable({
      container: container.querySelector('#eval-reports-table-container'),
      columns: [
        { header: 'عنوان گزارش', render: (r) => `<span style="font-weight: 500;">${r.title}</span>` },
        { header: 'تعداد پرسش‌ها', render: (r) => formatNum(r.totalQueries || 0) },
        {
          header: 'میانگین تناسب',
          render: (r) => {
            const score = r.avgRelevanceScore || 0;
            const badgeClass = score >= 65 ? 'badge-success' : (score >= 45 ? 'badge-warning' : 'badge-danger');
            return `<span class="badge ${badgeClass}">${score}٪</span>`;
          }
        },
        { header: 'نرخ Hit@3', render: (r) => `<span class="badge badge-info">${r.hitRateAt3 || 0}٪</span>` },
        { header: 'درصد قبولی', render: (r) => `${r.passingRate || 0}٪` },
        {
          header: 'وضعیت',
          render: (r) => {
            const badgeClass = r.status === 'PASSED' ? 'badge-success' : (r.status === 'NEEDS_IMPROVEMENT' ? 'badge-warning' : 'badge-danger');
            const label = r.status === 'PASSED' ? 'قبول' : (r.status === 'NEEDS_IMPROVEMENT' ? 'بهینه‌سازی' : 'رد');
            return `<span class="badge ${badgeClass}">${label}</span>`;
          }
        },
        { header: 'تاریخ ارزیابی', render: (r) => formatDateTime(r.createdAt) },
        {
          header: 'اقدام',
          render: (r) => `<button class="btn btn-secondary btn-sm btn-view-report" data-id="${r.id}">جزئیات</button>`
        }
      ],
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/library/evaluation/reports', {
        page: evalReportsState.page,
        pageSize: evalReportsState.pageSize
      });
      evalReportsState.data = res.data || [];
      evalReportsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#eval-reports-table-container'),
        columns: [
          { header: 'عنوان گزارش', render: (r) => `<span style="font-weight: 500;">${r.title}</span>` },
          { header: 'تعداد پرسش‌ها', render: (r) => formatNum(r.totalQueries || 0) },
          {
            header: 'میانگین تناسب',
            render: (r) => {
              const score = r.avgRelevanceScore || 0;
              const badgeClass = score >= 65 ? 'badge-success' : (score >= 45 ? 'badge-warning' : 'badge-danger');
              return `<span class="badge ${badgeClass}">${score}٪</span>`;
            }
          },
          { header: 'نرخ Hit@3', render: (r) => `<span class="badge badge-info">${r.hitRateAt3 || 0}٪</span>` },
          { header: 'درصد قبولی', render: (r) => `${r.passingRate || 0}٪` },
          {
            header: 'وضعیت',
            render: (r) => {
              const badgeClass = r.status === 'PASSED' ? 'badge-success' : (r.status === 'NEEDS_IMPROVEMENT' ? 'badge-warning' : 'badge-danger');
              const label = r.status === 'PASSED' ? 'قبول' : (r.status === 'NEEDS_IMPROVEMENT' ? 'بهینه‌سازی' : 'رد');
              return `<span class="badge ${badgeClass}">${label}</span>`;
            }
          },
          { header: 'تاریخ ارزیابی', render: (r) => formatDateTime(r.createdAt) },
          {
            header: 'اقدام',
            render: (r) => `<button class="btn btn-secondary btn-sm btn-view-report" data-id="${r.id}">جزئیات</button>`
          }
        ],
        data: evalReportsState.data,
        meta: evalReportsState.meta,
        currentPage: evalReportsState.page,
        pageSize: evalReportsState.pageSize,
        emptyMessage: 'هنوز گزارش ارزیابی ثبت نشده است. دکمه «اجرای بنچ‌مارک ارزیابی» را بزنید.',
        onPageChange: (p) => { evalReportsState.page = p; fetchEvalReports(); },
        onPageSizeChange: (s) => { evalReportsState.pageSize = s; evalReportsState.page = 1; fetchEvalReports(); }
      });

      // Bind Details Buttons
      container.querySelectorAll('.btn-view-report').forEach(btn => {
        btn.addEventListener('click', async () => {
          const repId = btn.dataset.id;
          try {
            const repRes = await ApiClient.get(`/library/evaluation/reports/${repId}`);
            openReportDrawer(repRes.data);
          } catch (err) {
            Toast.show('خطا در دریافت جزئیات: ' + err.message, 'error');
          }
        });
      });
    } catch (err) {
      container.querySelector('#eval-reports-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  function openReportDrawer(report) {
    const details = report.details || {};
    const weakQueries = details.weak_queries || [];
    const queryResults = details.query_results || [];

    let weakListHtml = weakQueries.map(w => `
      <div style="background: var(--danger-bg); border: 1px solid var(--danger-border); border-radius: 6px; padding: 0.75rem; margin-bottom: 0.5rem;">
        <div style="font-weight: 600; color: var(--danger-text); font-size: 0.85rem;">پرسش: "${w.query}"</div>
        <div style="font-size: 0.78rem; color: var(--danger-text); margin-top: 0.25rem;">امتیاز: ${w.top_score}% - ${w.diagnosis}</div>
      </div>
    `).join('');

    let queriesListHtml = queryResults.map((q, i) => `
      <div style="border-bottom: 1px solid var(--border-subtle); padding: 0.5rem 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem;">
          <span><strong>[${i + 1}]</strong> ${q.query}</span>
          <span class="badge ${q.top_score >= 65 ? 'badge-success' : 'badge-danger'}">${q.top_score}%</span>
        </div>
      </div>
    `).join('');

    Drawer.open({
      title: `📊 ${report.title}`,
      subtitle: `تاریخ: ${formatDateTime(report.createdAt)} | وضعیت: ${report.status}`,
      body: `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem;">
          <div style="background: var(--bg-body); padding: 0.75rem; border-radius: 6px;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">میانگین تناسب</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: var(--primary);">${report.avgRelevanceScore}%</div>
          </div>
          <div style="background: var(--bg-body); padding: 0.75rem; border-radius: 6px;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">نرخ موفقیت Hit@3</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: var(--info);">${report.hitRateAt3}%</div>
          </div>
        </div>

        ${weakQueries.length > 0 ? `
          <div style="margin-bottom: 1.25rem;">
            <h4 style="font-size: 0.9rem; color: var(--danger); margin-bottom: 0.5rem;">⚠️ پرسش‌های نیازمند بهینه‌سازی چانک (${weakQueries.length}):</h4>
            ${weakListHtml}
          </div>
        ` : '<div style="background: var(--success-bg); color: var(--success-text); padding: 0.5rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.82rem;">✓ همه پرسش‌های آزمون از حد نصاب قبولی ۶۵٪ عبور کردند.</div>'}

        <div>
          <h4 style="font-size: 0.9rem; margin-bottom: 0.5rem;">📋 ریز نتایج پرسش‌های آزمون (${queryResults.length}):</h4>
          <div style="max-height: 280px; overflow-y: auto;">
            ${queriesListHtml}
          </div>
        </div>
      `
    });
  }

  container.querySelector('#btn-refresh-eval-reports')?.addEventListener('click', fetchEvalReports);

  // -----------------------------------------------------------------
  // 7. Submissions & User Book Requests Management
  // -----------------------------------------------------------------
  const submissionColumns = [
    {
      header: 'کد رهگیری',
      render: (s) => `<code style="font-size: 0.75rem; font-weight: 700;">${s.tracking_code || s.trackingCode || (s.id ? s.id.substring(0, 10) : '—')}</code>`
    },
    {
      header: 'مشخصات کتاب',
      render: (s) => `
        <div>
          <div style="font-weight: 700;">${s.title || 'بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${s.author || 'نویسنده نامشخص'} ${s.publisher ? `• ${s.publisher}` : ''}</div>
        </div>
      `
    },
    {
      header: 'متقاضی',
      render: (s) => `
        <div>
          <div style="font-weight: 600;">${s.user_name || s.userName || 'کاربر مهمان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${s.user_contact || s.userContact || '—'}</div>
        </div>
      `
    },
    {
      header: 'نوع درخواست',
      render: (s) => (s.type === 'SUBMIT_NEW' || s.request_type === 'SUBMIT_NEW')
        ? `<span class="badge badge-purple">📤 ارسال کتاب جدید</span>`
        : `<span class="badge badge-info">🔍 درخواست کتاب ناموجود</span>`
    },
    {
      header: 'وضعیت',
      render: (s) => {
        const st = s.status || 'PENDING';
        if (st === 'APPROVED') return `<span class="badge badge-success">✓ تأیید شده</span>`;
        if (st === 'AVAILABLE') return `<span class="badge badge-primary">⭐ موجود شد</span>`;
        if (st === 'REJECTED') return `<span class="badge badge-danger">✕ رد شده</span>`;
        if (st === 'IN_REVIEW') return `<span class="badge badge-warning">⏳ در حال بررسی</span>`;
        return `<span class="badge badge-neutral">در انتظار بررسی</span>`;
      }
    },
    {
      header: 'تاریخ ثبت',
      render: (s) => `<span style="font-size: 0.75rem;">${formatDateTime(s.created_at || s.createdAt)}</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (s) => `
        <div style="display: flex; gap: 0.25rem; justify-content: flex-end;">
          ${s.status !== 'APPROVED' && s.status !== 'AVAILABLE' ? `
            <button class="btn btn-sm btn-primary btn-approve-sub" data-sub-id="${s.id}" title="تأیید درخواست">✓ تأیید</button>
          ` : ''}
          ${s.status !== 'REJECTED' ? `
            <button class="btn btn-sm btn-outline btn-reject-sub" data-sub-id="${s.id}" style="color: #ef4444;" title="رد درخواست">✕ رد</button>
          ` : ''}
          <button class="btn btn-sm btn-outline btn-delete-sub" data-sub-id="${s.id}" style="color: #64748b;" title="حذف">🗑️</button>
        </div>
      `
    }
  ];

  async function fetchSubmissions() {
    renderTable({
      container: container.querySelector('#submissions-table-container'),
      columns: submissionColumns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: submissionsState.page,
        limit: submissionsState.pageSize,
        q: submissionsState.search
      };
      if (submissionsState.status) {
        params.status = submissionsState.status;
      }

      const res = await ApiClient.get('/library/submissions', params);
      submissionsState.data = res.data || [];
      submissionsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#submissions-table-container'),
        columns: submissionColumns,
        data: submissionsState.data,
        meta: submissionsState.meta,
        currentPage: submissionsState.page,
        pageSize: submissionsState.pageSize,
        emptyMessage: 'هیچ درخواست یا کتاب ارسالی با فیلتر مشخص‌شده یافت نشد.',
        onPageChange: (newPage) => {
          submissionsState.page = newPage;
          fetchSubmissions();
        },
        onPageSizeChange: (newSize) => {
          submissionsState.pageSize = newSize;
          submissionsState.page = 1;
          fetchSubmissions();
        }
      });

      // Actions
      container.querySelectorAll('.btn-approve-sub').forEach(btn => {
        btn.addEventListener('click', async () => {
          const subId = btn.getAttribute('data-sub-id');
          await updateSubmissionStatus(subId, 'APPROVED');
        });
      });

      container.querySelectorAll('.btn-reject-sub').forEach(btn => {
        btn.addEventListener('click', async () => {
          const subId = btn.getAttribute('data-sub-id');
          const reason = prompt('دلیل رد درخواست (اختیاری):') || '';
          await updateSubmissionStatus(subId, 'REJECTED', reason);
        });
      });

      container.querySelectorAll('.btn-delete-sub').forEach(btn => {
        btn.addEventListener('click', async () => {
          const subId = btn.getAttribute('data-sub-id');
          if (!confirm('آیا از حذف این درخواست کتاب اطمینان دارید؟')) return;
          try {
            await ApiClient.delete(`/library/submissions/${subId}`);
            Toast.success('درخواست کتاب با موفقیت حذف شد.');
            fetchSubmissions();
          } catch (err) {
            console.error(err);
          }
        });
      });

    } catch (err) {
      container.querySelector('#submissions-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت درخواست‌های کتب: ${err.message}</div></div>
      `;
    }
  }

  async function updateSubmissionStatus(subId, status, adminNotes = '') {
    try {
      await ApiClient.put(`/library/submissions/${subId}/status`, { status, adminNotes });
      Toast.success(`وضعیت درخواست با موفقیت به روز شد.`);
      fetchSubmissions();
    } catch (err) {
      console.error(err);
    }
  }

  // Filter event listeners for Submissions
  let subSearchTimeout = null;
  container.querySelector('#submissions-search')?.addEventListener('input', (e) => {
    clearTimeout(subSearchTimeout);
    subSearchTimeout = setTimeout(() => {
      submissionsState.search = e.target.value.trim();
      submissionsState.page = 1;
      fetchSubmissions();
    }, 300);
  });

  container.querySelector('#submissions-filter-status')?.addEventListener('change', (e) => {
    submissionsState.status = e.target.value;
    submissionsState.page = 1;
    fetchSubmissions();
  });

  container.querySelector('#btn-refresh-submissions')?.addEventListener('click', fetchSubmissions);

  fetchBooks();
}

