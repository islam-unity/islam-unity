/**
 * View 2: Users & Personas (مدیریت کاربران و پرسونا)
 * Paginated table with multi-field search, quick status toggle, and lateral detail drawer.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderUsers(container) {
  let state = {
    page: 1,
    pageSize: 10,
    search: '',
    role: '',
    status: '', // '', 'true', 'false'
    data: [],
    meta: null,
    isLoading: false
  };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">👥 مدیریت کاربران و هویت</div>
        <span id="users-count-badge" class="badge badge-info">در حال بارگذاری...</span>
      </div>
      <div class="card-body">
        <!-- Toolbar -->
        <div class="toolbar">
          <div class="toolbar-group">
            <div class="search-input-wrap">
              <span class="search-icon">🔍</span>
              <input id="user-search" type="text" class="search-input" placeholder="جستجو بر اساس نام یا شماره همراه...">
            </div>

            <select id="user-filter-role" class="select-control">
              <option value="">همه نقش‌ها</option>
              <option value="SEEKER">سائل / کاربر عادی (SEEKER)</option>
              <option value="SCHOLAR">استاد / عالم (SCHOLAR)</option>
              <option value="ADMIN">مدیر ارشد (ADMIN)</option>
            </select>

            <select id="user-filter-status" class="select-control">
              <option value="">همه وضعیت‌ها</option>
              <option value="true">فقط فعال</option>
              <option value="false">فقط مسدود / معلق</option>
            </select>
          </div>

          <div class="toolbar-group">
            <button id="btn-refresh-users" class="btn btn-secondary btn-sm">
              ⟳ تازه‌سازی
            </button>
          </div>
        </div>

        <!-- Table Container -->
        <div id="users-table-container"></div>
      </div>
    </div>
  `;

  // Search input debounce
  let searchTimeout = null;
  const searchInput = container.querySelector('#user-search');
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      fetchUsers();
    }, 300);
  });

  // Role filter
  container.querySelector('#user-filter-role').addEventListener('change', (e) => {
    state.role = e.target.value;
    state.page = 1;
    fetchUsers();
  });

  // Status filter
  container.querySelector('#user-filter-status').addEventListener('change', (e) => {
    state.status = e.target.value;
    state.page = 1;
    fetchUsers();
  });

  // Refresh
  container.querySelector('#btn-refresh-users').addEventListener('click', () => {
    fetchUsers();
  });

  const columns = [
    {
      header: 'کاربر',
      render: (u) => `
        <div style="display: flex; align-items: center; gap: 0.65rem;">
          <div style="width: 34px; height: 34px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #475569; font-size: 0.85rem;">
            ${(u.fullName || u.full_name || 'کاربر').slice(0, 1)}
          </div>
          <div>
            <div style="font-weight: 600;">${u.fullName || u.full_name || 'بی‌نام'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-feature-settings: 'tnum';">${u.phoneNumber || u.phone_number || '—'}</div>
          </div>
        </div>
      `
    },
    {
      header: 'نقش کاربری',
      render: (u) => {
        const role = u.role || 'SEEKER';
        if (role === 'ADMIN') return `<span class="badge badge-danger">مدیر ارشد</span>`;
        if (role === 'SCHOLAR') return `<span class="badge badge-info">استاد / مبلغ</span>`;
        return `<span class="badge badge-neutral">سائل</span>`;
      }
    },
    {
      header: 'مذهب / سطح',
      render: (u) => {
        const madhhab = u.madhhab ? `مذهب: ${u.madhhab}` : 'عمومی';
        const level = u.knowledgeLevel || u.knowledge_level || '—';
        return `<div><div>${madhhab}</div><div style="font-size: 0.75rem; color: var(--text-muted);">${level}</div></div>`;
      }
    },
    {
      header: 'وضعیت حساب',
      render: (u) => {
        const isActive = u.isActive ?? u.is_active ?? true;
        return isActive
          ? `<span id="user-status-${u.id}" class="badge badge-success">فعال</span>`
          : `<span id="user-status-${u.id}" class="badge badge-danger">مسدود</span>`;
      }
    },
    {
      header: 'تاریخ عضویت',
      render: (u) => `<span style="font-size: 0.78rem;">${formatDateTime(u.createdAt || u.created_at)}</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (u) => {
        const isActive = u.isActive ?? u.is_active ?? true;
        return `
          <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
            <button class="btn btn-outline btn-sm btn-view-persona" data-user-id="${u.id}" title="مشاهده شناسنامه و پرسونا">
              👤 پرسونا
            </button>
            <button id="btn-toggle-${u.id}" class="btn btn-sm ${isActive ? 'btn-danger' : 'btn-primary'} btn-toggle-status" data-user-id="${u.id}" data-current-active="${isActive}">
              ${isActive ? 'مسدودسازی' : 'فعال‌سازی'}
            </button>
          </div>
        `;
      }
    }
  ];

  async function fetchUsers() {
    state.isLoading = true;
    renderTable({
      container: container.querySelector('#users-table-container'),
      columns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: state.page,
        pageSize: state.pageSize,
        search: state.search,
        role: state.role
      };
      if (state.status !== '') {
        params.is_active = state.status === 'true';
      }

      const res = await ApiClient.get('/users', params);
      state.data = res.data || [];
      state.meta = res.meta;

      const total = state.meta?.total !== undefined ? state.meta.total : (state.meta?.totalCount || state.data.length);
      const badge = container.querySelector('#users-count-badge');
      if (badge) badge.textContent = `${Number(total).toLocaleString('fa-IR')} کاربر ثبت‌شده`;

      renderTable({
        container: container.querySelector('#users-table-container'),
        columns,
        data: state.data,
        meta: state.meta,
        currentPage: state.page,
        pageSize: state.pageSize,
        emptyMessage: 'هیچ کاربری با فیلترهای مشخص‌شده یافت نشد.',
        onPageChange: (newPage) => {
          state.page = newPage;
          fetchUsers();
        },
        onPageSizeChange: (newSize) => {
          state.pageSize = newSize;
          state.page = 1;
          fetchUsers();
        }
      });

      attachRowActions();
    } catch (err) {
      container.querySelector('#users-table-container').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title" style="color: var(--danger);">خطا در دریافت کاربران: ${err.message}</div>
        </div>
      `;
    } finally {
      state.isLoading = false;
    }
  }

  function attachRowActions() {
    // 1. Quick status toggle buttons
    container.querySelectorAll('.btn-toggle-status').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = btn.getAttribute('data-user-id');
        const currentActive = btn.getAttribute('data-current-active') === 'true';
        const newActive = !currentActive;

        btn.classList.add('loading');
        btn.disabled = true;

        try {
          const res = await ApiClient.patch(`/users/${userId}/status`, { is_active: newActive });
          const updatedUser = res.data;
          const statusBadge = container.querySelector(`#user-status-${userId}`);

          if (newActive) {
            btn.textContent = 'مسدودسازی';
            btn.className = 'btn btn-sm btn-danger btn-toggle-status';
            btn.setAttribute('data-current-active', 'true');
            if (statusBadge) {
              statusBadge.textContent = 'فعال';
              statusBadge.className = 'badge badge-success';
            }
            Toast.success(`کاربر با موفقیت فعال گردید.`);
          } else {
            btn.textContent = 'فعال‌سازی';
            btn.className = 'btn btn-sm btn-primary btn-toggle-status';
            btn.setAttribute('data-current-active', 'false');
            if (statusBadge) {
              statusBadge.textContent = 'مسدود';
              statusBadge.className = 'badge badge-danger';
            }
            Toast.warning(`کاربر به حالت مسدود / معلق تغییر یافت.`);
          }
        } catch (err) {
          // Toast handled by ApiClient
        } finally {
          btn.classList.remove('loading');
          btn.disabled = false;
        }
      });
    });

    // 2. View persona detail drawer
    container.querySelectorAll('.btn-view-persona').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = btn.getAttribute('data-user-id');
        Drawer.open({
          title: 'شناسنامه کاربر و تنظیمات پرسونا',
          subtitle: `در حال دریافت اطلاعات کاربر ${userId}...`,
          contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
        });

        try {
          const res = await ApiClient.get(`/users/${userId}`);
          const u = res.data;
          const p = u.persona || {};

          Drawer.open({
            title: `شناسنامه: ${u.fullName || u.full_name || 'کاربر'}`,
            subtitle: `شماره تماس: ${u.phoneNumber || u.phone_number || '—'} | نقش: ${u.role}`,
            contentHtml: `
              <!-- User Demographic Details -->
              <div class="detail-section">
                <div class="detail-section-title">📋 مشخصات عمومی و هویتی</div>
                <div class="detail-row">
                  <span class="detail-label">شناسه یکتا</span>
                  <span class="detail-value" style="font-family: monospace; font-size: 0.8rem;">${u.id}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">سن / جنسیت</span>
                  <span class="detail-value">${u.age || '—'} سال / ${u.gender === 'MALE' ? 'مرد' : (u.gender === 'FEMALE' ? 'زن' : '—')}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">سطح تحصیلات</span>
                  <span class="detail-value">${u.education || '—'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">مذهب فقهی</span>
                  <span class="detail-value">${u.madhhab || 'عمومی'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">سطح دانش معارفی</span>
                  <span class="detail-value">${u.knowledgeLevel || u.knowledge_level || 'عمومی'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">اهداف یادگیری</span>
                  <span class="detail-value">${u.learningGoals || u.learning_goals || '—'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">علایق معارفی</span>
                  <span class="detail-value">${(u.interests && u.interests.length) ? u.interests.join('، ') : '—'}</span>
                </div>
              </div>

              <!-- Persona Config -->
              <div class="detail-section">
                <div class="detail-section-title">🤖 تنظیمات پرسونای اختصاصی هوش مصنوعی</div>
                <div class="detail-row">
                  <span class="detail-label">نام دستیار اختصاصی</span>
                  <span class="detail-value">${p.botName || p.bot_name || 'دستیار معارفی اتحاد'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">پریست نقش هوش مصنوعی</span>
                  <span class="detail-value">${p.botRolePreset || p.bot_role_preset || 'GENERAL_ASSISTANT'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">لحن پاسخگویی (Tone)</span>
                  <span class="detail-value">${p.tone || 'متین و علمی'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">رویکرد فقهی</span>
                  <span class="detail-value">${p.fiqhApproach || p.fiqh_approach || 'تقریب مذاهب اسلامی'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">سطح تفصیل پاسخ‌ها</span>
                  <span class="detail-value">${p.detailLevel || p.detail_level || 'استاندارد'}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">ارائه آدرس آیات و احادیث</span>
                  <span class="detail-value">${(p.includeAyahAddress ?? p.include_ayah_address) ? 'بله ✓' : 'خیر'}</span>
                </div>
                <div style="margin-top: 0.75rem;">
                  <span class="detail-label" style="display: block; margin-bottom: 0.25rem;">پرامپت و دستورالعمل اختصاصی:</span>
                  <div style="background: white; border: 1px solid var(--border-color); border-radius: 6px; padding: 0.65rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5;">
                    ${p.customPromptInstructions || p.custom_prompt_instructions || 'دستورالعمل خاصی تعریف نشده است.'}
                  </div>
                </div>
              </div>
            `,
            footerHtml: `
              <button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">
                بستن
              </button>
            `
          });
        } catch (err) {
          Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت شناسنامه: ${err.message}</div></div>`);
        }
      });
    });
  }

  fetchUsers();
}
