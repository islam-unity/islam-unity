/**
 * View 3: Consultations & Scholars (مشاوره دینی و اساتید)
 * Consultation threads with tracking code, urgency badge, messages drawer, quick reply, and scholars list.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderConsultations(container) {
  let activeTab = 'threads'; // 'threads' | 'scholars'

  let threadState = {
    page: 1,
    pageSize: 10,
    search: '',
    status: '', // '', 'WAITING_SCHOLAR', 'OPEN', 'ANSWERED', 'CLOSED'
    isUrgent: null, // null, true, false
    data: [],
    meta: null
  };

  let scholarState = {
    page: 1,
    pageSize: 10,
    search: '',
    data: [],
    meta: null
  };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">💬 پاسخ‌کده و مشاوره فقهی</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-btn-threads" class="subtab-btn active">تریدهای مشاوره و سوالات</button>
          <button id="tab-btn-scholars" class="subtab-btn">فهرست مبلغان و اساتید</button>
          <button id="tab-btn-pending-scholars" class="subtab-btn" style="position: relative; display: inline-flex; align-items: center; gap: 0.35rem;">
            <span>درخواست‌های عضویت علما (در انتظار بررسی)</span>
            <span id="pending-badge" style="background: #ef4444; color: white; border-radius: 9999px; padding: 1px 7px; font-size: 11px; font-weight: bold; display: none;">0</span>
          </button>
        </div>

        <!-- Threads Section -->
        <div id="section-threads">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="thread-search" type="text" class="search-input" placeholder="جستجو بر اساس عنوان، موضوع یا کد رهگیری...">
              </div>

              <!-- Filter pills -->
              <div style="display: flex; gap: 0.35rem; align-items: center;">
                <button class="btn btn-sm btn-outline filter-pill active" data-filter="all">همه</button>
                <button class="btn btn-sm btn-outline filter-pill" data-filter="urgent" style="color: var(--danger);">🚨 فوری</button>
                <button class="btn btn-sm btn-outline filter-pill" data-filter="WAITING_SCHOLAR">در انتظار استاد</button>
                <button class="btn btn-sm btn-outline filter-pill" data-filter="OPEN">ترید باز</button>
                <button class="btn btn-sm btn-outline filter-pill" data-filter="ANSWERED">پاسخ داده شده</button>
              </div>
            </div>

            <div class="toolbar-group">
              <button id="btn-refresh-threads" class="btn btn-secondary btn-sm">
                ⟳ تازه‌سازی
              </button>
            </div>
          </div>

          <div id="threads-table-container"></div>
        </div>

        <!-- Scholars Section -->
        <div id="section-scholars" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="scholar-search" type="text" class="search-input" placeholder="جستجو بر اساس نام استاد یا شهر...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-add-scholar" class="btn btn-primary btn-sm">
                ➕ افزودن عالم دینی جدید
              </button>
              <button id="btn-refresh-scholars" class="btn btn-secondary btn-sm">
                ⟳ تازه‌سازی
              </button>
            </div>
          </div>

          <div id="scholars-table-container"></div>
        </div>

        <!-- Pending Scholars Section -->
        <div id="section-pending-scholars" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div style="font-size: 0.85rem; color: var(--text-muted);">
                📋 داوطلبان عضویت به عنوان عالم دینی؛ پس از بررسی و احراز صلاحیت روی دکمه تایید کلیک کنید تا دسترسی‌های میز کار برای ایشان فعال شود.
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-pending" class="btn btn-secondary btn-sm">
                ⟳ تازه‌سازی
              </button>
            </div>
          </div>

          <div id="pending-scholars-table-container"></div>
        </div>
      </div>
    </div>
  `;

  // Sub-tabs switching
  const tabThreads = container.querySelector('#tab-btn-threads');
  const tabScholars = container.querySelector('#tab-btn-scholars');
  const tabPending = container.querySelector('#tab-btn-pending-scholars');
  const secThreads = container.querySelector('#section-threads');
  const secScholars = container.querySelector('#section-scholars');
  const secPending = container.querySelector('#section-pending-scholars');
  const pendingBadge = container.querySelector('#pending-badge');

  tabThreads.addEventListener('click', () => {
    activeTab = 'threads';
    tabThreads.classList.add('active');
    tabScholars.classList.remove('active');
    tabPending.classList.remove('active');
    secThreads.style.display = 'block';
    secScholars.style.display = 'none';
    secPending.style.display = 'none';
    fetchThreads();
  });

  tabScholars.addEventListener('click', () => {
    activeTab = 'scholars';
    tabScholars.classList.add('active');
    tabThreads.classList.remove('active');
    tabPending.classList.remove('active');
    secThreads.style.display = 'none';
    secScholars.style.display = 'block';
    secPending.style.display = 'none';
    fetchScholars();
  });

  tabPending.addEventListener('click', () => {
    activeTab = 'pending';
    tabPending.classList.add('active');
    tabThreads.classList.remove('active');
    tabScholars.classList.remove('active');
    secThreads.style.display = 'none';
    secScholars.style.display = 'none';
    secPending.style.display = 'block';
    fetchPendingScholars();
  });

  // Thread search
  let threadSearchTimeout = null;
  container.querySelector('#thread-search').addEventListener('input', (e) => {
    clearTimeout(threadSearchTimeout);
    threadSearchTimeout = setTimeout(() => {
      threadState.search = e.target.value.trim();
      threadState.page = 1;
      fetchThreads();
    }, 300);
  });

  // Filter pills
  container.querySelectorAll('.filter-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');
      threadState.page = 1;
      if (filter === 'all') {
        threadState.status = '';
        threadState.isUrgent = null;
      } else if (filter === 'urgent') {
        threadState.status = '';
        threadState.isUrgent = true;
      } else {
        threadState.status = filter;
        threadState.isUrgent = null;
      }
      fetchThreads();
    });
  });

  container.querySelector('#btn-refresh-threads').addEventListener('click', fetchThreads);

  // Scholars search
  let scholarSearchTimeout = null;
  container.querySelector('#scholar-search').addEventListener('input', (e) => {
    clearTimeout(scholarSearchTimeout);
    scholarSearchTimeout = setTimeout(() => {
      scholarState.search = e.target.value.trim();
      scholarState.page = 1;
      fetchScholars();
    }, 300);
  });

  container.querySelector('#btn-refresh-scholars').addEventListener('click', fetchScholars);

  const threadColumns = [
    {
      header: 'کد رهگیری',
      render: (t) => `<span style="font-family: monospace; font-weight: 700; color: var(--primary);">${t.trackingCode || t.tracking_code || '—'}</span>`
    },
    {
      header: 'موضوع و عنوان',
      render: (t) => `
        <div>
          <div style="font-weight: 600;">${t.title || 'بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${t.category || 'عمومی'}</div>
        </div>
      `
    },
    {
      header: 'فوریت',
      render: (t) => {
        const isUrgent = t.isUrgent ?? t.is_urgent;
        return isUrgent
          ? `<span class="badge badge-urgent">🚨 فوری</span>`
          : `<span class="badge badge-neutral">عادی</span>`;
      }
    },
    {
      header: 'وضعیت',
      render: (t) => {
        const st = t.status || 'OPEN';
        if (st === 'ANSWERED') return `<span class="badge badge-success">پاسخ داده شده</span>`;
        if (st === 'WAITING_SCHOLAR') return `<span class="badge badge-warning">در انتظار استاد</span>`;
        if (st === 'CLOSED') return `<span class="badge badge-neutral">بسته شده</span>`;
        return `<span class="badge badge-info">ترید باز</span>`;
      }
    },
    {
      header: 'تاریخ ثبت',
      render: (t) => `<span style="font-size: 0.78rem;">${formatDateTime(t.createdAt || t.created_at)}</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (t) => `
        <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
          <button class="btn btn-primary btn-sm btn-view-thread" data-thread-id="${t.id}" title="مشاهده مکالمه و پاسخ">
            💬 مکالمه
          </button>
          <button class="btn btn-outline btn-sm btn-status-thread" data-thread-id="${t.id}" data-current-status="${t.status}">
            تغییر وضعیت
          </button>
        </div>
      `
    }
  ];

  async function fetchThreads() {
    renderTable({
      container: container.querySelector('#threads-table-container'),
      columns: threadColumns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: threadState.page,
        pageSize: threadState.pageSize,
        search: threadState.search,
        status: threadState.status
      };
      if (threadState.isUrgent !== null) {
        params.is_urgent = threadState.isUrgent;
      }

      const res = await ApiClient.get('/consultations/threads', params);
      threadState.data = res.data || [];
      threadState.meta = res.meta;

      renderTable({
        container: container.querySelector('#threads-table-container'),
        columns: threadColumns,
        data: threadState.data,
        meta: threadState.meta,
        currentPage: threadState.page,
        pageSize: threadState.pageSize,
        emptyMessage: 'هیچ ترید مشاوره‌ای یافت نشد.',
        onPageChange: (newPage) => {
          threadState.page = newPage;
          fetchThreads();
        },
        onPageSizeChange: (newSize) => {
          threadState.pageSize = newSize;
          threadState.page = 1;
          fetchThreads();
        }
      });

      attachThreadActions();
    } catch (err) {
      container.querySelector('#threads-table-container').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title" style="color: var(--danger);">خطا در دریافت تریدها: ${err.message}</div>
        </div>
      `;
    }
  }

  function attachThreadActions() {
    // 1. View Thread & Quick Reply in Drawer
    container.querySelectorAll('.btn-view-thread').forEach(btn => {
      btn.addEventListener('click', async () => {
        const threadId = btn.getAttribute('data-thread-id');
        openThreadDrawer(threadId);
      });
    });

    // 2. Change status fast action
    container.querySelectorAll('.btn-status-thread').forEach(btn => {
      btn.addEventListener('click', async () => {
        const threadId = btn.getAttribute('data-thread-id');
        const currentStatus = btn.getAttribute('data-current-status');
        const nextStatus = currentStatus === 'ANSWERED' ? 'OPEN' : 'ANSWERED';

        btn.classList.add('loading');
        try {
          await ApiClient.patch(`/consultations/threads/${threadId}/status`, { status: nextStatus });
          Toast.success(`وضعیت ترید با موفقیت به ${nextStatus} تغییر یافت.`);
          fetchThreads();
        } finally {
          btn.classList.remove('loading');
        }
      });
    });
  }

  async function openThreadDrawer(threadId) {
    Drawer.open({
      title: 'مکالمات ترید مشاوره',
      subtitle: `در حال دریافت اطلاعات ترید...`,
      contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
    });

    try {
      const res = await ApiClient.get(`/consultations/threads/${threadId}`);
      const t = res.data;
      const msgs = t.messages || [];
      const atts = t.attachments || [];

      let messagesHtml = msgs.length === 0
        ? '<div style="text-align: center; color: var(--text-muted); padding: 1rem;">هنوز پیامی در این ترید ثبت نشده است.</div>'
        : msgs.map(m => `
            <div class="chat-bubble ${m.senderRole === 'SCHOLAR' || m.senderRole === 'ADMIN' ? 'scholar' : 'user'}">
              <div style="font-weight: 700; font-size: 0.75rem; margin-bottom: 0.25rem;">
                ${m.senderRole === 'SCHOLAR' ? 'عالم / استاد' : (m.senderRole === 'ADMIN' ? 'پاسخ ادمین' : 'سائل')}
              </div>
              <div>${m.text || ''}</div>
              ${m.citation ? `<div style="font-size: 0.75rem; margin-top: 0.4rem; padding: 0.3rem; background: rgba(0,0,0,0.05); border-radius: 4px;"><strong>منبع:</strong> ${m.citation}</div>` : ''}
              <div class="chat-meta">${formatDateTime(m.createdAt || m.created_at)}</div>
            </div>
          `).join('');

      let attachmentsHtml = atts.length === 0
        ? ''
        : `
          <div class="detail-section">
            <div class="detail-section-title">📎 ضمائم و صوت‌ها (${atts.length})</div>
            ${atts.map(a => `
              <div class="detail-row">
                <span>${a.title || a.type || 'فایل پیوست'}</span>
                <span class="detail-value">${a.fileUrl || a.file_url || '—'}</span>
              </div>
            `).join('')}
          </div>
        `;

      Drawer.open({
        title: `ترید: ${t.title || 'بدون عنوان'}`,
        subtitle: `کد رهگیری: ${t.trackingCode || t.tracking_code || '—'} | وضعیت: ${t.status}`,
        contentHtml: `
          <div class="detail-section">
            <div class="detail-row">
              <span class="detail-label">موضوع و دسته‌بندی</span>
              <span class="detail-value">${t.category || 'عمومی'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">فوریت</span>
              <span class="detail-value">${(t.isUrgent ?? t.is_urgent) ? '🚨 فوری' : 'عادی'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">تاریخ ثبت</span>
              <span class="detail-value">${formatDateTime(t.createdAt || t.created_at)}</span>
            </div>
          </div>

          <!-- Chat messages stream -->
          <div class="detail-section">
            <div class="detail-section-title">💬 جریان پیام‌های مشاوره</div>
            <div class="chat-container">
              ${messagesHtml}
            </div>
          </div>

          ${attachmentsHtml}

          <!-- Quick reply form -->
          <div class="detail-section">
            <div class="detail-section-title">✍️ ارسال پاسخ سریع از سوی استاد / ادمین</div>
            <textarea id="quick-reply-text" class="search-input" rows="3" style="width: 100%; margin-bottom: 0.5rem;" placeholder="متن پاسخ معارفی و مستند را وارد کنید..."></textarea>
            <input id="quick-reply-citation" type="text" class="search-input" style="width: 100%; margin-bottom: 0.75rem;" placeholder="ارجاع منبع، آیه یا روایت (اختیاری)">
            <button id="btn-submit-reply" class="btn btn-primary" style="width: 100%;">
              ارسال پاسخ و تبدیل وضعیت به «پاسخ داده شده»
            </button>
          </div>
        `,
        footerHtml: `
          <button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">
            بستن
          </button>
        `
      });

      // Submit quick reply
      const replyBtn = document.getElementById('btn-submit-reply');
      if (replyBtn) {
        replyBtn.addEventListener('click', async () => {
          const text = document.getElementById('quick-reply-text').value.trim();
          const citation = document.getElementById('quick-reply-citation').value.trim();
          if (!text) {
            Toast.warning('لطفاً متن پاسخ را وارد نمایید.');
            return;
          }

          replyBtn.classList.add('loading');
          replyBtn.disabled = true;

          try {
            await ApiClient.post(`/consultations/threads/${threadId}/reply`, {
              text,
              citation: citation || null,
              sender_role: 'SCHOLAR'
            });
            Toast.success('پاسخ با موفقیت ارسال شد و وضعیت ترید به‌روزرسانی گردید.');
            openThreadDrawer(threadId); // Refresh drawer
            fetchThreads(); // Refresh table
          } finally {
            replyBtn.classList.remove('loading');
            replyBtn.disabled = false;
          }
        });
      }
    } catch (err) {
      Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت ترید: ${err.message}</div></div>`);
    }
  }

  // Scholars
  const scholarColumns = [
    {
      header: 'نام عالم و استاد',
      render: (s) => `
        <div style="display: flex; align-items: center; gap: 0.65rem;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: #10b981; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700;">
            ${(s.name || 'ع').slice(0, 1)}
          </div>
          <div>
            <div style="font-weight: 600;">${s.name || 'استاد'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${s.title || 'استاد حوزه و دانشگاه'}</div>
          </div>
        </div>
      `
    },
    {
      header: 'شهر / مذهب',
      render: (s) => `<div>${s.city || '—'} / ${s.madhhab || 'عمومی'}</div>`
    },
    {
      header: 'تخصص‌ها',
      render: (s) => {
        const specs = s.specialties || [];
        return specs.length ? specs.map(x => `<span class="badge badge-neutral" style="margin: 0.1rem;">${x}</span>`).join('') : '—';
      }
    },
    {
      header: 'تعداد پاسخ‌ها',
      render: (s) => `<span style="font-weight: 700;">${formatNum(s.answerCount ?? s.answer_count ?? 0)}</span>`
    },
    {
      header: 'امتیاز',
      render: (s) => `<span class="badge badge-warning">⭐ ${s.rating || '۵.۰'}</span>`
    },
    {
      header: 'وضعیت تایید',
      render: (s) => (s.isVerified ?? s.is_verified)
        ? `<span class="badge badge-success">تایید شده ✓</span>`
        : `<span class="badge badge-neutral">در انتظار تایید</span>`
    },
    {
      header: 'عملیات',
      render: (s) => `
        <button class="btn btn-sm btn-outline btn-delete-scholar" data-id="${s.id}" data-name="${s.name}" style="color: var(--danger); border-color: var(--danger); padding: 0.2rem 0.5rem;" title="حذف عالم دینی">
          🗑️
        </button>
      `
    }
  ];

  // Add Scholar Handler
  const btnAddScholar = container.querySelector('#btn-add-scholar');
  if (btnAddScholar) {
    btnAddScholar.addEventListener('click', () => {
      Drawer.open({
        title: '➕ افزودن عالم دینی و استاد جدید',
        subtitle: 'مشخصات هویتی، علمی و حوزوی جهت پاسخ‌گویی به سوالات کاربران',
        contentHtml: `
          <div style="display: flex; flex-direction: column; gap: 0.85rem; font-size: 0.85rem;">
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">نام و نام خانوادگی:</label>
              <input id="drawer-sch-name" type="text" class="search-input" style="width: 100%;" placeholder="مثال: آیت‌الله دکتر سید مهدی حسینی">
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">عنوان حوزوی یا دانشگاهی:</label>
              <input id="drawer-sch-title" type="text" class="search-input" style="width: 100%;" placeholder="مثال: استاد سطوح عالی فقه و علوم قرآن">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>
                <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">مذهب فقهی:</label>
                <select id="drawer-sch-madhhab" class="search-input" style="width: 100%;">
                  <option value="شیعه اثناعشری">شیعه اثناعشری (جعفری)</option>
                  <option value="اهل سنت حنفی">اهل سنت (حنفی)</option>
                  <option value="اهل سنت شافعی">اهل سنت (شافعی)</option>
                  <option value="اهل سنت مالکی / حنبلی">اهل سنت (مالکی / حنبلی)</option>
                  <option value="مقارن و تقریب فریقین">مقارن و تقریب فریقین</option>
                </select>
              </div>
              <div>
                <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">شهر سکونت:</label>
                <input id="drawer-sch-city" type="text" class="search-input" style="width: 100%;" placeholder="مثال: قم، مشهد، تهران، سنندج">
              </div>
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">مرکز علمی، حوزه یا مسجد:</label>
              <input id="drawer-sch-mosque" type="text" class="search-input" style="width: 100%;" placeholder="مثال: حوزه علمیه قم / دانشگاه تهران">
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">تخصص‌ها (با ویرگول جدا کنید):</label>
              <input id="drawer-sch-specialties" type="text" class="search-input" style="width: 100%;" placeholder="مثال: فقه مقارن, تفسیر قرآن, اخلاق اسلامی">
            </div>
            <div>
              <label style="display: block; font-weight: 700; margin-bottom: 0.25rem;">بیوگرافی و رزومه علمی:</label>
              <textarea id="drawer-sch-bio" class="search-input" style="width: 100%; height: 80px; resize: vertical;" placeholder="توضیحات مختصر درباره سوابق تدریس و تالیفات..."></textarea>
            </div>
          </div>
        `,
        footerHtml: `
          <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
            <button id="btn-cancel-add-sch" class="btn btn-secondary btn-sm">انصراف</button>
            <button id="btn-submit-add-sch" class="btn btn-primary btn-sm">ثبت و ذخیره عالم دینی</button>
          </div>
        `
      });

      document.getElementById('btn-cancel-add-sch').addEventListener('click', () => Drawer.close());
      document.getElementById('btn-submit-add-sch').addEventListener('click', async () => {
        const name = document.getElementById('drawer-sch-name').value.trim();
        const title = document.getElementById('drawer-sch-title').value.trim();
        const madhhab = document.getElementById('drawer-sch-madhhab').value;
        const city = document.getElementById('drawer-sch-city').value.trim();
        const mosque = document.getElementById('drawer-sch-mosque').value.trim();
        const rawSpecs = document.getElementById('drawer-sch-specialties').value.trim();
        const bio = document.getElementById('drawer-sch-bio').value.trim();

        if (!name || !title || !city || !bio) {
          Toast.error('لطفاً فیلدهای الزامی (نام، عنوان، شهر و بیوگرافی) را پر کنید.');
          return;
        }

        const specialties = rawSpecs ? rawSpecs.split(/[,،]/).map(s => s.trim()).filter(Boolean) : ['علوم قرآن و فقه'];

        try {
          await ApiClient.post('/consultations/scholars', {
            name,
            title,
            madhhab,
            city,
            mosque: mosque || 'مرکز علوم اسلامی',
            specialties,
            bio,
            isVerified: true,
            rating: 5.0
          });
          Toast.success(`عالم دینی '${name}' با موفقیت ثبت شد.`);
          Drawer.close();
          fetchScholars();
        } catch (err) {
          Toast.error(`خطا در ثبت عالم: ${err.message}`);
        }
      });
    });
  }

  // Delegate delete scholar click
  container.querySelector('#scholars-table-container').addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-delete-scholar');
    if (!btn) return;
    const schId = btn.dataset.id;
    const schName = btn.dataset.name || 'عالم دینی';
    if (!confirm(`آیا از حذف '${schName}' اطمینان دارید؟`)) return;

    try {
      await ApiClient.delete('/consultations/scholars/' + schId);
      Toast.success(`عالم '${schName}' حذف شد.`);
      fetchScholars();
    } catch (err) {
      Toast.error(`خطا در حذف عالم: ${err.message}`);
    }
  });

  async function fetchScholars() {
    renderTable({
      container: container.querySelector('#scholars-table-container'),
      columns: scholarColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/consultations/scholars', {
        page: scholarState.page,
        pageSize: scholarState.pageSize,
        search: scholarState.search
      });
      scholarState.data = res.data || [];
      scholarState.meta = res.meta;

      renderTable({
        container: container.querySelector('#scholars-table-container'),
        columns: scholarColumns,
        data: scholarState.data,
        meta: scholarState.meta,
        currentPage: scholarState.page,
        pageSize: scholarState.pageSize,
        emptyMessage: 'استادی یافت نشد.',
        onPageChange: (newPage) => {
          scholarState.page = newPage;
          fetchScholars();
        },
        onPageSizeChange: (newSize) => {
          scholarState.pageSize = newSize;
          scholarState.page = 1;
          fetchScholars();
        }
      });
    } catch (err) {
      container.querySelector('#scholars-table-container').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title" style="color: var(--danger);">خطا در دریافت اساتید: ${err.message}</div>
        </div>
      `;
    }
  }

  // Pending Scholars
  const pendingColumns = [
    {
      header: 'نام متقاضی',
      render: (u) => `
        <div style="font-weight: 700; color: var(--primary);">
          ${u.fullName || '—'}
        </div>
      `
    },
    {
      header: 'شماره تماس',
      render: (u) => `<span dir="ltr" style="font-family: monospace; font-weight: 600;">${u.phoneNumber || '—'}</span>`
    },
    {
      header: 'نام مسجد یا مرکز دینی',
      render: (u) => `
        <div style="display: flex; align-items: center; gap: 0.35rem; font-weight: 600;">
          <span>🕌</span>
          <span>${u.mosqueName || 'مسجد ثبت نشده'}</span>
        </div>
      `
    },
    {
      header: 'آدرس محل فعالیت',
      render: (u) => `<span style="font-size: 0.8rem; color: var(--text-muted);">${u.mosqueAddress || '—'}</span>`
    },
    {
      header: 'مذهب فقهی',
      render: (u) => `<span class="badge badge-neutral">${u.madhhab || 'عمومی'}</span>`
    },
    {
      header: 'تاریخ ثبت‌نام',
      render: (u) => `<span style="font-size: 0.78rem;">${formatDateTime(u.createdAt)}</span>`
    },
    {
      header: 'عملیات احراز صلاحیت',
      style: 'text-align: left;',
      render: (u) => `
        <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
          <button class="btn btn-sm btn-approve-scholar" data-id="${u.id}" data-name="${u.fullName}" style="background: #10b981; color: white; border: none; font-weight: 600; padding: 0.3rem 0.65rem;" title="تایید و ارتقای کاربر به عنوان عالم رسمی">
            ✓ تایید و فعال‌سازی
          </button>
          <button class="btn btn-sm btn-reject-scholar" data-id="${u.id}" data-name="${u.fullName}" style="background: #ef4444; color: white; border: none; padding: 0.3rem 0.65rem;" title="رد درخواست عالم">
            ✕ رد
          </button>
        </div>
      `
    }
  ];

  // Refresh Pending button
  const btnRefreshPending = container.querySelector('#btn-refresh-pending');
  if (btnRefreshPending) {
    btnRefreshPending.addEventListener('click', fetchPendingScholars);
  }

  // Handle Approve / Reject Clicks
  container.addEventListener('click', async (e) => {
    const approveBtn = e.target.closest('.btn-approve-scholar');
    if (approveBtn) {
      const uId = approveBtn.dataset.id;
      const uName = approveBtn.dataset.name || 'متقاضی';
      if (!confirm(`آیا از تایید صلاحیت علمی و ارتقای «${uName}» به عنوان عالم دینی رسمی اطمینان دارید؟`)) return;

      approveBtn.disabled = true;
      try {
        await ApiClient.post(`/consultations/scholars/${uId}/approve`, {});
        Toast.success(`عالم دینی «${uName}» با موفقیت تایید و دسترسی‌های وی فعال گردید.`);
        fetchPendingScholars();
        checkPendingBadge();
      } catch (err) {
        Toast.error(`خطا در تایید عالم: ${err.message}`);
        approveBtn.disabled = false;
      }
      return;
    }

    const rejectBtn = e.target.closest('.btn-reject-scholar');
    if (rejectBtn) {
      const uId = rejectBtn.dataset.id;
      const uName = rejectBtn.dataset.name || 'متقاضی';
      if (!confirm(`آیا از رد درخواست عضویت «${uName}» اطمینان دارید؟ (کاربر به عنوان کاربر عادی باقی خواهد ماند)`)) return;

      rejectBtn.disabled = true;
      try {
        await ApiClient.post(`/consultations/scholars/${uId}/reject`, {});
        Toast.info(`درخواست «${uName}» رد شد.`);
        fetchPendingScholars();
        checkPendingBadge();
      } catch (err) {
        Toast.error(`خطا در رد درخواست: ${err.message}`);
        rejectBtn.disabled = false;
      }
    }
  });

  async function checkPendingBadge() {
    try {
      const res = await ApiClient.get('/consultations/pending-scholars');
      const count = (res.data || []).length;
      if (pendingBadge) {
        if (count > 0) {
          pendingBadge.textContent = count;
          pendingBadge.style.display = 'inline-block';
        } else {
          pendingBadge.style.display = 'none';
        }
      }
    } catch (e) {
      // Ignore badge check error silently
    }
  }

  async function fetchPendingScholars() {
    renderTable({
      container: container.querySelector('#pending-scholars-table-container'),
      columns: pendingColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/consultations/pending-scholars');
      const list = res.data || [];
      checkPendingBadge();

      renderTable({
        container: container.querySelector('#pending-scholars-table-container'),
        columns: pendingColumns,
        data: list,
        emptyMessage: 'هیچ درخواست عضویت جدیدی در انتظار بررسی وجود ندارد.'
      });
    } catch (err) {
      container.querySelector('#pending-scholars-table-container').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title" style="color: var(--danger);">خطا در دریافت درخواست‌های معلق: ${err.message}</div>
        </div>
      `;
    }
  }

  checkPendingBadge();
  fetchThreads();
}
