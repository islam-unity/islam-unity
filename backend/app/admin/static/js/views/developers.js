/**
 * View 8: Developers & System API (توسعه‌دهندگان و سیستم)
 * Developer accounts, API keys with revoke/activate fast actions, and system health status.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Toast } from '../components/toast.js';

export function renderDevelopers(container) {
  let activeTab = 'keys'; // 'keys' | 'accounts' | 'health'

  let keysState = { page: 1, pageSize: 10, data: [], meta: null };
  let accountsState = { page: 1, pageSize: 10, search: '', data: [], meta: null };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">🔑 پلتفرم توسعه‌دهندگان و پایش سلامت سیستم</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-dev-keys" class="subtab-btn active">کلیدهای دسترسی API (API Keys)</button>
          <button id="tab-dev-accounts" class="subtab-btn">حساب‌های توسعه‌دهنده (Accounts)</button>
          <button id="tab-dev-health" class="subtab-btn">پایش سلامت سیستم و زیرساخت</button>
        </div>

        <!-- Keys Section -->
        <div id="section-dev-keys">
          <div class="toolbar">
            <div class="toolbar-group">
              <span style="font-size: 0.85rem; color: var(--text-secondary);">
                مدیریت دسترسی‌ها، ابطال آنی یا فعال‌سازی کلیدهای اختصاصی اپلیکیشن‌ها
              </span>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-keys" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="keys-table-container"></div>
        </div>

        <!-- Accounts Section -->
        <div id="section-dev-accounts" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="accounts-search" type="text" class="search-input" placeholder="جستجو بر اساس نام اپلیکیشن یا توضیحات...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-accounts" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="accounts-table-container"></div>
        </div>

        <!-- Health Section -->
        <div id="section-dev-health" style="display: none;">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
            <button id="btn-refresh-health" class="btn btn-secondary btn-sm">⟳ بررسی مجدد سلامت سیستم</button>
          </div>
          <div id="health-container"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabKeys = container.querySelector('#tab-dev-keys');
  const tabAccounts = container.querySelector('#tab-dev-accounts');
  const tabHealth = container.querySelector('#tab-dev-health');
  const secKeys = container.querySelector('#section-dev-keys');
  const secAccounts = container.querySelector('#section-dev-accounts');
  const secHealth = container.querySelector('#section-dev-health');

  tabKeys.addEventListener('click', () => {
    activeTab = 'keys';
    tabKeys.classList.add('active');
    tabAccounts.classList.remove('active');
    tabHealth.classList.remove('active');
    secKeys.style.display = 'block';
    secAccounts.style.display = 'none';
    secHealth.style.display = 'none';
    fetchKeys();
  });

  tabAccounts.addEventListener('click', () => {
    activeTab = 'accounts';
    tabAccounts.classList.add('active');
    tabKeys.classList.remove('active');
    tabHealth.classList.remove('active');
    secKeys.style.display = 'none';
    secAccounts.style.display = 'block';
    secHealth.style.display = 'none';
    fetchAccounts();
  });

  tabHealth.addEventListener('click', () => {
    activeTab = 'health';
    tabHealth.classList.add('active');
    tabKeys.classList.remove('active');
    tabAccounts.classList.remove('active');
    secKeys.style.display = 'none';
    secAccounts.style.display = 'none';
    secHealth.style.display = 'block';
    fetchHealth();
  });

  container.querySelector('#btn-refresh-keys').addEventListener('click', fetchKeys);
  container.querySelector('#btn-refresh-accounts').addEventListener('click', fetchAccounts);
  container.querySelector('#btn-refresh-health').addEventListener('click', fetchHealth);

  // Keys Columns
  const keyColumns = [
    {
      header: 'عنوان کلید',
      render: (k) => `<span style="font-weight: 700;">${k.label || 'کلید بدون نام'}</span>`
    },
    {
      header: 'پیشوند کلید API',
      render: (k) => `<code style="background: #f1f5f9; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 600; color: #0f172a;">${k.keyPrefix || k.key_prefix || 'ett_live_...'}</code>`
    },
    {
      header: 'تعداد درخواست‌ها',
      render: (k) => formatNum(k.totalRequests ?? k.total_requests ?? 0)
    },
    {
      header: 'توکن‌های مصرفی',
      render: (k) => formatNum(k.totalTokens ?? k.total_tokens ?? 0)
    },
    {
      header: 'وضعیت',
      render: (k) => {
        const isActive = k.isActive ?? k.is_active ?? true;
        return isActive
          ? `<span id="key-st-${k.id}" class="badge badge-success">فعال ✓</span>`
          : `<span id="key-st-${k.id}" class="badge badge-danger">باطل شده</span>`;
      }
    },
    {
      header: 'آخرین استفاده',
      render: (k) => formatDateTime(k.lastUsedAt || k.last_used_at)
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (k) => {
        const isActive = k.isActive ?? k.is_active ?? true;
        return `
          <button id="btn-toggle-key-${k.id}" class="btn btn-sm ${isActive ? 'btn-danger' : 'btn-primary'} btn-toggle-key" data-key-id="${k.id}" data-current-active="${isActive}">
            ${isActive ? 'ابطال کلید (Revoke)' : 'فعال‌سازی مجدد'}
          </button>
        `;
      }
    }
  ];

  async function fetchKeys() {
    renderTable({
      container: container.querySelector('#keys-table-container'),
      columns: keyColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/developers/keys', {
        page: keysState.page,
        pageSize: keysState.pageSize
      });
      keysState.data = res.data || [];
      keysState.meta = res.meta;

      renderTable({
        container: container.querySelector('#keys-table-container'),
        columns: keyColumns,
        data: keysState.data,
        meta: keysState.meta,
        currentPage: keysState.page,
        pageSize: keysState.pageSize,
        emptyMessage: 'کلید دسترسی یافت نشد.',
        onPageChange: (p) => { keysState.page = p; fetchKeys(); },
        onPageSizeChange: (s) => { keysState.pageSize = s; keysState.page = 1; fetchKeys(); }
      });

      // Attach Toggle Key action
      container.querySelectorAll('.btn-toggle-key').forEach(btn => {
        btn.addEventListener('click', async () => {
          const keyId = btn.getAttribute('data-key-id');
          const currentActive = btn.getAttribute('data-current-active') === 'true';
          const newActive = !currentActive;

          btn.classList.add('loading');
          btn.disabled = true;

          try {
            await ApiClient.patch(`/developers/keys/${keyId}/status`, { is_active: newActive });
            const badge = container.querySelector(`#key-st-${keyId}`);

            if (newActive) {
              btn.textContent = 'ابطال کلید (Revoke)';
              btn.className = 'btn btn-sm btn-danger btn-toggle-key';
              btn.setAttribute('data-current-active', 'true');
              if (badge) {
                badge.textContent = 'فعال ✓';
                badge.className = 'badge badge-success';
              }
              Toast.success('کلید دسترسی API با موفقیت فعال شد.');
            } else {
              btn.textContent = 'فعال‌سازی مجدد';
              btn.className = 'btn btn-sm btn-primary btn-toggle-key';
              btn.setAttribute('data-current-active', 'false');
              if (badge) {
                badge.textContent = 'باطل شده';
                badge.className = 'badge badge-danger';
              }
              Toast.warning('کلید دسترسی API باطل گردید.');
            }
          } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
          }
        });
      });
    } catch (err) {
      container.querySelector('#keys-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // Accounts Columns
  const accountColumns = [
    {
      header: 'نام اپلیکیشن / برنامه',
      render: (a) => `
        <div>
          <div style="font-weight: 700;">${a.appName || a.app_name || 'بدون نام'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${a.description || 'بدون توضیح'}</div>
        </div>
      `
    },
    {
      header: 'سطح حساب (Tier)',
      render: (a) => `<span class="badge badge-purple">${a.tier || 'STANDARD'}</span>`
    },
    {
      header: 'سقف توکن ماهانه',
      render: (a) => formatNum(a.monthlyQuotaTokens ?? a.monthly_quota_tokens ?? 0)
    },
    {
      header: 'مصرف این ماه',
      render: (a) => formatNum(a.usedTokensThisMonth ?? a.used_tokens_this_month ?? 0)
    },
    {
      header: 'نرخ مجاز (Rate Limit)',
      render: (a) => `${formatNum(a.rateLimitPerMinute ?? a.rate_limit_per_minute ?? 60)} در دقیقه`
    },
    {
      header: 'وضعیت',
      render: (a) => (a.isActive ?? a.is_active)
        ? `<span class="badge badge-success">فعال</span>`
        : `<span class="badge badge-danger">غیرفعال</span>`
    }
  ];

  async function fetchAccounts() {
    renderTable({
      container: container.querySelector('#accounts-table-container'),
      columns: accountColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/developers/accounts', {
        page: accountsState.page,
        pageSize: accountsState.pageSize,
        search: accountsState.search
      });
      accountsState.data = res.data || [];
      accountsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#accounts-table-container'),
        columns: accountColumns,
        data: accountsState.data,
        meta: accountsState.meta,
        currentPage: accountsState.page,
        pageSize: accountsState.pageSize,
        emptyMessage: 'حساب توسعه‌دهنده‌ای یافت نشد.',
        onPageChange: (p) => { accountsState.page = p; fetchAccounts(); },
        onPageSizeChange: (s) => { accountsState.pageSize = s; accountsState.page = 1; fetchAccounts(); }
      });
    } catch (err) {
      container.querySelector('#accounts-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  // System Health
  async function fetchHealth() {
    const healthBox = container.querySelector('#health-container');
    healthBox.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
      const res = await ApiClient.get('/developers/system-health');
      const h = res.data || {};
      const db = h.database || {};
      const sys = h.system || {};
      const srv = h.services || {};

      healthBox.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem;">
          <div class="detail-section">
            <div class="detail-section-title">🗄️ پایگاه داده و ذخیره‌سازی</div>
            <div class="detail-row">
              <span class="detail-label">وضعیت اتصال:</span>
              <span class="badge ${db.status === 'connected' ? 'badge-success' : 'badge-danger'}">${db.status || 'connected'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">درایور پایگاه داده:</span>
              <span class="detail-value">${db.driver || 'aiosqlite/sqlite3'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">تعداد جداول مدیریت‌شده:</span>
              <span class="detail-value">${formatNum(db.managedTablesCount || 23)} جدول</span>
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">💻 محیط سیستم‌عامل سرور</div>
            <div class="detail-row">
              <span class="detail-label">سیستم‌عامل:</span>
              <span class="detail-value">${sys.os || 'Windows'} ${sys.release || ''}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">نسخه پایتون:</span>
              <span class="detail-value" style="font-family: monospace;">Python ${sys.pythonVersion || '3.11'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">وضعیت کلی:</span>
              <span class="badge ${h.status === 'healthy' ? 'badge-success' : 'badge-warning'}">${(h.status || 'healthy').toUpperCase()}</span>
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">⚡ ریزسرویس‌های متصل</div>
            <div class="detail-row">
              <span class="detail-label">موتور هوش مصنوعی (AI Engine):</span>
              <span class="badge badge-success">${srv.aiEngine || 'operational'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">پایگاه برداری Qdrant:</span>
              <span class="badge badge-success">${srv.vectorDb || 'connected'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">وب‌سوکت زمان‌واقعی:</span>
              <span class="badge badge-success">${srv.realtimeWs || 'operational'}</span>
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      healthBox.innerHTML = `<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در استعلام سلامت: ${err.message}</div></div>`;
    }
  }

  fetchKeys();
}
