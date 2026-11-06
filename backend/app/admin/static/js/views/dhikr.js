/**
 * View: Dhikr & Supplications Management (ادعیه، اذکار و دسته‌بندی‌های شمارش)
 * Allows admins to view, create, edit, and delete supplications across custom & system categories.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderDhikr(container) {
  let state = {
    selectedCategory: 'all',
    search: '',
    items: [],
    categories: [],
    loading: false
  };

  container.innerHTML = `
    <!-- Top Stats Overview -->
    <div class="stats-grid" style="margin-bottom: 1.5rem;">
      <div class="stat-card">
        <div class="stat-label">تعداد کل ادعیه و اذکار</div>
        <div id="stat-total-dhikrs" class="stat-value" style="color: #0284c7;">--</div>
        <div class="stat-change">بانک جامع اذکار معتبر و شخصی</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">دسته‌بندی‌های فعال</div>
        <div id="stat-total-categories" class="stat-value" style="color: #8b5cf6;">--</div>
        <div class="stat-change">ایام هفته، تعقیبات، حاجات، مناجات و...</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">اذکار رسمی سیستمی</div>
        <div id="stat-system-dhikrs" class="stat-value" style="color: #10b981;">--</div>
        <div class="stat-change">دارای استناد و مأخذ روایی دقیق</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">اذکار اضافه شده کاربران</div>
        <div id="stat-custom-dhikrs" class="stat-value" style="color: #f59e0b;">--</div>
        <div class="stat-change">ثبت شده از طریق اپلیکیشن موبایل</div>
      </div>
    </div>

    <!-- Main Card -->
    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div class="card-title">📿 مدیریت ادعیه، اذکار و دسته‌بندی‌های شمارنده</div>
        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
          <button id="btn-add-dhikr" class="btn btn-primary btn-sm">
            ➕ افزودن دعا یا ذکر جدید
          </button>
          <button id="btn-manage-categories" class="btn btn-secondary btn-sm">
            📁 مدیریت دسته‌بندی‌ها
          </button>
          <button id="btn-seed-dhikrs" class="btn btn-secondary btn-sm" style="color: #b45309;" title="بازنشانی اذکار پیش‌فرض">
            ↺ بارگذاری اذکار پیش‌فرض
          </button>
        </div>
      </div>

      <div class="card-body">
        <!-- Category Filter Pills -->
        <div id="category-pills-bar" style="display: flex; gap: 0.5rem; overflow-x: auto; padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <button class="subtab-btn active" data-cat="all">همه اذکار</button>
        </div>

        <!-- Search Toolbar -->
        <div class="toolbar" style="margin-bottom: 1.25rem;">
          <div class="toolbar-group">
            <div class="search-input-wrap" style="width: 320px;">
              <span class="search-icon">🔍</span>
              <input id="dhikr-search-input" type="text" class="search-input" placeholder="جستجو در عنوان، متن عربی یا ترجمه...">
            </div>
          </div>
          <div class="toolbar-group">
            <button id="btn-refresh-dhikrs" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
          </div>
        </div>

        <!-- Data Table Container -->
        <div id="dhikr-table-container">
          <div class="loading-container">
            <div class="spinner"></div>
            <div>در حال دریافت ادعیه و اذکار...</div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Attach Top Action Event Listeners
  const btnAddDhikr = container.querySelector('#btn-add-dhikr');
  const btnManageCats = container.querySelector('#btn-manage-categories');
  const btnSeed = container.querySelector('#btn-seed-dhikrs');
  const btnRefresh = container.querySelector('#btn-refresh-dhikrs');
  const searchInput = container.querySelector('#dhikr-search-input');

  btnAddDhikr.addEventListener('click', () => openAddOrEditDhikrDrawer(null));
  btnManageCats.addEventListener('click', () => openManageCategoriesDrawer());
  btnRefresh.addEventListener('click', () => loadData());

  btnSeed.addEventListener('click', async () => {
    if (!confirm('آیا مایلید اذکار و دسته‌بندی‌های استاندارد معارفی پیش‌فرض مجدداً بررسی و همگام شوند؟')) return;
    try {
      const res = await ApiClient.post('/dhikr/seed');
      Toast.success(res.meta?.message || 'اذکار پیش‌فرض با موفقیت بارگذاری شدند.');
      loadData();
    } catch (e) {
      console.error(e);
    }
  });

  let searchTimeout = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.search = e.target.value.trim();
      loadData();
    }, 300);
  });

  // Load Data function
  async function loadData() {
    state.loading = true;
    try {
      const params = {};
      if (state.selectedCategory && state.selectedCategory !== 'all') {
        params.category = state.selectedCategory;
      }
      if (state.search) {
        params.q = state.search;
      }

      const res = await ApiClient.get('/dhikr', params);
      const data = res.data || {};
      state.items = data.items || [];
      state.categories = data.categories || [];

      updateStats();
      renderCategoryPills();
      renderDhikrTable();
    } catch (err) {
      console.error('Error fetching dhikrs:', err);
      container.querySelector('#dhikr-table-container').innerHTML = `
        <div style="text-align: center; padding: 2rem; color: #ef4444;">
          خطا در دریافت اطلاعات ادعیه و اذکار. لطفا مجددا تلاش کنید.
        </div>
      `;
    } finally {
      state.loading = false;
    }
  }

  function updateStats() {
    const total = state.items.length;
    const catsCount = state.categories.length;
    const systemCount = state.items.filter(i => i.is_system).length;
    const customCount = total - systemCount;

    const elTotal = container.querySelector('#stat-total-dhikrs');
    const elCats = container.querySelector('#stat-total-categories');
    const elSys = container.querySelector('#stat-system-dhikrs');
    const elCust = container.querySelector('#stat-custom-dhikrs');

    if (elTotal) elTotal.textContent = formatNum(total);
    if (elCats) elCats.textContent = formatNum(catsCount);
    if (elSys) elSys.textContent = formatNum(systemCount);
    if (elCust) elCust.textContent = formatNum(customCount);
  }

  function renderCategoryPills() {
    const pillsBar = container.querySelector('#category-pills-bar');
    if (!pillsBar) return;

    let html = `<button class="subtab-btn ${state.selectedCategory === 'all' ? 'active' : ''}" data-cat="all">🌟 همه (${state.items.length})</button>`;
    
    state.categories.forEach(cat => {
      const count = state.items.filter(i => i.category === cat.id).length;
      const isActive = state.selectedCategory === cat.id;
      html += `
        <button class="subtab-btn ${isActive ? 'active' : ''}" data-cat="${cat.id}">
          ${cat.title} ${count > 0 ? `(${count})` : ''}
        </button>
      `;
    });

    pillsBar.innerHTML = html;

    pillsBar.querySelectorAll('.subtab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.selectedCategory = btn.getAttribute('data-cat');
        renderCategoryPills();
        loadData();
      });
    });
  }

  function renderDhikrTable() {
    const tableContainer = container.querySelector('#dhikr-table-container');
    if (!tableContainer) return;

    if (state.items.length === 0) {
      tableContainer.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-secondary, #64748b);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📿</div>
          <div style="font-weight: 700; margin-bottom: 0.25rem;">هیچ دعا یا ذکری یافت نشد</div>
          <div style="font-size: 0.85rem;">برای افزودن ذکر جدید روی دکمه «افزودن دعا یا ذکر جدید» کلیک کنید.</div>
        </div>
      `;
      return;
    }

    const columns = [
      {
        header: '#',
        render: (row, idx) => `<span style="font-size: 0.8rem; color: #94a3b8;">${idx + 1}</span>`
      },
      {
        header: 'عنوان دعا و دسته‌بندی',
        render: (row) => `
          <div>
            <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem;">${escapeHtml(row.title)}</div>
            <div style="font-size: 0.75rem;">
              <span class="badge" style="background: rgba(14, 165, 233, 0.1); color: #0284c7; border: 1px solid rgba(14, 165, 233, 0.25); border-radius: 4px; padding: 2px 6px;">
                ${escapeHtml(row.category_title || row.category)}
              </span>
            </div>
          </div>
        `
      },
      {
        header: 'متن عربی ذکر',
        render: (row) => `
          <div style="font-family: 'Amiri', 'Traditional Arabic', serif; font-size: 1.15rem; font-weight: 600; color: #0f172a; direction: rtl; max-width: 380px; line-height: 1.6;">
            ${escapeHtml(row.arabic_text)}
          </div>
          ${row.translation ? `<div style="font-size: 0.78rem; color: #64748b; margin-top: 0.25rem; max-width: 380px;">${escapeHtml(row.translation)}</div>` : ''}
        `
      },
      {
        header: 'هدف شمارش',
        render: (row) => `
          <div style="text-align: center;">
            <span style="font-weight: 800; font-size: 1.1rem; color: #059669;">${formatNum(row.target_count || 100)}</span>
            <div style="font-size: 0.7rem; color: #64748b;">مرتبه</div>
          </div>
        `
      },
      {
        header: 'فضیلت و مأخذ روایی',
        render: (row) => `
          <div style="font-size: 0.8rem; max-width: 250px;">
            <div style="color: #475569; margin-bottom: 0.25rem;">${escapeHtml(row.virtue || '—')}</div>
            <div style="font-size: 0.72rem; color: #94a3b8;">منبع: ${escapeHtml(row.source || 'مفاتیح‌الجنان')}</div>
          </div>
        `
      },
      {
        header: 'نوع ذکر',
        render: (row) => row.is_system
          ? `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #059669; border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 3px 8px; font-size: 0.75rem;">سیستمی رسمی</span>`
          : `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 6px; padding: 3px 8px; font-size: 0.75rem;">کاربر (${escapeHtml(row.user_id || 'نامشخص')})</span>`
      },
      {
        header: 'عملیات',
        render: (row) => `
          <div style="display: flex; gap: 0.35rem; align-items: center;">
            <button class="btn btn-secondary btn-sm btn-edit-dhikr" data-id="${row.id}" title="ویرایش مشخصات" style="padding: 4px 8px;">
              ✏️ ویرایش
            </button>
            <button class="btn btn-secondary btn-sm btn-del-dhikr" data-id="${row.id}" title="حذف" style="padding: 4px 8px; color: #ef4444;">
              🗑️
            </button>
          </div>
        `
      }
    ];

    renderTable(tableContainer, {
      columns,
      data: state.items
    });

    // Attach row action handlers
    tableContainer.querySelectorAll('.btn-edit-dhikr').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const item = state.items.find(i => i.id === id);
        if (item) openAddOrEditDhikrDrawer(item);
      });
    });

    tableContainer.querySelectorAll('.btn-del-dhikr').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const item = state.items.find(i => i.id === id);
        if (!item) return;

        if (!confirm(`آیا از حذف دعای «${item.title}» اطمینان دارید؟`)) return;

        try {
          await ApiClient.request(`/dhikr/${id}`, { method: 'DELETE' });
          Toast.success('ذکر مورد نظر با موفقیت حذف شد.');
          loadData();
        } catch (err) {
          console.error(err);
        }
      });
    });
  }

  // Drawer for Adding or Editing Dhikr
  function openAddOrEditDhikrDrawer(existingItem = null) {
    const isEdit = !!existingItem;
    const title = isEdit ? `ویرایش دعا: ${existingItem.title}` : '➕ افزودن دعا یا ذکر جدید به سامانه';
    const subtitle = isEdit ? 'تغییر متن، ترجمه، هدف شمارش یا دسته‌بندی' : 'افزودن به دسته‌بندی‌های پیش‌فرض با قابلیت استفاده در صلوات‌شمار';

    let categoryOptionsHtml = '';
    state.categories.forEach(cat => {
      const selected = (existingItem?.category === cat.id) ? 'selected' : '';
      categoryOptionsHtml += `<option value="${cat.id}" ${selected}>${cat.title} (${cat.id})</option>`;
    });

    const bodyHtml = `
      <form id="dhikr-form" style="display: flex; flex-direction: column; gap: 1rem;">
        <div class="form-group">
          <label class="form-label" for="form-dhikr-title" style="font-weight: 700;">عنوان ذکر یا نام دعا <span style="color: #ef4444;">*</span></label>
          <input id="form-dhikr-title" type="text" class="form-input" required placeholder="مثال: ذکر روز یکشنبه، دعای فرج، تسبیحات حضرت زهرا..." value="${escapeHtml(existingItem?.title || '')}">
        </div>

        <div class="form-group">
          <label class="form-label" for="form-dhikr-arabic" style="font-weight: 700;">متن عربی ذکر <span style="color: #ef4444;">*</span></label>
          <textarea id="form-dhikr-arabic" class="form-input" rows="3" required placeholder="متن کامل یا فراز دعا با اعراب‌گذاری عربی..." style="font-family: 'Amiri', 'Traditional Arabic', serif; font-size: 1.15rem; line-height: 1.7;">${escapeHtml(existingItem?.arabic_text || '')}</textarea>
        </div>

        <div class="form-group">
          <label class="form-label" for="form-dhikr-trans">ترجمه فارسی روان یا مفهوم</label>
          <textarea id="form-dhikr-trans" class="form-input" rows="2" placeholder="ترجمه فارسی جهت درک بهتر معارف ذکر...">${escapeHtml(existingItem?.translation || '')}</textarea>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div class="form-group">
            <label class="form-label" for="form-dhikr-cat" style="font-weight: 700;">دسته‌بندی <span style="color: #ef4444;">*</span></label>
            <select id="form-dhikr-cat" class="form-select" required>
              ${categoryOptionsHtml}
              <option value="__NEW__">➕ ایجاد دسته‌بندی جدید...</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="form-dhikr-count" style="font-weight: 700;">تعداد دور هدف شمارش</label>
            <input id="form-dhikr-count" type="number" min="1" max="100000" class="form-input" value="${existingItem?.target_count || 100}">
          </div>
        </div>

        <div id="new-category-box" style="display: none; background: rgba(14, 165, 233, 0.05); border: 1px dashed #0284c7; border-radius: 8px; padding: 0.75rem;">
          <div class="form-group" style="margin-bottom: 0.5rem;">
            <label class="form-label" for="form-new-cat-id" style="font-size: 0.8rem;">شناسه انگلیسی دسته جدید</label>
            <input id="form-new-cat-id" type="text" class="form-input" placeholder="مثال: ramadan, shaban, morning">
          </div>
          <div class="form-group">
            <label class="form-label" for="form-new-cat-title" style="font-size: 0.8rem;">عنوان فارسی دسته جدید</label>
            <input id="form-new-cat-title" type="text" class="form-input" placeholder="مثال: اعمال ماه رجب و شعبان">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="form-dhikr-virtue">فضیلت و پاداش معنوی ذکر</label>
          <input id="form-dhikr-virtue" type="text" class="form-input" placeholder="مثال: موجب وسعت رزق، آرامش دل‌ها، استجابت دعا..." value="${escapeHtml(existingItem?.virtue || '')}">
        </div>

        <div class="form-group">
          <label class="form-label" for="form-dhikr-source">منبع یا مأخذ روایی</label>
          <input id="form-dhikr-source" type="text" class="form-input" placeholder="مثال: مفاتیح الجنان، اصول کافی، بحارالانوار..." value="${escapeHtml(existingItem?.source || '')}">
        </div>
      </form>
    `;

    Drawer.open({
      title,
      subtitle,
      body: bodyHtml,
      footer: `
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <button id="drawer-cancel-btn" class="btn btn-secondary">انصراف</button>
          <button id="drawer-save-btn" class="btn btn-primary">
            💾 ${isEdit ? 'ذخیره تغییرات' : 'افزودن به بانک ادعیه'}
          </button>
        </div>
      `
    });

    const selectCat = document.querySelector('#form-dhikr-cat');
    const newCatBox = document.querySelector('#new-category-box');
    selectCat.addEventListener('change', () => {
      newCatBox.style.display = selectCat.value === '__NEW__' ? 'block' : 'none';
    });

    document.querySelector('#drawer-cancel-btn').addEventListener('click', () => {
      Drawer.close();
    });

    document.querySelector('#drawer-save-btn').addEventListener('click', async () => {
      const titleVal = document.querySelector('#form-dhikr-title').value.trim();
      const arabicVal = document.querySelector('#form-dhikr-arabic').value.trim();
      const transVal = document.querySelector('#form-dhikr-trans').value.trim();
      let catVal = document.querySelector('#form-dhikr-cat').value;
      const countVal = parseInt(document.querySelector('#form-dhikr-count').value, 10) || 100;
      const virtueVal = document.querySelector('#form-dhikr-virtue').value.trim();
      const sourceVal = document.querySelector('#form-dhikr-source').value.trim();

      if (!titleVal || !arabicVal) {
        Toast.error('لطفاً عنوان و متن عربی ذکر را وارد فرمایید.');
        return;
      }

      let categoryTitle = '';
      if (catVal === '__NEW__') {
        const newCatId = document.querySelector('#form-new-cat-id').value.trim();
        const newCatTitle = document.querySelector('#form-new-cat-title').value.trim();
        if (!newCatId || !newCatTitle) {
          Toast.error('لطفاً شناسه و عنوان دسته‌بندی جدید را وارد نمایید.');
          return;
        }
        // Create category first
        try {
          await ApiClient.post('/dhikr/categories', {
            id: newCatId,
            title: newCatTitle,
            icon: 'counter_3',
            display_order: 10
          });
          catVal = newCatId;
          categoryTitle = newCatTitle;
        } catch (e) {
          return;
        }
      } else {
        const found = state.categories.find(c => c.id === catVal);
        categoryTitle = found ? found.title : '';
      }

      const payload = {
        title: titleVal,
        arabic_text: arabicVal,
        translation: transVal,
        category: catVal,
        category_title: categoryTitle,
        target_count: countVal,
        virtue: virtueVal,
        source: sourceVal
      };

      try {
        if (isEdit) {
          await ApiClient.put(`/dhikr/${existingItem.id}`, payload);
          Toast.success('تغییرات ذکر با موفقیت ذخیره شد.');
        } else {
          await ApiClient.post('/dhikr', payload);
          Toast.success('دعا و ذکر جدید با موفقیت اضافه شد.');
        }
        Drawer.close();
        loadData();
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Drawer for Managing Categories
  function openManageCategoriesDrawer() {
    let listHtml = '';
    state.categories.forEach(cat => {
      const count = state.items.filter(i => i.category === cat.id).length;
      listHtml += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border-bottom: 1px solid var(--border-color, #e2e8f0);">
          <div>
            <div style="font-weight: 700; color: var(--text-primary);">${escapeHtml(cat.title)}</div>
            <div style="font-size: 0.75rem; color: #64748b;">
              شناسه: <code>${escapeHtml(cat.id)}</code> • شامل ${formatNum(count)} ذکر
            </div>
            ${cat.description ? `<div style="font-size: 0.73rem; color: #94a3b8; margin-top: 2px;">${escapeHtml(cat.description)}</div>` : ''}
          </div>
          <div>
            <span class="badge" style="background: rgba(14, 165, 233, 0.1); color: #0284c7; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
              ترتیب: ${cat.display_order || 0}
            </span>
          </div>
        </div>
      `;
    });

    const bodyHtml = `
      <div style="margin-bottom: 1.5rem;">
        <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 700;">فهرست دسته‌بندی‌های موجود:</h4>
        <div style="background: var(--bg-card, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px;">
          ${listHtml}
        </div>
      </div>

      <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 1rem;">
        <h4 style="margin: 0 0 0.75rem 0; font-size: 0.95rem; font-weight: 700; color: #059669;">➕ افزودن دسته‌بندی جدید:</h4>
        <div class="form-group" style="margin-bottom: 0.75rem;">
          <label class="form-label" for="add-cat-id">شناسه انگلیسی دسته (ID) <span style="color: #ef4444;">*</span></label>
          <input id="add-cat-id" type="text" class="form-input" placeholder="مثال: rajab, shaban, zekr_hajat">
        </div>
        <div class="form-group" style="margin-bottom: 0.75rem;">
          <label class="form-label" for="add-cat-title">عنوان فارسی دسته <span style="color: #ef4444;">*</span></label>
          <input id="add-cat-title" type="text" class="form-input" placeholder="مثال: ادعیه و اعمال ماه رجب المرجب">
        </div>
        <div class="form-group" style="margin-bottom: 0.75rem;">
          <label class="form-label" for="add-cat-desc">توضیحات مختصر</label>
          <input id="add-cat-desc" type="text" class="form-input" placeholder="توضیح کوتاه درباره ماهیت اذکار این دسته">
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
          <div class="form-group">
            <label class="form-label" for="add-cat-icon">آیکون</label>
            <input id="add-cat-icon" type="text" class="form-input" value="counter_3">
          </div>
          <div class="form-group">
            <label class="form-label" for="add-cat-order">ترتیب نمایش</label>
            <input id="add-cat-order" type="number" class="form-input" value="${state.categories.length + 1}">
          </div>
        </div>
        <button id="btn-save-new-cat" class="btn btn-primary" style="margin-top: 1rem; width: 100%;">
          ✨ ثبت و ذخیره دسته‌بندی
        </button>
      </div>
    `;

    Drawer.open({
      title: '📁 مدیریت دسته‌بندی‌های ادعیه و اذکار',
      subtitle: 'تعریف دسته‌های موضوعی برای دسته‌بندی شمارنده‌ها در اپلیکیشن',
      body: bodyHtml,
      footer: `
        <button id="drawer-cat-close-btn" class="btn btn-secondary" style="width: 100%;">بستن</button>
      `
    });

    document.querySelector('#drawer-cat-close-btn').addEventListener('click', () => {
      Drawer.close();
    });

    document.querySelector('#btn-save-new-cat').addEventListener('click', async () => {
      const id = document.querySelector('#add-cat-id').value.trim();
      const catTitle = document.querySelector('#add-cat-title').value.trim();
      const desc = document.querySelector('#add-cat-desc').value.trim();
      const icon = document.querySelector('#add-cat-icon').value.trim() || 'counter_3';
      const order = parseInt(document.querySelector('#add-cat-order').value, 10) || 0;

      if (!id || !catTitle) {
        Toast.error('شناسه و عنوان دسته‌بندی الزامی هستند.');
        return;
      }

      try {
        await ApiClient.post('/dhikr/categories', {
          id,
          title: catTitle,
          description: desc,
          icon,
          display_order: order
        });
        Toast.success('دسته‌بندی جدید با موفقیت ایجاد شد.');
        Drawer.close();
        loadData();
      } catch (e) {
        console.error(e);
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Initial Data Load
  loadData();
}
