/**
 * Reusable Paginated Table Component
 * Standardizes Master Grid tables, page controls (10/25/50), page indicator,
 * empty state, and loading spinner across all 8 domains.
 */

export function renderTable({
  container,
  columns,
  data = [],
  meta = null,
  currentPage = 1,
  pageSize = 10,
  onPageChange = null,
  onPageSizeChange = null,
  emptyMessage = 'داده‌ای برای نمایش یافت نشد.',
  isLoading = false
}) {
  if (typeof container === 'string') {
    container = document.querySelector(container);
  }
  if (!container) return;

  if (isLoading) {
    container.innerHTML = `
      <div class="table-container">
        <div class="loading-container">
          <div class="spinner spinner-lg"></div>
          <div>در حال دریافت اطلاعات از سرور...</div>
        </div>
      </div>
    `;
    return;
  }

  if (!data || data.length === 0) {
    container.innerHTML = `
      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              ${columns.map(col => `<th>${col.header}</th>`).join('')}
            </tr>
          </thead>
        </table>
        <div class="empty-state">
          <div class="empty-state-icon">📂</div>
          <div class="empty-state-title">${emptyMessage}</div>
        </div>
      </div>
    `;
    return;
  }

  // Calculate pagination metadata
  const total = meta?.total !== undefined ? meta.total : (meta?.totalCount || data.length);
  const totalPages = meta?.totalPages || Math.max(1, Math.ceil(total / pageSize));
  const page = meta?.page || currentPage;

  let tableHtml = `
    <div class="table-container">
      <div style="overflow-x: auto;">
        <table class="admin-table">
          <thead>
            <tr>
              ${columns.map(col => `<th style="${col.style || ''}">${col.header}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
  `;

  data.forEach((row, rowIndex) => {
    tableHtml += '<tr>';
    columns.forEach(col => {
      let cellContent = '';
      if (typeof col.render === 'function') {
        cellContent = col.render(row, rowIndex);
      } else {
        const val = row[col.field];
        cellContent = val !== undefined && val !== null ? String(val) : '—';
      }
      tableHtml += `<td style="${col.style || ''}">${cellContent}</td>`;
    });
    tableHtml += '</tr>';
  });

  tableHtml += `
          </tbody>
        </table>
      </div>
      <div class="pagination-bar">
        <div class="pagination-info">
          <span>کل: <strong>${Number(total).toLocaleString('fa-IR')}</strong> مورد</span>
          <span>صفحه <strong>${Number(page).toLocaleString('fa-IR')}</strong> از <strong>${Number(totalPages).toLocaleString('fa-IR')}</strong></span>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <label for="table-page-size" style="font-size: 0.8rem;">تعداد:</label>
            <select id="table-page-size" class="select-control" style="padding: 0.2rem 0.5rem; font-size: 0.8rem;">
              <option value="10" ${pageSize === 10 ? 'selected' : ''}>۱۰</option>
              <option value="25" ${pageSize === 25 ? 'selected' : ''}>۲۵</option>
              <option value="50" ${pageSize === 50 ? 'selected' : ''}>۵۰</option>
            </select>
          </div>
        </div>
        <div class="pagination-actions">
          <button id="btn-prev-page" class="pagination-btn" ${page <= 1 ? 'disabled' : ''}>
            قبلی
          </button>
          <button id="btn-next-page" class="pagination-btn" ${page >= totalPages ? 'disabled' : ''}>
            بعدی
          </button>
        </div>
      </div>
    </div>
  `;

  container.innerHTML = tableHtml;

  // Event handlers
  const pageSizeSelect = container.querySelector('#table-page-size');
  if (pageSizeSelect && onPageSizeChange) {
    pageSizeSelect.addEventListener('change', (e) => {
      onPageSizeChange(Number(e.target.value));
    });
  }

  const prevBtn = container.querySelector('#btn-prev-page');
  if (prevBtn && onPageChange && page > 1) {
    prevBtn.addEventListener('click', () => {
      onPageChange(page - 1);
    });
  }

  const nextBtn = container.querySelector('#btn-next-page');
  if (nextBtn && onPageChange && page < totalPages) {
    nextBtn.addEventListener('click', () => {
      onPageChange(page + 1);
    });
  }
}

/**
 * Helper to format ISO dates to readable Persian locale
 */
export function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d);
  } catch {
    return isoString;
  }
}

/**
 * Helper to format numbers with Persian separators
 */
export function formatNum(num) {
  if (num === null || num === undefined) return '۰';
  return Number(num).toLocaleString('fa-IR');
}
