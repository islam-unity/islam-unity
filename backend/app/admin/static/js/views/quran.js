/**
 * View 5: Quran & Reciters (قرآن کریم و قاریان)
 * 114 Surahs, paginated Ayahs with limit/offset optimization, Tadabbur drawer, and Reciters.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';

export function renderQuran(container) {
  let activeTab = 'surahs'; // 'surahs' | 'ayahs' | 'reciters' | 'thematic'

  let surahsState = { page: 1, pageSize: 20, data: [], meta: null };
  let ayahsState = { page: 1, pageSize: 15, surahId: '', juz: '', search: '', data: [], meta: null };
  let recitersState = { data: [] };
  let thematicState = { page: 1, pageSize: 15, search: '', data: [], meta: null };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">📖 قرآن کریم، آیات نورانی، قاریان و سوره‌های موضوعی</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-quran-surahs" class="subtab-btn active">فهرست ۱۱۴ سوره مبارکه</button>
          <button id="tab-quran-ayahs" class="subtab-btn">آیات شریفه و تدبر</button>
          <button id="tab-quran-thematic" class="subtab-btn">✨ سوره‌های موضوعی (Thematic)</button>
          <button id="tab-quran-reciters" class="subtab-btn">قاریان و قطعات صوتی</button>
        </div>

        <!-- Surahs Section -->
        <div id="section-quran-surahs">
          <div id="surahs-table-container"></div>
        </div>

        <!-- Ayahs Section -->
        <div id="section-quran-ayahs" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <select id="ayah-filter-surah" class="select-control" style="min-width: 150px;">
                <option value="">همه سوره‌ها</option>
              </select>

              <select id="ayah-filter-juz" class="select-control">
                <option value="">همه جزء‌ها</option>
                ${Array.from({ length: 30 }, (_, i) => `<option value="${i + 1}">جزء ${i + 1}</option>`).join('')}
              </select>

              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="ayah-search" type="text" class="search-input" placeholder="جستجو در متن عربی یا ترجمه...">
              </div>
            </div>

            <div class="toolbar-group">
              <button id="btn-refresh-ayahs" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="ayahs-table-container"></div>
        </div>

        <!-- Thematic Section -->
        <div id="section-quran-thematic" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="thematic-search" type="text" class="search-input" placeholder="جستجو در عنوان یا موضوع سوره‌های موضوعی...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-thematic" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="thematic-table-container"></div>
        </div>

        <!-- Reciters Section -->
        <div id="section-quran-reciters" style="display: none;">
          <div id="reciters-table-container"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabSurahs = container.querySelector('#tab-quran-surahs');
  const tabAyahs = container.querySelector('#tab-quran-ayahs');
  const tabThematic = container.querySelector('#tab-quran-thematic');
  const tabReciters = container.querySelector('#tab-quran-reciters');
  const secSurahs = container.querySelector('#section-quran-surahs');
  const secAyahs = container.querySelector('#section-quran-ayahs');
  const secThematic = container.querySelector('#section-quran-thematic');
  const secReciters = container.querySelector('#section-quran-reciters');

  function switchTab(name) {
    activeTab = name;
    tabSurahs.classList.toggle('active', name === 'surahs');
    tabAyahs.classList.toggle('active', name === 'ayahs');
    tabThematic.classList.toggle('active', name === 'thematic');
    tabReciters.classList.toggle('active', name === 'reciters');

    secSurahs.style.display = name === 'surahs' ? 'block' : 'none';
    secAyahs.style.display = name === 'ayahs' ? 'block' : 'none';
    secThematic.style.display = name === 'thematic' ? 'block' : 'none';
    secReciters.style.display = name === 'reciters' ? 'block' : 'none';
  }

  tabSurahs.addEventListener('click', () => { switchTab('surahs'); fetchSurahs(); });
  tabAyahs.addEventListener('click', () => { switchTab('ayahs'); fetchAyahs(); });
  tabThematic.addEventListener('click', () => { switchTab('thematic'); fetchThematicSurahs(); });
  tabReciters.addEventListener('click', () => { switchTab('reciters'); fetchReciters(); });

  // Ayah filters
  const surahSelect = container.querySelector('#ayah-filter-surah');
  surahSelect.addEventListener('change', (e) => {
    ayahsState.surahId = e.target.value;
    ayahsState.page = 1;
    fetchAyahs();
  });

  const juzSelect = container.querySelector('#ayah-filter-juz');
  juzSelect.addEventListener('change', (e) => {
    ayahsState.juz = e.target.value;
    ayahsState.page = 1;
    fetchAyahs();
  });

  let ayahSearchTimeout = null;
  container.querySelector('#ayah-search').addEventListener('input', (e) => {
    clearTimeout(ayahSearchTimeout);
    ayahSearchTimeout = setTimeout(() => {
      ayahsState.search = e.target.value.trim();
      ayahsState.page = 1;
      fetchAyahs();
    }, 300);
  });

  container.querySelector('#btn-refresh-ayahs').addEventListener('click', fetchAyahs);

  // Surahs Columns
  const surahColumns = [
    { header: '#', render: (s) => `<span style="font-weight: 700;">${s.id}</span>` },
    {
      header: 'نام سوره',
      render: (s) => `
        <div>
          <span style="font-weight: 700; font-size: 0.95rem;">سورة ${s.nameArabic || s.name_arabic}</span>
          <span style="color: var(--text-muted); font-size: 0.8rem; margin-right: 0.5rem;">(${s.namePersian || s.name_persian || ''})</span>
        </div>
      `
    },
    { header: 'تعداد آیات', render: (s) => formatNum(s.ayahCount || s.ayah_count || 0) },
    {
      header: 'محل نزول',
      render: (s) => {
        const type = s.revelationType || s.revelation_type;
        return type === 'MAKKI' ? `<span class="badge badge-amber">مکی</span>` : `<span class="badge badge-info">مدنی</span>`;
      }
    },
    { header: 'جزء', render: (s) => `جزء ${formatNum(s.juzNumber || s.juz_number || 1)}` },
    { header: 'ترتیب نزول', render: (s) => formatNum(s.revelationOrder || s.revelation_order || 0) },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (s) => `
        <button class="btn btn-outline btn-sm btn-filter-surah-ayahs" data-surah-id="${s.id}">
          📖 مشاهده آیات
        </button>
      `
    }
  ];

  async function fetchSurahs() {
    renderTable({
      container: container.querySelector('#surahs-table-container'),
      columns: surahColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/quran/surahs', {
        page: surahsState.page,
        pageSize: surahsState.pageSize
      });
      surahsState.data = res.data || [];
      surahsState.meta = res.meta;

      // Populate surah dropdown
      if (surahSelect.children.length <= 1) {
        surahsState.data.forEach(s => {
          const opt = document.createElement('option');
          opt.value = s.id;
          opt.textContent = `${s.id}. ${s.namePersian || s.nameArabic}`;
          surahSelect.appendChild(opt);
        });
      }

      renderTable({
        container: container.querySelector('#surahs-table-container'),
        columns: surahColumns,
        data: surahsState.data,
        meta: surahsState.meta,
        currentPage: surahsState.page,
        pageSize: surahsState.pageSize,
        emptyMessage: 'سوره‌ای یافت نشد.',
        onPageChange: (p) => { surahsState.page = p; fetchSurahs(); },
        onPageSizeChange: (s) => { surahsState.pageSize = s; surahsState.page = 1; fetchSurahs(); }
      });

      // Quick jump to ayahs
      container.querySelectorAll('.btn-filter-surah-ayahs').forEach(btn => {
        btn.addEventListener('click', () => {
          const surahId = btn.getAttribute('data-surah-id');
          ayahsState.surahId = surahId;
          surahSelect.value = surahId;
          tabAyahs.click();
        });
      });
    } catch (err) {
      container.querySelector('#surahs-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // Ayahs Columns
  const ayahColumns = [
    {
      header: 'آیه',
      render: (a) => `
        <div style="font-weight: 700; text-align: center;">
          <span>سوره ${a.surahId || a.surah_id}</span>
          <div style="font-size: 0.75rem; color: var(--text-muted);">آیه ${a.ayahNumber || a.ayah_number}</div>
        </div>
      `
    },
    {
      header: 'متن عربی آیه',
      render: (a) => `
        <div style="font-family: 'Amiri', 'Traditional Arabic', serif; font-size: 1.15rem; line-height: 2; color: #064e3b; direction: rtl;">
          ${a.textArabic || a.text_arabic || a.textClean || a.text_clean || ''}
        </div>
      `
    },
    {
      header: 'ترجمه فارسی',
      render: (a) => `
        <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
          ${a.textPersian || a.text_persian || 'ترجمه ثبت نشده است.'}
        </div>
      `
    },
    {
      header: 'جزء / صفحه',
      render: (a) => `<div>جزء ${a.juz || '—'}</div><div style="font-size: 0.75rem; color: var(--text-muted);">ص ${a.page || '—'}</div>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (a) => `
        <button class="btn btn-primary btn-sm btn-view-tadabbur" data-surah="${a.surahId || a.surah_id}" data-ayah="${a.ayahNumber || a.ayah_number}">
          🌟 تدبر و تفسیر
        </button>
      `
    }
  ];

  async function fetchAyahs() {
    renderTable({
      container: container.querySelector('#ayahs-table-container'),
      columns: ayahColumns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: ayahsState.page,
        pageSize: ayahsState.pageSize,
        search: ayahsState.search
      };
      if (ayahsState.surahId) params.surah_id = ayahsState.surahId;
      if (ayahsState.juz) params.juz = ayahsState.juz;

      const res = await ApiClient.get('/quran/ayahs', params);
      ayahsState.data = res.data || [];
      ayahsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#ayahs-table-container'),
        columns: ayahColumns,
        data: ayahsState.data,
        meta: ayahsState.meta,
        currentPage: ayahsState.page,
        pageSize: ayahsState.pageSize,
        emptyMessage: 'آیه‌ای با فیلترهای مشخص‌شده یافت نشد.',
        onPageChange: (p) => { ayahsState.page = p; fetchAyahs(); },
        onPageSizeChange: (s) => { ayahsState.pageSize = s; ayahsState.page = 1; fetchAyahs(); }
      });

      // Tadabbur action
      container.querySelectorAll('.btn-view-tadabbur').forEach(btn => {
        btn.addEventListener('click', async () => {
          const surahId = btn.getAttribute('data-surah');
          const ayahNumber = btn.getAttribute('data-ayah');
          openTadabburDrawer(surahId, ayahNumber);
        });
      });
    } catch (err) {
      container.querySelector('#ayahs-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت آیات: ${err.message}</div></div>
      `;
    }
  }

  async function openTadabburDrawer(surahId, ayahNumber) {
    Drawer.open({
      title: `تدبر و تفسیر سوره ${surahId}، آیه ${ayahNumber}`,
      subtitle: 'در حال دریافت داده‌های تدبر...',
      contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
    });

    try {
      const res = await ApiClient.get(`/quran/ayahs/${surahId}/${ayahNumber}/tadabbur`);
      const t = res.data;
      const keywords = t.keywords || [];
      const aiTadabbur = t.aiTadabbur || t.ai_tadabbur || [];

      Drawer.open({
        title: `تدبر و تفسیر سوره ${surahId}، آیه ${ayahNumber}`,
        subtitle: `پایگاه معارفی تدبر و المیزان`,
        contentHtml: `
          <div class="detail-section">
            <div class="detail-section-title">📖 تفسیر اجمالی و معارفی</div>
            <div style="font-size: 0.9rem; line-height: 1.8; color: var(--text-main);">
              ${t.briefTafsir || t.brief_tafsir || 'تفسیر اجمالی ثبت نشده است.'}
            </div>
          </div>

          ${t.reflectionQuestion || t.reflection_question ? `
            <div class="detail-section">
              <div class="detail-section-title">❓ پرسش تدبری برای اندیشه</div>
              <div style="background: white; border-right: 4px solid var(--primary); padding: 0.75rem; border-radius: 6px; font-weight: 600; color: #064e3b;">
                ${t.reflectionQuestion || t.reflection_question}
              </div>
            </div>
          ` : ''}

          <div class="detail-section">
            <div class="detail-section-title">🔑 کلیدواژه‌های موضوعی آیه</div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
              ${keywords.length ? keywords.map(k => `<span class="badge badge-info">${k}</span>`).join('') : '<span style="color: var(--text-muted);">کلیدواژه‌ای موجود نیست</span>'}
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">🤖 نکات تدبر هوش مصنوعی (AI Reflections)</div>
            <ul style="padding-right: 1.25rem; font-size: 0.85rem; line-height: 1.6; color: var(--text-secondary);">
              ${aiTadabbur.length ? aiTadabbur.map(x => `<li style="margin-bottom: 0.35rem;">${x}</li>`).join('') : '<li>نکته‌ای استخراج نشده است.</li>'}
            </ul>
          </div>
        `,
        footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
      });
    } catch (err) {
      Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت تدبر: ${err.message}</div></div>`);
    }
  }

  // Reciters
  async function fetchReciters() {
    renderTable({
      container: container.querySelector('#reciters-table-container'),
      columns: [
        { header: 'شناسه', render: (r) => `<span style="font-family: monospace;">${r.id}</span>` },
        { header: 'نام قاری (فارسی)', render: (r) => `<span style="font-weight: 700;">${r.nameFa || r.name_fa}</span>` },
        { header: 'نام قاری (عربی)', render: (r) => r.nameAr || r.name_ar || '—' },
        { header: 'سبک تلاوت', render: (r) => `<span class="badge badge-info">${r.style || 'ترتیل'}</span>` },
        { header: 'بیت‌ریت', render: (r) => `${r.bitrate || 128} kbps` },
        { header: 'پیش‌فرض', render: (r) => (r.isDefault ?? r.is_default) ? `<span class="badge badge-success">پیش‌فرض ✓</span>` : '—' }
      ],
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/quran/reciters');
      recitersState.data = res.data || [];
      renderTable({
        container: container.querySelector('#reciters-table-container'),
        columns: [
          { header: 'شناسه', render: (r) => `<span style="font-family: monospace;">${r.id}</span>` },
          { header: 'نام قاری (فارسی)', render: (r) => `<span style="font-weight: 700;">${r.nameFa || r.name_fa}</span>` },
          { header: 'نام قاری (عربی)', render: (r) => r.nameAr || r.name_ar || '—' },
          { header: 'سبک تلاوت', render: (r) => `<span class="badge badge-info">${r.style || 'ترتیل'}</span>` },
          { header: 'بیت‌ریت', render: (r) => `${r.bitrate || 128} kbps` },
          { header: 'پیش‌فرض', render: (r) => (r.isDefault ?? r.is_default) ? `<span class="badge badge-success">پیش‌فرض ✓</span>` : '—' }
        ],
        data: recitersState.data,
        emptyMessage: 'قاری یافت نشد.'
      });
    } catch (err) {
      container.querySelector('#reciters-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // -------------------------------------------------------------
  // Thematic Surahs
  // -------------------------------------------------------------
  async function fetchThematicSurahs() {
    renderTable({
      container: container.querySelector('#thematic-table-container'),
      columns: thematicColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/quran/thematic-surahs', {
        page: thematicState.page,
        pageSize: thematicState.pageSize,
        search: thematicState.search
      });

      thematicState.data = res.data || [];
      thematicState.meta = res.meta;

      renderTable({
        container: container.querySelector('#thematic-table-container'),
        columns: thematicColumns,
        data: thematicState.data,
        meta: thematicState.meta,
        currentPage: thematicState.page,
        pageSize: thematicState.pageSize,
        emptyMessage: 'سوره موضوعی یافت نشد.',
        onPageChange: (newPage) => {
          thematicState.page = newPage;
          fetchThematicSurahs();
        },
        onPageSizeChange: (newSize) => {
          thematicState.pageSize = newSize;
          thematicState.page = 1;
          fetchThematicSurahs();
        }
      });

      // Attach Actions
      container.querySelectorAll('.btn-toggle-thematic-feature').forEach(btn => {
        btn.addEventListener('click', async () => {
          const sId = btn.getAttribute('data-surah-id');
          btn.disabled = true;
          try {
            await ApiClient.patch(`/quran/thematic-surahs/${sId}/feature`);
            fetchThematicSurahs();
          } catch (err) {
            btn.disabled = false;
          }
        });
      });

      container.querySelectorAll('.btn-view-thematic-detail').forEach(btn => {
        btn.addEventListener('click', async () => {
          const sId = btn.getAttribute('data-surah-id');
          openThematicDetailDrawer(sId);
        });
      });

      container.querySelectorAll('.btn-delete-thematic').forEach(btn => {
        btn.addEventListener('click', async () => {
          const sId = btn.getAttribute('data-surah-id');
          const title = btn.getAttribute('data-title');
          if (!confirm(`آیا از حذف سوره موضوعی «${title}» اطمینان دارید؟`)) return;
          try {
            await ApiClient.delete(`/quran/thematic-surahs/${sId}`);
            fetchThematicSurahs();
          } catch (err) {
            console.error(err);
          }
        });
      });

    } catch (err) {
      container.querySelector('#thematic-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت سوره‌های موضوعی: ${err.message}</div></div>
      `;
    }
  }

  const thematicColumns = [
    {
      header: 'شناسه سوره',
      render: (t) => `<span style="font-family: monospace; font-size: 0.8rem;">${t.id}</span>`
    },
    {
      header: 'عنوان موضوعی',
      render: (t) => `
        <div>
          <div style="font-weight: 700;">${t.title_fa || t.title || t.name_persian || 'بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${t.theme_category || t.themeCategory || 'موضوع معارفی'}</div>
        </div>
      `
    },
    {
      header: 'تعداد آیات منتخب',
      render: (t) => formatNum(t.ayah_count || t.ayahCount || (t.ayahs ? t.ayahs.length : 0))
    },
    {
      header: 'وضعیت نشان ویژه',
      render: (t) => (t.is_featured ?? t.isFeatured)
        ? `<span class="badge badge-success">⭐ ویژه</span>`
        : `<span class="badge badge-neutral">عادی</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (t) => `
        <div style="display: flex; gap: 0.35rem; justify-content: flex-end;">
          <button class="btn btn-sm btn-outline btn-toggle-thematic-feature" data-surah-id="${t.id}" title="تغییر وضعیت نشان ویژه">
            ${(t.is_featured ?? t.isFeatured) ? 'عادی‌سازی' : '⭐ ویژه کن'}
          </button>
          <button class="btn btn-sm btn-primary btn-view-thematic-detail" data-surah-id="${t.id}" title="مشاهده جزئیات و آیات">
            🔍 جزئیات
          </button>
          <button class="btn btn-sm btn-outline btn-delete-thematic" data-surah-id="${t.id}" data-title="${t.title_fa || t.title || ''}" style="color: #ef4444;" title="حذف">
            🗑️
          </button>
        </div>
      `
    }
  ];

  async function openThematicDetailDrawer(surahId) {
    Drawer.open({
      title: 'سوره موضوعی',
      subtitle: `در حال دریافت اطلاعات سوره موضوعی ${surahId}...`,
      contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
    });

    try {
      const res = await ApiClient.get(`/quran/thematic-surahs/${surahId}`);
      const d = res.data;
      const ayahs = d.ayahs || [];

      Drawer.open({
        title: `✨ سوره موضوعی: ${d.title_fa || d.title || d.name_persian || surahId}`,
        subtitle: `دسته‌بندی: ${d.theme_category || 'عمومی'} | تعداد آیات: ${formatNum(ayahs.length)}`,
        contentHtml: `
          <div class="detail-section">
            <div class="detail-section-title">📝 چکیده و فلسفه نام‌گذاری موضوعی</div>
            <div style="font-size: 0.88rem; line-height: 1.7; color: var(--text-secondary); background: var(--bg-body); padding: 0.75rem; border-radius: 6px;">
              ${d.summary || 'چکیده‌ای ثبت نشده است.'}
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">📖 آیات منتخب این محور (${formatNum(ayahs.length)} آیه)</div>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${ayahs.map((a, i) => `
                <div style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem;">
                  <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--primary); margin-bottom: 0.35rem;">
                    <span>[${i + 1}] سوره ${a.surah_id} : آیه ${a.ayah_number}</span>
                    <span class="badge badge-info">جزء ${a.juz || '—'}</span>
                  </div>
                  <div style="font-family: 'Amiri', 'Traditional Arabic', serif; font-size: 1.05rem; line-height: 1.8; color: var(--text-main); direction: rtl; text-align: right; margin-bottom: 0.35rem;">
                    ${a.text_arabic || a.textArabic}
                  </div>
                  <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.6;">
                    ${a.text_persian || a.textPersian || '—'}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `,
        footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
      });
    } catch (err) {
      Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت جزئیات: ${err.message}</div></div>`);
    }
  }

  // Thematic Search listener
  let thematicSearchTimeout = null;
  container.querySelector('#thematic-search')?.addEventListener('input', (e) => {
    clearTimeout(thematicSearchTimeout);
    thematicSearchTimeout = setTimeout(() => {
      thematicState.search = e.target.value.trim();
      thematicState.page = 1;
      fetchThematicSurahs();
    }, 300);
  });

  container.querySelector('#btn-refresh-thematic')?.addEventListener('click', fetchThematicSurahs);

  fetchSurahs();
}
