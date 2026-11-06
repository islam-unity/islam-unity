/**
 * View: Prayer Times & Cities Management (اوقات شرعی و مدیریت شهرها)
 * Supports JSON upload (single & multi-city batch), manual editing, export, and reset to defaults.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderPrayerTimes(container) {
  let activeTab = 'list'; // 'list' | 'json' | 'manual'
  let citiesState = {
    search: '',
    data: [],
    loading: false
  };

  const SAMPLE_ARRAY_JSON = JSON.stringify([
    {
      "city_id": "mashhad",
      "city_name": "مشهد مقدس",
      "province": "خراسان رضوی",
      "fajr": "04:25",
      "sunrise": "05:49",
      "dhuhr": "11:29",
      "asr": "14:45",
      "sunset": "17:08",
      "maghrib": "17:26",
      "isha": "18:18",
      "midnight": "22:47"
    },
    {
      "city_id": "shiraz",
      "city_name": "شیراز",
      "province": "فارس",
      "fajr": "04:46",
      "sunrise": "06:06",
      "dhuhr": "11:47",
      "asr": "15:07",
      "sunset": "17:29",
      "maghrib": "17:46",
      "isha": "18:36",
      "midnight": "23:07"
    }
  ], null, 2);

  const SAMPLE_DICT_JSON = JSON.stringify({
    "yazd": {
      "city_name": "یزد",
      "province": "یزد",
      "fajr": "04:43",
      "sunrise": "06:04",
      "dhuhr": "11:45",
      "asr": "15:04",
      "sunset": "17:27",
      "maghrib": "17:44",
      "isha": "18:34",
      "midnight": "23:05"
    },
    "kerman": {
      "city_name": "کرمان",
      "province": "کرمان",
      "fajr": "04:32",
      "sunrise": "05:52",
      "dhuhr": "11:34",
      "asr": "14:53",
      "sunset": "17:15",
      "maghrib": "17:33",
      "isha": "18:23",
      "midnight": "22:53"
    }
  }, null, 2);

  const SAMPLE_FA_JSON = JSON.stringify({
    "نام شهر": "کاشان",
    "استان": "اصفهان",
    "اذان صبح": "04:51",
    "طلوع آفتاب": "06:14",
    "اذان ظهر": "11:53",
    "اذان عصر": "15:10",
    "غروب آفتاب": "17:33",
    "اذان مغرب": "17:51",
    "اذان عشاء": "18:42",
    "نیمه شب": "23:12"
  }, null, 2);

  container.innerHTML = `
    <!-- Top Stat Summary -->
    <div class="stat-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 1.5rem;">
      <div class="stat-card">
        <div class="stat-label">تعداد کل شهرهای فعال</div>
        <div class="stat-value" id="stat-total-cities">--</div>
        <div class="stat-change" style="color: var(--text-secondary);">بارگذاری‌شده در اپلیکیشن موبایل</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">مبنای استخراج و محاسبه</div>
        <div class="stat-value" style="font-size: 1.15rem; color: #0d9488;">ژئوفیزیک دانشگاه تهران</div>
        <div class="stat-change">هماهنگ با شیوه رسمی تقویم کشور</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">همگام‌سازی بلادرنگ</div>
        <div class="stat-value" style="font-size: 1.15rem; color: #10b981;">فعال (API v1)</div>
        <div class="stat-change">پشتیبانی از بارگذاری یکجا (Batch)</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div class="card-title">🕌 مدیریت اوقات شرعی و بارگذاری داده‌های شهرها</div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <button id="btn-export-json" class="btn btn-secondary btn-sm" title="دانلود کل داده‌ها در یک فایل JSON">
            📥 خروجی کامل JSON
          </button>
          <button id="btn-reset-defaults" class="btn btn-secondary btn-sm" style="color: #b45309;" title="بازنشانی جدول به ۱۲ کلان‌شهر استاندارد">
            ↺ بازنشانی به ۱۲ شهر پیش‌فرض
          </button>
        </div>
      </div>

      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs" style="margin-bottom: 1.25rem;">
          <button id="subtab-list" class="subtab-btn active">📋 فهرست شهرها و اوقات شرعی</button>
          <button id="subtab-json" class="subtab-btn">⚡ بارگذاری گروهی JSON (چند شهر یا تک‌شهر)</button>
          <button id="subtab-manual" class="subtab-btn">➕ افزودن / ویرایش دستی شهر</button>
        </div>

        <!-- Tab 1: Cities List -->
        <div id="section-cities-list">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="cities-search-input" type="text" class="search-input" placeholder="جستجوی نام شهر یا استان...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-cities" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
              <button id="btn-switch-to-json" class="btn btn-primary btn-sm">⚡ بارگذاری JSON</button>
            </div>
          </div>

          <div id="cities-table-container"></div>
        </div>

        <!-- Tab 2: JSON Batch Upload -->
        <div id="section-json-upload" style="display: none;">
          <div style="background: var(--bg-hover, #f8fafc); border: 1px dashed var(--border-color, #cbd5e1); border-radius: 12px; padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
              <div>
                <h4 style="margin: 0 0 0.25rem 0; font-size: 0.95rem; font-weight: 700; color: var(--text-primary);">
                  📁 آپلود مستقیم فایل JSON
                </h4>
                <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">
                  می‌توانید یک فایل حاوی یک شهر یا چندین شهر را انتخاب کنید تا مستقیماً به بانک اطلاعات اضافه شود.
                </p>
              </div>
              <div>
                <input type="file" id="json-file-input" accept=".json,application/json" style="display: none;">
                <button id="btn-trigger-file-upload" class="btn btn-secondary btn-sm">
                  📂 انتخاب فایل JSON از سیستم
                </button>
              </div>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-size: 0.85rem; font-weight: 700;">قالب‌های نمونه آماده:</span>
              <button id="btn-sample-array" class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">آرایه چند شهر (Array)</button>
              <button id="btn-sample-dict" class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">کلید-مقدار (Object/Dict)</button>
              <button id="btn-sample-fa" class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">تک شهر با کلید فارسی</button>
            </div>
            <div>
              <button id="btn-format-json" class="btn btn-secondary btn-sm" title="مرتب‌سازی و اعتبارسنجی سینتکس">
                🧹 مرتب‌سازی کد JSON
              </button>
            </div>
          </div>

          <div style="margin-bottom: 1rem;">
            <textarea id="json-editor-textarea" style="width: 100%; height: 260px; font-family: monospace; font-size: 0.85rem; direction: ltr; text-align: left; padding: 0.75rem; border-radius: 8px; border: 1px solid var(--border-color, #cbd5e1); background: #0f172a; color: #38bdf8; line-height: 1.5; resize: vertical;" spellcheck="false" placeholder="محتوای JSON شهرها را اینجا وارد کنید..."></textarea>
          </div>

          <!-- Preview & Action Bar -->
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; background: var(--bg-surface, #fff); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color, #e2e8f0);">
            <div id="json-preview-badge" style="font-size: 0.85rem; color: var(--text-secondary);">
              ✍️ متنی وارد نشده است.
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <label style="font-size: 0.8rem; display: flex; align-items: center; gap: 0.35rem; cursor: pointer;">
                <input type="checkbox" id="overwrite-existing-checkbox" checked>
                <span>به‌روزرسانی در صورت وجود شهر همنام</span>
              </label>
              <button id="btn-submit-json" class="btn btn-primary btn-sm">
                🚀 بارگذاری و ذخیره در دیتابیس
              </button>
            </div>
          </div>
        </div>

        <!-- Tab 3: Manual City Form -->
        <div id="section-manual-form" style="display: none;">
          <form id="city-manual-form" style="max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 1rem;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
              <div>
                <label style="display: block; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.35rem;">شناسه یکتا (اختیاری):</label>
                <input id="input-city-id" type="text" class="search-input" style="width: 100%; direction: ltr;" placeholder="مثال: tehran یا gorgan">
              </div>
              <div>
                <label style="display: block; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.35rem;">نام شهر (الزامی):</label>
                <input id="input-city-name" type="text" class="search-input" style="width: 100%;" placeholder="مثال: گرگان" required>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
              <div>
                <label style="display: block; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.35rem;">استان:</label>
                <input id="input-city-province" type="text" class="search-input" style="width: 100%;" placeholder="مثال: گلستان">
              </div>
              <div>
                <label style="display: block; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.35rem;">مبنای محاسبه:</label>
                <input id="input-calc-method" type="text" class="search-input" style="width: 100%;" value="مؤسسه ژئوفیزیک دانشگاه تهران">
              </div>
            </div>

            <div style="border-top: 1px solid var(--border-color, #e2e8f0); padding-top: 1rem;">
              <h5 style="margin: 0 0 0.75rem 0; font-size: 0.9rem; font-weight: 700;">ساعات اوقات شرعی (فرمت HH:MM به وقت محلی):</h5>
              
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem;">
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">اذان صبح:</label>
                  <input id="time-fajr" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="04:48" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">طلوع آفتاب:</label>
                  <input id="time-sunrise" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="06:12" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">اذان ظهر:</label>
                  <input id="time-dhuhr" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="11:52" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">اذان عصر:</label>
                  <input id="time-asr" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="15:08">
                </div>
              </div>

              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-top: 0.75rem;">
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">غروب آفتاب:</label>
                  <input id="time-sunset" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="17:31">
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">اذان مغرب:</label>
                  <input id="time-maghrib" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="17:49" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">اذان عشاء:</label>
                  <input id="time-isha" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="18:41">
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; margin-bottom: 0.2rem;">نیمه شب:</label>
                  <input id="time-midnight" type="text" class="search-input" style="width: 100%; direction: ltr; text-align: center;" placeholder="23:10">
                </div>
              </div>
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
              <button type="button" id="btn-cancel-manual" class="btn btn-secondary btn-sm">انصراف</button>
              <button type="submit" class="btn btn-primary btn-sm">💾 ذخیره مشخصات شهر</button>
            </div>
          </form>
        </div>

      </div>
    </div>
  `;

  // UI Element References
  const subtabList = container.querySelector('#subtab-list');
  const subtabJson = container.querySelector('#subtab-json');
  const subtabManual = container.querySelector('#subtab-manual');

  const secList = container.querySelector('#section-cities-list');
  const secJson = container.querySelector('#section-json-upload');
  const secManual = container.querySelector('#section-manual-form');

  const tableContainer = container.querySelector('#cities-table-container');
  const searchInput = container.querySelector('#cities-search-input');
  const statTotalCities = container.querySelector('#stat-total-cities');

  const jsonTextarea = container.querySelector('#json-editor-textarea');
  const jsonPreviewBadge = container.querySelector('#json-preview-badge');
  const fileInput = container.querySelector('#json-file-input');

  function switchTab(tab) {
    activeTab = tab;
    [subtabList, subtabJson, subtabManual].forEach(b => b.classList.remove('active'));
    secList.style.display = 'none';
    secJson.style.display = 'none';
    secManual.style.display = 'none';

    if (tab === 'list') {
      subtabList.classList.add('active');
      secList.style.display = 'block';
      loadCities();
    } else if (tab === 'json') {
      subtabJson.classList.add('active');
      secJson.style.display = 'block';
      if (!jsonTextarea.value.trim()) {
        jsonTextarea.value = SAMPLE_ARRAY_JSON;
        inspectJson();
      }
    } else if (tab === 'manual') {
      subtabManual.classList.add('active');
      secManual.style.display = 'block';
    }
  }

  subtabList.addEventListener('click', () => switchTab('list'));
  subtabJson.addEventListener('click', () => switchTab('json'));
  subtabManual.addEventListener('click', () => switchTab('manual'));
  container.querySelector('#btn-switch-to-json')?.addEventListener('click', () => switchTab('json'));

  // Load cities from backend
  async function loadCities() {
    citiesState.loading = true;
    renderCitiesGrid();

    try {
      const res = await ApiClient.get('/prayer-times', { q: citiesState.search });
      const items = res?.data?.items || [];
      citiesState.data = items;
      if (statTotalCities) {
        statTotalCities.textContent = formatNum(res?.data?.total ?? items.length);
      }
    } catch (err) {
      console.error('Failed to load prayer times:', err);
    } finally {
      citiesState.loading = false;
      renderCitiesGrid();
    }
  }

  // Render Cities Table
  function renderCitiesGrid() {
    renderTable({
      container: tableContainer,
      isLoading: citiesState.loading,
      data: citiesState.data,
      emptyMessage: 'هیچ شهری یافت نشد. می‌توانید با بارگذاری JSON یا افزودن دستی شهرها را وارد کنید.',
      columns: [
        {
          header: 'نام شهر و استان',
          render: (row) => `
            <div>
              <strong style="color: var(--text-primary);">${row.city_name}</strong>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">${row.province || '—'}</div>
            </div>
          `
        },
        {
          header: 'اذان صبح',
          render: (row) => `<span class="badge" style="background: rgba(99, 102, 241, 0.1); color: #4f46e5;" dir="ltr">${row.fajr || '—'}</span>`
        },
        {
          header: 'طلوع آفتاب',
          render: (row) => `<span dir="ltr" style="font-size: 0.85rem; color: #d97706;">${row.sunrise || '—'}</span>`
        },
        {
          header: 'اذان ظهر',
          render: (row) => `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #b45309; font-weight: 700;" dir="ltr">${row.dhuhr || '—'}</span>`
        },
        {
          header: 'اذان عصر',
          render: (row) => `<span dir="ltr" style="font-size: 0.85rem;">${row.asr || '—'}</span>`
        },
        {
          header: 'غروب',
          render: (row) => `<span dir="ltr" style="font-size: 0.85rem; color: #e11d48;">${row.sunset || '—'}</span>`
        },
        {
          header: 'اذان مغرب',
          render: (row) => `<span class="badge" style="background: rgba(147, 51, 234, 0.1); color: #7e22ce; font-weight: 700;" dir="ltr">${row.maghrib || '—'}</span>`
        },
        {
          header: 'اذان عشاء',
          render: (row) => `<span dir="ltr" style="font-size: 0.85rem;">${row.isha || '—'}</span>`
        },
        {
          header: 'نیمه‌شب',
          render: (row) => `<span dir="ltr" style="font-size: 0.85rem; color: var(--text-secondary);">${row.midnight || '—'}</span>`
        },
        {
          header: 'عملیات',
          render: (row) => `
            <div style="display: flex; gap: 0.35rem; align-items: center;">
              <button class="btn btn-secondary btn-sm action-view-city" data-id="${row.city_id}" title="مشاهده و ویرایش">
                ✏️
              </button>
              <button class="btn btn-secondary btn-sm action-delete-city" data-id="${row.city_id}" data-name="${row.city_name}" style="color: #ef4444;" title="حذف">
                🗑️
              </button>
            </div>
          `
        }
      ]
    });

    // Attach row events
    tableContainer.querySelectorAll('.action-view-city').forEach(btn => {
      btn.addEventListener('click', () => {
        const cityId = btn.getAttribute('data-id');
        const city = citiesState.data.find(c => c.city_id === cityId);
        if (city) openCityDrawer(city);
      });
    });

    tableContainer.querySelectorAll('.action-delete-city').forEach(btn => {
      btn.addEventListener('click', async () => {
        const cityId = btn.getAttribute('data-id');
        const cityName = btn.getAttribute('data-name');
        if (confirm(`آیا از حذف اوقات شرعی شهر «${cityName}» اطمینان دارید؟`)) {
          try {
            await ApiClient.delete(`/prayer-times/${cityId}`);
            Toast.success(`شهر «${cityName}» با موفقیت حذف شد.`);
            loadCities();
          } catch (err) {
            // Toast handled by ApiClient
          }
        }
      });
    });
  }

  // Open Slide-Over Drawer for viewing / editing single city
  function openCityDrawer(city) {
    Drawer.open({
      title: `اوقات شرعی: ${city.city_name}`,
      subtitle: `${city.province || 'ایران'} • شناسه: ${city.city_id}`,
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: 1rem; padding: 0.5rem 0;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div>
              <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">نام شهر:</label>
              <input id="drawer-city-name" class="search-input" style="width: 100%;" value="${city.city_name}">
            </div>
            <div>
              <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">استان:</label>
              <input id="drawer-city-province" class="search-input" style="width: 100%;" value="${city.province || ''}">
            </div>
          </div>

          <div style="border-top: 1px solid var(--border-color, #e2e8f0); padding-top: 0.75rem;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">اذان صبح:</label>
                <input id="drawer-fajr" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.fajr || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">طلوع آفتاب:</label>
                <input id="drawer-sunrise" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.sunrise || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">اذان ظهر:</label>
                <input id="drawer-dhuhr" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.dhuhr || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">اذان عصر:</label>
                <input id="drawer-asr" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.asr || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">غروب آفتاب:</label>
                <input id="drawer-sunset" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.sunset || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">اذان مغرب:</label>
                <input id="drawer-maghrib" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.maghrib || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">اذان عشاء:</label>
                <input id="drawer-isha" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.isha || ''}">
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block;">نیمه‌شب:</label>
                <input id="drawer-midnight" class="search-input" dir="ltr" style="width: 100%; text-align: center;" value="${city.midnight || ''}">
              </div>
            </div>
          </div>

          <div style="background: var(--bg-hover, #f1f5f9); padding: 0.75rem; border-radius: 8px; font-size: 0.8rem; color: var(--text-secondary);">
            <div><strong>مبنای محاسبه:</strong> ${city.calculation_method || 'مؤسسه ژئوفیزیک دانشگاه تهران'}</div>
            <div><strong>منبع داده:</strong> ${city.source || 'ثبت دستی / فایل JSON'}</div>
            <div><strong>آخرین به‌روزرسانی:</strong> ${formatDateTime(city.updated_at)}</div>
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <button id="drawer-btn-delete" class="btn btn-secondary btn-sm" style="color: #ef4444;">حذف شهر</button>
          <div style="display: flex; gap: 0.5rem;">
            <button id="drawer-btn-cancel" class="btn btn-secondary btn-sm">انصراف</button>
            <button id="drawer-btn-save" class="btn btn-primary btn-sm">💾 ذخیره تغییرات</button>
          </div>
        </div>
      `
    });

    const drawerBody = document.getElementById('drawer-body');
    const drawerFooter = document.getElementById('drawer-footer');

    drawerFooter?.querySelector('#drawer-btn-cancel')?.addEventListener('click', () => Drawer.close());

    drawerFooter?.querySelector('#drawer-btn-delete')?.addEventListener('click', async () => {
      if (confirm(`آیا مطمئن هستید می‌خواهید شهر «${city.city_name}» را حذف کنید؟`)) {
        try {
          await ApiClient.delete(`/prayer-times/${city.city_id}`);
          Toast.success(`شهر «${city.city_name}» حذف شد.`);
          Drawer.close();
          loadCities();
        } catch (err) {}
      }
    });

    drawerFooter?.querySelector('#drawer-btn-save')?.addEventListener('click', async () => {
      const updatedData = {
        city_id: city.city_id,
        city_name: drawerBody.querySelector('#drawer-city-name')?.value?.trim() || city.city_name,
        province: drawerBody.querySelector('#drawer-city-province')?.value?.trim(),
        fajr: drawerBody.querySelector('#drawer-fajr')?.value?.trim(),
        sunrise: drawerBody.querySelector('#drawer-sunrise')?.value?.trim(),
        dhuhr: drawerBody.querySelector('#drawer-dhuhr')?.value?.trim(),
        asr: drawerBody.querySelector('#drawer-asr')?.value?.trim(),
        sunset: drawerBody.querySelector('#drawer-sunset')?.value?.trim(),
        maghrib: drawerBody.querySelector('#drawer-maghrib')?.value?.trim(),
        isha: drawerBody.querySelector('#drawer-isha')?.value?.trim(),
        midnight: drawerBody.querySelector('#drawer-midnight')?.value?.trim()
      };

      try {
        await ApiClient.post('/prayer-times', updatedData);
        Toast.success(`تغییرات شهر «${updatedData.city_name}» با موفقیت ذخیره شد.`);
        Drawer.close();
        loadCities();
      } catch (err) {}
    });
  }

  // Live JSON validation & count inspector
  function inspectJson() {
    const text = jsonTextarea.value.trim();
    if (!text) {
      jsonPreviewBadge.innerHTML = '✍️ متنی وارد نشده است.';
      return null;
    }

    try {
      const parsed = JSON.parse(text);
      let count = 0;
      let cityNames = [];

      if (Array.isArray(parsed)) {
        count = parsed.length;
        cityNames = parsed.map(c => c.city_name || c.name || c['نام شهر'] || c.city || 'شهر بدون نام');
      } else if (typeof parsed === 'object' && parsed !== null) {
        if (parsed.city_name || parsed.name || parsed['نام شهر'] || parsed.fajr || parsed['اذان صبح']) {
          count = 1;
          cityNames = [parsed.city_name || parsed.name || parsed['نام شهر'] || 'تک‌شهر'];
        } else {
          const keys = Object.keys(parsed);
          count = keys.length;
          cityNames = keys.map(k => parsed[k]?.city_name || parsed[k]?.['نام شهر'] || k);
        }
      }

      jsonPreviewBadge.innerHTML = `
        <span style="color: #10b981; font-weight: 700;">✓ ساختار JSON معتبر است</span> — 
        شناسایی شده: <strong>${formatNum(count)} شهر</strong> 
        <span style="font-size: 0.75rem; color: var(--text-secondary);">(${cityNames.slice(0, 4).join('، ')}${count > 4 ? ' و...' : ''})</span>
      `;
      return parsed;
    } catch (err) {
      jsonPreviewBadge.innerHTML = `<span style="color: #ef4444; font-weight: 700;">✗ خطای ساختار JSON:</span> ${err.message}`;
      return null;
    }
  }

  jsonTextarea?.addEventListener('input', inspectJson);

  // Template switchers
  container.querySelector('#btn-sample-array')?.addEventListener('click', () => {
    jsonTextarea.value = SAMPLE_ARRAY_JSON;
    inspectJson();
  });
  container.querySelector('#btn-sample-dict')?.addEventListener('click', () => {
    jsonTextarea.value = SAMPLE_DICT_JSON;
    inspectJson();
  });
  container.querySelector('#btn-sample-fa')?.addEventListener('click', () => {
    jsonTextarea.value = SAMPLE_FA_JSON;
    inspectJson();
  });

  // Format JSON button
  container.querySelector('#btn-format-json')?.addEventListener('click', () => {
    const parsed = inspectJson();
    if (parsed) {
      jsonTextarea.value = JSON.stringify(parsed, null, 2);
      Toast.success('متن JSON با موفقیت مرتب شد.');
    } else {
      Toast.error('ابتدا خطای سینتکس JSON را برطرف کنید.');
    }
  });

  // File Upload Trigger
  const triggerBtn = container.querySelector('#btn-trigger-file-upload');
  triggerBtn?.addEventListener('click', () => fileInput?.click());

  fileInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      jsonTextarea.value = event.target.result;
      inspectJson();
      Toast.success(`فایل «${file.name}» با موفقیت خوانده شد.`);
    };
    reader.onerror = () => {
      Toast.error('خطا در خواندن فایل انتخاب شده.');
    };
    reader.readAsText(file, 'UTF-8');
  });

  // Submit JSON to server
  container.querySelector('#btn-submit-json')?.addEventListener('click', async () => {
    const parsed = inspectJson();
    if (!parsed) {
      Toast.error('لطفاً یک ساختار JSON معتبر وارد کنید.');
      return;
    }

    const overwrite = container.querySelector('#overwrite-existing-checkbox')?.checked ?? true;

    try {
      const res = await ApiClient.post('/prayer-times/upload-json', {
        data: parsed,
        overwrite_existing: overwrite
      });

      const count = res?.data?.count || 0;
      Toast.success(`تعداد ${formatNum(count)} شهر با موفقیت ذخیره و به‌روزرسانی شد.`);
      switchTab('list');
    } catch (err) {
      // ApiClient displays error toast
    }
  });

  // Export JSON
  container.querySelector('#btn-export-json')?.addEventListener('click', async () => {
    try {
      const res = await ApiClient.get('/prayer-times/export');
      const exportData = res?.data || [];
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `ettehad_prayer_times_${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      Toast.success('فایل JSON اوقات شرعی با موفقیت دانلود شد.');
    } catch (err) {
      Toast.error('خطا در استخراج فایل خروجی.');
    }
  });

  // Reset to Defaults
  container.querySelector('#btn-reset-defaults')?.addEventListener('click', async () => {
    if (confirm('آیا از بازنشانی کلیه اوقات شرعی به ۱۲ کلان‌شهر پیش‌فرض اطمینان دارید؟ تغییرات دستی بازنویسی خواهند شد.')) {
      try {
        const res = await ApiClient.post('/prayer-times/reset-defaults');
        Toast.success('اوقات شرعی با موفقیت به مقادیر پیش‌فرض بازنشانی شدند.');
        loadCities();
      } catch (err) {}
    }
  });

  // Search filter
  searchInput?.addEventListener('input', (e) => {
    citiesState.search = e.target.value.trim();
    loadCities();
  });

  container.querySelector('#btn-refresh-cities')?.addEventListener('click', () => loadCities());

  // Manual Form Submit
  const manualForm = container.querySelector('#city-manual-form');
  manualForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cityData = {
      city_id: container.querySelector('#input-city-id')?.value?.trim() || undefined,
      city_name: container.querySelector('#input-city-name')?.value?.trim(),
      province: container.querySelector('#input-city-province')?.value?.trim() || undefined,
      calculation_method: container.querySelector('#input-calc-method')?.value?.trim() || 'مؤسسه ژئوفیزیک دانشگاه تهران',
      fajr: container.querySelector('#time-fajr')?.value?.trim(),
      sunrise: container.querySelector('#time-sunrise')?.value?.trim(),
      dhuhr: container.querySelector('#time-dhuhr')?.value?.trim(),
      asr: container.querySelector('#time-asr')?.value?.trim() || undefined,
      sunset: container.querySelector('#time-sunset')?.value?.trim() || undefined,
      maghrib: container.querySelector('#time-maghrib')?.value?.trim(),
      isha: container.querySelector('#time-isha')?.value?.trim() || undefined,
      midnight: container.querySelector('#time-midnight')?.value?.trim() || undefined
    };

    try {
      await ApiClient.post('/prayer-times', cityData);
      Toast.success(`شهر «${cityData.city_name}» با موفقیت اضافه شد.`);
      manualForm.reset();
      switchTab('list');
    } catch (err) {}
  });

  container.querySelector('#btn-cancel-manual')?.addEventListener('click', () => {
    switchTab('list');
  });

  // Initial load
  loadCities();
}
