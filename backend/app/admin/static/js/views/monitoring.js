/**
 * View: Live Monitoring & System Health (مانیتورینگ زنده و جلسات حضوری)
 * Displays live server health, CPU/RAM stats, database status, and meetings management.
 */

import { ApiClient } from '../api.js';
import { formatNum, renderTable } from '../components/table.js';
import { Toast } from '../components/toast.js';

let refreshTimer = null;

export async function renderMonitoring(container) {
  // Clear any existing timer
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }

  container.innerHTML = `
    <!-- Top Action / Info Banner -->
    <div class="card" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, #0f172a, #1e293b); color: white; border: 1px solid rgba(255,255,255,0.1);">
      <div class="card-body" style="padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
              <span class="status-dot"></span>
              <h2 style="font-size: 1.3rem; font-weight: 700; color: #f8fafc; margin: 0;">
                مرکز پایش و مانیتورینگ زنده سامانه اتحاد
              </h2>
            </div>
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">
              سلامت هسته سرور، مصرف منابع پردازشی، توزیع جغرافیایی و مدیریت قرارهای ملاقات حضوری با علما
            </p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button id="btn-refresh-monitoring" class="btn btn-outline" style="border-color: rgba(255,255,255,0.25); color: #f8fafc;">
              <span>⟳ به‌روزرسانی آنی</span>
            </button>
            <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #10b981; background: rgba(16,185,129,0.1); padding: 0.4rem 0.8rem; rounded: 8px; border-radius: 8px;">
              <span>برخط (Auto-Refresh فعال)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Live KPI Metrics Grid -->
    <div id="monitoring-kpi-grid" class="kpi-grid" style="margin-bottom: 1.5rem;">
      <div class="kpi-card">
        <div class="spinner"></div>
        <div class="kpi-label">در حال سنجش وضعیت سرور...</div>
      </div>
    </div>

    <!-- 2-Column Section: Server Health & Services -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
      <!-- Services Health Box -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🛡️ وضعیت و زمان پاسخ‌دهی میکرو‌سرویس‌ها</div>
          <span class="badge badge-success">تمام سرویس‌ها فعال</span>
        </div>
        <div class="card-body" style="padding: 1rem;">
          <div id="monitoring-services-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="color: var(--text-muted); font-size: 0.85rem;">در حال بررسی سلامت سرویس‌ها...</div>
          </div>
        </div>
      </div>

      <!-- Live Logs Stream -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">📝 رخدادها و لاگ‌های زنده سرور</div>
          <span style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">FastAPI STDOUT</span>
        </div>
        <div class="card-body" style="padding: 1rem;">
          <div id="monitoring-logs-list" style="background: #0f172a; color: #cbd5e1; border-radius: 8px; padding: 0.75rem; font-family: monospace; font-size: 0.78rem; max-height: 230px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem;">
            <div>[System] در حال دریافت آخرین لاگ‌ها...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Scholar Appointments & Meetings Management Section -->
    <div class="card">
      <div class="card-header" style="flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <div class="card-title">🤝 مدیریت وقت‌های دیدار و مشاوره حضوری با علما</div>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin: 0.25rem 0 0 0;">
            لیست درخواست‌های ملاقات ثبت‌شده توسط کاربران بر اساس موقعیت مکانی و دفاتر اساتید
          </p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <select id="meeting-filter-status" class="form-input" style="width: auto; font-size: 0.8rem; padding: 0.35rem 0.75rem;">
            <option value="">همه وضعیت‌ها</option>
            <option value="PENDING">در انتظار بررسی (PENDING)</option>
            <option value="CONFIRMED">تأیید شده (CONFIRMED)</option>
            <option value="COMPLETED">برگزار شده (COMPLETED)</option>
            <option value="CANCELLED">لغو شده (CANCELLED)</option>
          </select>
        </div>
      </div>
      <div class="card-body" style="padding: 0;">
        <div id="meetings-table-container">
          <div style="padding: 2rem; text-align: center; color: var(--text-muted);">
            <div class="spinner" style="margin-bottom: 0.5rem;"></div>
            <div>در حال دریافت جلسات...</div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Attach event handlers
  document.getElementById('btn-refresh-monitoring')?.addEventListener('click', () => {
    loadMonitoringStats();
    loadMeetings();
  });

  document.getElementById('meeting-filter-status')?.addEventListener('change', (e) => {
    loadMeetings(e.target.value);
  });

  // Initial load
  await loadMonitoringStats();
  await loadMeetings();

  // Setup auto-refresh every 6 seconds
  refreshTimer = setInterval(() => {
    if (window.location.hash === '#monitoring') {
      loadMonitoringStats(false);
    } else {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }, 6000);
}

async function loadMonitoringStats(showToast = true) {
  try {
    const res = await ApiClient.get('/monitoring/stats');
    const data = res?.data || res;
    if (!data) return;

    // Render KPI Cards
    const kpiGrid = document.getElementById('monitoring-kpi-grid');
    if (kpiGrid) {
      kpiGrid.innerHTML = `
        <div class="kpi-card">
          <div class="kpi-value" style="color: #10b981;">${data.system?.cpuPercent || 0}%</div>
          <div class="kpi-label">بار پردازنده (CPU)</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
            سیستم‌عامل: ${data.system?.os || 'Windows'}
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-value" style="color: #3b82f6;">${data.system?.memory?.used_mb || 0} MB</div>
          <div class="kpi-label">حافظه مصرفی (RAM)</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
            از کل ${data.system?.memory?.total_mb || 0} MB (${data.system?.memory?.percent || 0}%)
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-value" style="color: #8b5cf6;">${data.system?.uptimeHours || 0} ساعت</div>
          <div class="kpi-label">مدت‌زمان فعالیت (Uptime)</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
            پایتون ${data.system?.python || '3.11'}
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-value" style="color: #f59e0b;">${data.meetings?.total || 0}</div>
          <div class="kpi-label">کل قرارهای دیدار حضوری</div>
          <div style="font-size: 0.75rem; color: #10b981; margin-top: 0.25rem;">
            ${data.meetings?.pending || 0} مورد در انتظار تایید
          </div>
        </div>
      `;
    }

    // Render Services List
    const servicesList = document.getElementById('monitoring-services-list');
    if (servicesList && Array.isArray(data.services)) {
      servicesList.innerHTML = data.services.map(s => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.75rem; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">⚡</span>
            <div>
              <div style="font-weight: 600; font-size: 0.85rem; color: var(--text-color);">${s.name}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">تأخیر: ${s.latency_ms}ms</div>
            </div>
          </div>
          <span class="badge ${s.status === 'UP' ? 'badge-success' : 'badge-warning'}">
            ${s.status === 'UP' ? 'فعال ✓' : s.status}
          </span>
        </div>
      `).join('');
    }

    // Render Recent Logs
    const logsList = document.getElementById('monitoring-logs-list');
    if (logsList && Array.isArray(data.recentLogs)) {
      logsList.innerHTML = data.recentLogs.map(l => `
        <div style="display: flex; gap: 0.5rem; align-items: flex-start; line-height: 1.4;">
          <span style="color: #64748b; font-size: 0.7rem; white-space: nowrap;">${l.time}</span>
          <span style="color: #38bdf8; font-weight: bold; font-size: 0.7rem;">[${l.source}]</span>
          <span style="color: #e2e8f0; font-size: 0.75rem;">${l.message}</span>
        </div>
      `).join('');
    }

  } catch (err) {
    console.error('[Monitoring] Error loading stats:', err);
  }
}

async function loadMeetings(statusFilter = '') {
  const container = document.getElementById('meetings-table-container');
  if (!container) return;

  try {
    const url = statusFilter ? `/monitoring/meetings?status=${encodeURIComponent(statusFilter)}` : '/monitoring/meetings';
    const res = await ApiClient.get(url);
    const meetings = res?.data || res || [];

    if (!Array.isArray(meetings) || meetings.length === 0) {
      container.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: var(--text-muted);">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">📅</div>
          <div style="font-weight: 600;">هیچ درخواست وقت دیداری ثبت نشده است.</div>
          <div style="font-size: 0.8rem; margin-top: 0.25rem;">درخواست‌های ارسالی کاربران از بخش «عالمان نزدیک من» در این جدول نمایش داده می‌شوند.</div>
        </div>
      `;
      return;
    }

    const columns = [
      { key: 'tracking', label: 'شناسه پیگیری', render: (row) => `<code style="font-size: 0.75rem;">${row.id.substring(0, 10)}</code>` },
      { key: 'userName', label: 'متقاضی', render: (row) => `
        <div style="font-weight: 600;">${row.userName}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${row.userPhone}</div>
      `},
      { key: 'scholarName', label: 'عالم دینی / استاد', render: (row) => `
        <div style="font-weight: 600; color: var(--primary);">${row.scholarName}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${row.scholarCity} • ${row.location || ''}</div>
      `},
      { key: 'timeSlot', label: 'زمان دیدار', render: (row) => `
        <div>${row.meetingDate}</div>
        <div style="font-size: 0.75rem; color: #d97706; font-weight: 600;">${row.timeSlot}</div>
      `},
      { key: 'subject', label: 'موضوع مشاوره', render: (row) => `<div style="max-width: 200px; font-size: 0.8rem;">${row.subject}</div>` },
      { key: 'status', label: 'وضعیت', render: (row) => {
        let badgeClass = 'badge-warning';
        let label = 'در انتظار';
        if (row.status === 'CONFIRMED') { badgeClass = 'badge-success'; label = 'تأیید شده'; }
        else if (row.status === 'COMPLETED') { badgeClass = 'badge-primary'; label = 'برگزار شد'; }
        else if (row.status === 'CANCELLED') { badgeClass = 'badge-danger'; label = 'لغو شده'; }
        return `<span class="badge ${badgeClass}">${label}</span>`;
      }},
      { key: 'actions', label: 'اقدامات ادمین', render: (row) => `
        <div style="display: flex; gap: 0.25rem;">
          ${row.status === 'PENDING' ? `
            <button onclick="window.updateMeetingStatus('${row.id}', 'CONFIRMED')" class="btn btn-sm btn-primary" title="تأیید وقت دیدار">✓ تأیید</button>
            <button onclick="window.updateMeetingStatus('${row.id}', 'CANCELLED')" class="btn btn-sm btn-outline" style="color: #ef4444;" title="لغو وقت">✕ لغو</button>
          ` : `
            <button onclick="window.updateMeetingStatus('${row.id}', 'COMPLETED')" class="btn btn-sm btn-outline" title="ثبت انجام دیدار">اتمام جلسه</button>
          `}
        </div>
      `}
    ];

    container.innerHTML = renderTable({ columns, data: meetings });

  } catch (err) {
    console.error('[Monitoring] Error loading meetings:', err);
    container.innerHTML = `<div style="padding: 1.5rem; color: #ef4444;">خطا در دریافت جدول جلسات.</div>`;
  }
}

// Global handler for action buttons
window.updateMeetingStatus = async function(meetingId, status) {
  try {
    await ApiClient.post(`/monitoring/meetings/${meetingId}/status`, { status });
    Toast.show(`وضعیت وقت دیدار با موفقیت به روز شد.`, 'success');
    await loadMeetings();
    await loadMonitoringStats(false);
  } catch (err) {
    Toast.show('خطا در تغییر وضعیت وقت دیدار', 'error');
  }
};
