/**
 * View 1: Overview & Analytics (نمای کلی و آمار)
 * Displays key platform metrics, server health, and quick actions.
 */

import { ApiClient } from '../api.js';
import { formatNum } from '../components/table.js';

export async function renderOverview(container) {
  container.innerHTML = `
    <div class="card" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, #064e3b, #0f172a); color: white; border: none;">
      <div class="card-body" style="padding: 1.75rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h2 style="font-size: 1.4rem; font-weight: 700; margin-bottom: 0.5rem; color: #f8fafc;">
              داشبورد مدیریت پلتفرم معارفی و هوش مصنوعی «اتحاد»
            </h2>
            <p style="color: #cbd5e1; font-size: 0.9rem;">
              سامانه یکپارچه مانیتورینگ کاربران، پاسخ‌کده فقهی، کتابخانه معنایی، قرآن کریم و سرویس‌های هوش مصنوعی
            </p>
          </div>
          <button id="btn-refresh-overview" class="btn btn-outline" style="border-color: rgba(255,255,255,0.3); color: white;">
            <span>⟳ به‌روزرسانی آمار</span>
          </button>
        </div>
      </div>
    </div>

    <!-- KPI Cards Grid -->
    <div id="overview-kpi-grid" class="kpi-grid">
      <div class="kpi-card">
        <div class="spinner"></div>
        <div class="kpi-label">در حال بارگذاری شاخص‌ها...</div>
      </div>
    </div>

    <!-- Secondary Widgets -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1.5rem;">
      <!-- System Health Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🖥️ وضعیت سلامت سرویس‌ها و زیرساخت</div>
          <span class="badge badge-success">پایدار و برخط</span>
        </div>
        <div class="card-body">
          <div class="detail-section">
            <div class="detail-row">
              <span class="detail-label">پایگاه داده رابطه‌ای (SQLite Async)</span>
              <span id="health-db" class="detail-value" style="color: var(--success);">متصل ✓</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">موتور پردازش فرانت‌اند (Admin UI)</span>
              <span class="detail-value">Vanilla ES2022 Modules (Zero CDN)</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">موتور بک‌اند وب</span>
              <span class="detail-value">FastAPI 0.110+ (Starlette Core)</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">اندپوینت‌های داده‌ای</span>
              <span class="detail-value" style="direction: ltr;">/api/v1/admin</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">وضعیت کلی سرویس</span>
              <span id="health-status" class="badge badge-success">OPERATIONAL</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Navigation Shortcuts -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🚀 دسترسی سریع به بخش‌های اصلی</div>
        </div>
        <div class="card-body">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <a href="#users" class="btn btn-outline" style="justify-content: flex-start;">
              👥 مدیریت کاربران
            </a>
            <a href="#consultations" class="btn btn-outline" style="justify-content: flex-start;">
              💬 پاسخ‌کده و مشاوره
            </a>
            <a href="#library" class="btn btn-outline" style="justify-content: flex-start;">
              📚 کتابخانه و چانک‌ها
            </a>
            <a href="#quran" class="btn btn-outline" style="justify-content: flex-start;">
              📖 قرآن کریم و آیات
            </a>
            <a href="#ai" class="btn btn-outline" style="justify-content: flex-start;">
              🤖 چت و تعرفه هوش مصنوعی
            </a>
            <a href="#feed" class="btn btn-outline" style="justify-content: flex-start;">
              🛡️ گزارش‌های تخلف فید
            </a>
            <a href="#developers" class="btn btn-outline" style="justify-content: flex-start;">
              🔑 کلیدهای API توسعه‌دهنده
            </a>
            <a href="/docs" target="_blank" class="btn btn-outline" style="justify-content: flex-start;">
              📄 مستندات Swagger
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  // Attach refresh event
  const refreshBtn = container.querySelector('#btn-refresh-overview');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => loadData(container));
  }

  await loadData(container);
}

async function loadData(container) {
  const grid = container.querySelector('#overview-kpi-grid');
  if (!grid) return;

  try {
    const res = await ApiClient.get('/overview');
    const data = res.data || {};

    const totalUsers = data.totalUsers ?? data.total_users ?? 0;
    const totalScholars = data.totalScholars ?? data.total_scholars ?? 0;
    const openThreads = data.openThreads ?? data.open_threads ?? 0;
    const aiTokens = data.aiTokensConsumed ?? data.ai_tokens_consumed ?? 0;
    const contentReports = data.contentReportsCount ?? data.pendingReportsCount ?? data.totalReportsCount ?? 0;

    grid.innerHTML = `
      <div class="kpi-card">
        <div class="kpi-icon-wrap emerald">👥</div>
        <div class="kpi-content">
          <div class="kpi-label">کل کاربران سامانه</div>
          <div class="kpi-value">${formatNum(totalUsers)}</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap blue">🎓</div>
        <div class="kpi-content">
          <div class="kpi-label">اساتید و مبلغان</div>
          <div class="kpi-value">${formatNum(totalScholars)}</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap amber">💬</div>
        <div class="kpi-content">
          <div class="kpi-label">تریدهای باز مشاوره</div>
          <div class="kpi-value">${formatNum(openThreads)}</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap purple">🤖</div>
        <div class="kpi-content">
          <div class="kpi-label">توکن‌های مصرفی هوش مصنوعی</div>
          <div class="kpi-value">${formatNum(aiTokens)}</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap red">🛡️</div>
        <div class="kpi-content">
          <div class="kpi-label">گزارش‌های تخلف نیازمند بررسی</div>
          <div class="kpi-value">${formatNum(contentReports)}</div>
        </div>
      </div>
    `;

    const healthDb = container.querySelector('#health-db');
    const healthStatus = container.querySelector('#health-status');
    if (data.systemHealth) {
      if (healthDb) healthDb.textContent = data.systemHealth.database === 'connected' ? 'متصل ✓' : 'قطع ✗';
      if (healthStatus) healthStatus.textContent = (data.systemHealth.status || 'healthy').toUpperCase();
    }
  } catch (err) {
    grid.innerHTML = `
      <div class="kpi-card" style="grid-column: 1 / -1; border-color: var(--danger-border); background-color: var(--danger-bg);">
        <div class="kpi-label" style="color: var(--danger-text);">خطا در دریافت آمار داشبورد: ${err.message}</div>
      </div>
    `;
  }
}
