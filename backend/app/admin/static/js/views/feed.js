/**
 * View 7: Feed & Content Moderation (فید و نظارت بر محتوا)
 * Moderation reports queue, quick resolve/dismiss actions, and feed posts table.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

export function renderFeed(container) {
  let activeTab = 'reports'; // 'reports' | 'posts'

  let reportsState = { page: 1, pageSize: 10, status: '', data: [], meta: null };
  let postsState = { page: 1, pageSize: 10, search: '', status: '', data: [], meta: null };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">🛡️ شبکه اجتماعی، فید و کارتابل بازبینی تخلفات</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-feed-reports" class="subtab-btn active">کارتابل گزارش‌های تخلف محتوا (PostReport)</button>
          <button id="tab-feed-posts" class="subtab-btn">پست‌ها و محتوای منتشرشده</button>
        </div>

        <!-- Reports Section -->
        <div id="section-feed-reports">
          <div class="toolbar">
            <div class="toolbar-group">
              <select id="report-filter-status" class="select-control">
                <option value="">همه وضعیت‌ها</option>
                <option value="PENDING">در انتظار بررسی (PENDING)</option>
                <option value="RESOLVED_DISMISSED">رد گزارش و تایید محتوا (RESOLVED_DISMISSED)</option>
                <option value="RESOLVED_REMOVED">تایید تخلف و حذف پست (RESOLVED_REMOVED)</option>
              </select>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-reports" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="reports-table-container"></div>
        </div>

        <!-- Posts Section -->
        <div id="section-feed-posts" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="posts-search" type="text" class="search-input" placeholder="جستجو در عنوان یا متن پست‌ها...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-posts" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="posts-table-container"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabReports = container.querySelector('#tab-feed-reports');
  const tabPosts = container.querySelector('#tab-feed-posts');
  const secReports = container.querySelector('#section-feed-reports');
  const secPosts = container.querySelector('#section-feed-posts');

  tabReports.addEventListener('click', () => {
    activeTab = 'reports';
    tabReports.classList.add('active');
    tabPosts.classList.remove('active');
    secReports.style.display = 'block';
    secPosts.style.display = 'none';
    fetchReports();
  });

  tabPosts.addEventListener('click', () => {
    activeTab = 'posts';
    tabPosts.classList.add('active');
    tabReports.classList.remove('active');
    secReports.style.display = 'none';
    secPosts.style.display = 'block';
    fetchPosts();
  });

  // Report status filter
  container.querySelector('#report-filter-status').addEventListener('change', (e) => {
    reportsState.status = e.target.value;
    reportsState.page = 1;
    fetchReports();
  });
  container.querySelector('#btn-refresh-reports').addEventListener('click', fetchReports);

  // Posts search
  let postSearchTimeout = null;
  container.querySelector('#posts-search').addEventListener('input', (e) => {
    clearTimeout(postSearchTimeout);
    postSearchTimeout = setTimeout(() => {
      postsState.search = e.target.value.trim();
      postsState.page = 1;
      fetchPosts();
    }, 300);
  });
  container.querySelector('#btn-refresh-posts').addEventListener('click', fetchPosts);

  // Reports Columns
  const reportColumns = [
    {
      header: 'شناسه گزارش',
      render: (r) => `<span style="font-family: monospace; font-size: 0.8rem;">${r.id}</span>`
    },
    {
      header: 'شناسه پست / کاربر',
      render: (r) => `
        <div>
          <div style="font-family: monospace; font-size: 0.78rem;">پست: ${r.postId || r.post_id}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">گزارش‌دهنده: ${r.userId || r.user_id}</div>
        </div>
      `
    },
    {
      header: 'علت تخلف',
      render: (r) => `<span class="badge badge-danger">${r.reason || 'محتوای نامناسب'}</span>`
    },
    {
      header: 'توضیحات شاکی',
      render: (r) => `<div style="max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${r.description || '—'}</div>`
    },
    {
      header: 'وضعیت',
      render: (r) => {
        const st = r.status || 'PENDING';
        if (st === 'PENDING') return `<span id="report-st-${r.id}" class="badge badge-warning">در انتظار بررسی</span>`;
        if (st === 'RESOLVED_REMOVED') return `<span id="report-st-${r.id}" class="badge badge-danger">حذف محتوا ✓</span>`;
        return `<span id="report-st-${r.id}" class="badge badge-success">رد گزارش ✓</span>`;
      }
    },
    {
      header: 'تاریخ ثبت',
      render: (r) => `<span style="font-size: 0.78rem;">${formatDateTime(r.createdAt || r.created_at)}</span>`
    },
    {
      header: 'عملیات سریع',
      style: 'text-align: left;',
      render: (r) => `
        <div style="display: flex; gap: 0.35rem; justify-content: flex-end;">
          <button class="btn btn-outline btn-sm btn-view-report" data-report-id="${r.id}" data-post-id="${r.postId || r.post_id}" data-reason="${r.reason || ''}" data-desc="${r.description || ''}">
            👁️ بررسی
          </button>
          <button class="btn btn-sm btn-primary btn-dismiss-report" data-report-id="${r.id}" title="رد گزارش و تایید پست">
            رد گزارش
          </button>
          <button class="btn btn-sm btn-danger btn-remove-post" data-report-id="${r.id}" title="تایید تخلف و حذف فوری پست">
            حذف پست
          </button>
        </div>
      `
    }
  ];

  async function fetchReports() {
    renderTable({
      container: container.querySelector('#reports-table-container'),
      columns: reportColumns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: reportsState.page,
        pageSize: reportsState.pageSize
      };
      if (reportsState.status) params.status = reportsState.status;

      const res = await ApiClient.get('/feed/reports', params);
      reportsState.data = res.data || [];
      reportsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#reports-table-container'),
        columns: reportColumns,
        data: reportsState.data,
        meta: reportsState.meta,
        currentPage: reportsState.page,
        pageSize: reportsState.pageSize,
        emptyMessage: 'گزارش تخلفی ثبت نشده است.',
        onPageChange: (p) => { reportsState.page = p; fetchReports(); },
        onPageSizeChange: (s) => { reportsState.pageSize = s; reportsState.page = 1; fetchReports(); }
      });

      attachReportActions();
    } catch (err) {
      container.querySelector('#reports-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت گزارش‌ها: ${err.message}</div></div>
      `;
    }
  }

  function attachReportActions() {
    // 1. Dismiss report
    container.querySelectorAll('.btn-dismiss-report').forEach(btn => {
      btn.addEventListener('click', async () => {
        const reportId = btn.getAttribute('data-report-id');
        btn.classList.add('loading');
        try {
          await ApiClient.patch(`/feed/reports/${reportId}/status`, { status: 'RESOLVED_DISMISSED' });
          const badge = container.querySelector(`#report-st-${reportId}`);
          if (badge) {
            badge.textContent = 'رد گزارش ✓';
            badge.className = 'badge badge-success';
          }
          Toast.success('گزارش با موفقیت رد شد و انتشار پست بلامانع اعلام گردید.');
        } finally {
          btn.classList.remove('loading');
        }
      });
    });

    // 2. Remove post
    container.querySelectorAll('.btn-remove-post').forEach(btn => {
      btn.addEventListener('click', async () => {
        const reportId = btn.getAttribute('data-report-id');
        btn.classList.add('loading');
        try {
          await ApiClient.patch(`/feed/reports/${reportId}/status`, { status: 'RESOLVED_REMOVED' });
          const badge = container.querySelector(`#report-st-${reportId}`);
          if (badge) {
            badge.textContent = 'حذف محتوا ✓';
            badge.className = 'badge badge-danger';
          }
          Toast.warning('تخلف تایید شد و پست متخلف از فید سامانه مخفی/حذف گردید.');
        } finally {
          btn.classList.remove('loading');
        }
      });
    });

    // 3. View detail in Drawer
    container.querySelectorAll('.btn-view-report').forEach(btn => {
      btn.addEventListener('click', () => {
        const reportId = btn.getAttribute('data-report-id');
        const postId = btn.getAttribute('data-post-id');
        const reason = btn.getAttribute('data-reason');
        const desc = btn.getAttribute('data-desc');

        Drawer.open({
          title: `بررسی گزارش تخلف: ${reportId}`,
          subtitle: `شناسه پست مورد شکایت: ${postId}`,
          contentHtml: `
            <div class="detail-section">
              <div class="detail-section-title">⚠️ مشخصات شکایت و تخلف اعلامی</div>
              <div class="detail-row">
                <span class="detail-label">عنوان تخلف</span>
                <span class="badge badge-danger">${reason}</span>
              </div>
              <div style="margin-top: 0.75rem;">
                <span class="detail-label" style="display: block; margin-bottom: 0.25rem;">شرح تخلف توسط شاکی:</span>
                <div style="background: white; border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; font-size: 0.85rem; line-height: 1.6;">
                  ${desc || 'توضیحات تکمیلی ثبت نشده است.'}
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="detail-section-title">📌 اقدامات کارتابل نظارت</div>
              <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                با انتخاب «تایید تخلف و حذف پست»، وضعیت این پست بلافاصله در فید به حالت مخفی (REPORTED_HIDDEN) تغییر خواهد یافت.
              </p>
              <div style="display: flex; gap: 0.5rem;">
                <button id="drawer-btn-dismiss" class="btn btn-primary" style="flex: 1;">
                  ✓ رد گزارش (تایید پست)
                </button>
                <button id="drawer-btn-remove" class="btn btn-danger" style="flex: 1;">
                  ✕ تایید تخلف و حذف پست
                </button>
              </div>
            </div>
          `,
          footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
        });

        document.getElementById('drawer-btn-dismiss').addEventListener('click', async () => {
          await ApiClient.patch(`/feed/reports/${reportId}/status`, { status: 'RESOLVED_DISMISSED' });
          Toast.success('گزارش با موفقیت رد شد.');
          Drawer.close();
          fetchReports();
        });

        document.getElementById('drawer-btn-remove').addEventListener('click', async () => {
          await ApiClient.patch(`/feed/reports/${reportId}/status`, { status: 'RESOLVED_REMOVED' });
          Toast.warning('پست با موفقیت از فید حذف شد.');
          Drawer.close();
          fetchReports();
        });
      });
    });
  }

  // Posts Columns
  const postColumns = [
    {
      header: 'عنوان و متن پست',
      render: (p) => `
        <div>
          <div style="font-weight: 700;">${p.title || 'بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); max-width: 350px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.content || ''}</div>
        </div>
      `
    },
    {
      header: 'دسته‌بندی',
      render: (p) => `<span class="badge badge-info">${p.category || 'عمومی'}</span>`
    },
    {
      header: 'وضعیت انتشار',
      render: (p) => {
        const st = p.status || 'PUBLISHED';
        if (st === 'PUBLISHED') return `<span class="badge badge-success">منتشر شده</span>`;
        if (st === 'REPORTED_HIDDEN') return `<span class="badge badge-danger">مخفی / تخلف</span>`;
        return `<span class="badge badge-neutral">${st}</span>`;
      }
    },
    {
      header: 'آمار تعاملات',
      render: (p) => `
        <div style="font-size: 0.78rem;">
          <span>👁️ ${formatNum(p.viewsCount ?? p.views_count ?? 0)}</span> |
          <span>❤️ ${formatNum(p.likesCount ?? p.likes_count ?? 0)}</span> |
          <span>💬 ${formatNum(p.commentsCount ?? p.comments_count ?? 0)}</span>
        </div>
      `
    },
    {
      header: 'تاریخ ارسال',
      render: (p) => `<span style="font-size: 0.78rem;">${formatDateTime(p.createdAt || p.created_at)}</span>`
    }
  ];

  async function fetchPosts() {
    renderTable({
      container: container.querySelector('#posts-table-container'),
      columns: postColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/feed/posts', {
        page: postsState.page,
        pageSize: postsState.pageSize,
        search: postsState.search
      });
      postsState.data = res.data || [];
      postsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#posts-table-container'),
        columns: postColumns,
        data: postsState.data,
        meta: postsState.meta,
        currentPage: postsState.page,
        pageSize: postsState.pageSize,
        emptyMessage: 'پستی یافت نشد.',
        onPageChange: (p) => { postsState.page = p; fetchPosts(); },
        onPageSizeChange: (s) => { postsState.pageSize = s; postsState.page = 1; fetchPosts(); }
      });
    } catch (err) {
      container.querySelector('#posts-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت پست‌ها: ${err.message}</div></div>
      `;
    }
  }

  fetchReports();
}
