/**
 * Ettehad Admin Dashboard - Main SPA Application Controller
 * Pure Vanilla JavaScript (ES2022 Native Modules)
 * Handles client-side routing, active state, header metadata, and view rendering.
 */

import { Drawer } from './components/drawer.js';
import { Toast } from './components/toast.js';
import { ApiClient } from './api.js';
import { renderOverview } from './views/overview.js';
import { renderUsers } from './views/users.js';
import { renderConsultations } from './views/consultations.js';
import { renderLibrary } from './views/library.js';
import { renderQuran } from './views/quran.js';
import { renderAI } from './views/ai.js';
import { renderRagEval } from './views/rag_eval.js';
import { renderFeed } from './views/feed.js';
import { renderMonitoring } from './views/monitoring.js';
import { renderDevelopers } from './views/developers.js';
import { renderPrayerTimes } from './views/prayer_times.js';
import { renderDhikr } from './views/dhikr.js';

const routes = {
  overview: {
    title: 'نمای کلی و آمار سامانه',
    render: renderOverview
  },
  users: {
    title: 'مدیریت کاربران و هویت',
    render: renderUsers
  },
  consultations: {
    title: 'پاسخ‌کده و مشاوره فقهی',
    render: renderConsultations
  },
  library: {
    title: 'کتابخانه معارفی و پایگاه دانش معنایی',
    render: renderLibrary
  },
  quran: {
    title: 'قرآن کریم، آیات شریفه و قاریان',
    render: renderQuran
  },
  ai: {
    title: 'سرویس‌های هوش مصنوعی و هزینه‌ها',
    render: renderAI
  },
  'rag-eval': {
    title: 'آزمایشگاه و ارزیابی داده‌های بازیابی RAG',
    render: renderRagEval
  },
  feed: {
    title: 'شبکه اجتماعی و کارتابل بازبینی تخلفات',
    render: renderFeed
  },
  monitoring: {
    title: 'مرکز مانیتورینگ زنده، سلامت سیستم و جلسات حضوری',
    render: renderMonitoring
  },
  'prayer-times': {
    title: 'اوقات شرعی و مدیریت JSON شهرها',
    render: renderPrayerTimes
  },
  dhikr: {
    title: 'ادعیه، اذکار و دسته‌بندی‌های شمارنده',
    render: renderDhikr
  },
  developers: {
    title: 'پلتفرم توسعه‌دهندگان و سیستم',
    render: renderDevelopers
  }
};


class App {
  static init() {
    Drawer.init();
    Toast.init();

    App.setupDateDisplay();
    App.setupServerSwitcher();
    App.setupHealthPing();
    App.setupNavigation();
    App.handleRoute();

    window.addEventListener('hashchange', () => App.handleRoute());
  }

  static setupServerSwitcher() {
    const switcher = document.getElementById('select-backend-endpoint');
    if (!switcher) return;

    const currentSaved = localStorage.getItem('ETTEHAD_ADMIN_BACKEND_URL');
    if (currentSaved) {
      switcher.value = currentSaved;
    } else {
      switcher.value = 'auto';
    }

    switcher.addEventListener('change', (e) => {
      const val = e.target.value;
      if (val === 'auto') {
        ApiClient.setBaseUrl(null);
        Toast.info('آدرس بک‌اند به حالت تشخیص خودکار تغییر یافت.');
      } else {
        ApiClient.setBaseUrl(val);
        Toast.success(`آدرس بک‌اند تنظیم شد: ${val}`);
      }
      App.checkHealth();
      App.handleRoute();
    });
  }

  static setupHealthPing() {
    const pill = document.getElementById('header-status-pill');
    if (pill) {
      pill.addEventListener('click', () => {
        Toast.info('در حال بررسی مجدد وضعیت اتصال به بک‌اند...');
        App.checkHealth(true);
      });
    }

    App.checkHealth();
    // Re-check health every 30 seconds
    setInterval(() => App.checkHealth(false), 30000);
  }

  static async checkHealth(showToast = false) {
    const dot = document.getElementById('header-status-dot');
    const text = document.getElementById('header-status-text');
    const pill = document.getElementById('header-status-pill');

    try {
      const startT = performance.now();
      const res = await ApiClient.get('/overview');
      const elapsed = Math.round(performance.now() - startT);

      if (dot) {
        dot.style.background = '#10b981'; // Green
        dot.style.boxShadow = '0 0 8px rgba(16, 185, 129, 0.6)';
      }
      if (text) {
        const isRemote = ApiClient.baseUrl.includes('unitysi.ir');
        text.textContent = isRemote ? `متصل به api.unitysi.ir (${elapsed}ms)` : `متصل به سرور (${elapsed}ms)`;
        text.style.color = 'var(--text-main)';
      }
      if (pill) {
        pill.title = `اتصال برقرار است (${elapsed} میلی‌ثانیه). کلیک جهت تست مجدد`;
      }
      if (showToast) {
        Toast.success(`اتصال با موفقیت برقرار شد (${elapsed}ms)`);
      }
    } catch (err) {
      if (dot) {
        dot.style.background = '#ef4444'; // Red
        dot.style.boxShadow = '0 0 8px rgba(239, 68, 68, 0.6)';
      }
      if (text) {
        text.textContent = 'عدم ارتباط با سرور';
        text.style.color = '#ef4444';
      }
      if (pill) {
        pill.title = `خطا در اتصال: ${err.message}. کلیک جهت تست مجدد`;
      }
      if (showToast) {
        Toast.error(`خطا در اتصال به بک‌اند: ${err.message}`);
      }
    }
  }

  static setupDateDisplay() {
    const dateEl = document.getElementById('header-current-date');
    if (dateEl) {
      try {
        const now = new Date();
        const formatted = new Intl.DateTimeFormat('fa-IR', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        }).format(now);
        dateEl.textContent = `📅 امروز: ${formatted}`;
      } catch {
        dateEl.textContent = '';
      }
    }
  }

  static setupNavigation() {
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(link => {
      link.addEventListener('click', () => {
        // Close drawer if open when navigating
        Drawer.close();
      });
    });
  }

  static handleRoute() {
    const hash = window.location.hash.replace('#', '').trim() || 'overview';
    const targetRoute = routes[hash] || routes.overview;

    // Update active nav link
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(link => {
      const linkHash = link.getAttribute('href').replace('#', '').trim();
      link.classList.toggle('active', linkHash === hash);
    });

    // Update Header title
    const headerTitleEl = document.getElementById('header-active-title');
    if (headerTitleEl) {
      headerTitleEl.textContent = targetRoute.title;
    }
    document.title = `${targetRoute.title} | پنل مدیریت اتحاد`;

    // Render View
    const contentContainer = document.getElementById('admin-content-view');
    if (contentContainer) {
      contentContainer.innerHTML = '<div class="loading-container"><div class="spinner spinner-lg"></div><div>در حال آماده‌سازی بخش...</div></div>';
      try {
        targetRoute.render(contentContainer);
      } catch (err) {
        console.error('Render error:', err);
        contentContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-title" style="color: var(--danger);">خطا در بارگذاری بخش: ${err.message}</div>
          </div>
        `;
      }
    }
  }
}

// Bootstrap on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
