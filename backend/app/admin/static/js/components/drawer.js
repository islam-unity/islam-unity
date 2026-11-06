/**
 * Slide-Over Lateral Detail Drawer (580px)
 * Master-Detail detail pane with backdrop, close events, and dynamic content
 */

export class Drawer {
  static drawerEl = null;
  static backdropEl = null;
  static titleEl = null;
  static subtitleEl = null;
  static bodyEl = null;
  static footerEl = null;
  static closeBtn = null;
  static currentOnClose = null;

  static init() {
    if (!Drawer.drawerEl) {
      Drawer.drawerEl = document.getElementById('admin-drawer');
      Drawer.backdropEl = document.getElementById('drawer-backdrop');
      Drawer.titleEl = document.getElementById('drawer-title');
      Drawer.subtitleEl = document.getElementById('drawer-subtitle');
      Drawer.bodyEl = document.getElementById('drawer-body');
      Drawer.footerEl = document.getElementById('drawer-footer');
      Drawer.closeBtn = document.getElementById('drawer-close-btn');

      if (Drawer.closeBtn) {
        Drawer.closeBtn.addEventListener('click', () => Drawer.close());
      }

      if (Drawer.backdropEl) {
        Drawer.backdropEl.addEventListener('click', () => Drawer.close());
      }

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && Drawer.isOpen()) {
          Drawer.close();
        }
      });
    }
  }

  static isOpen() {
    return Drawer.drawerEl && Drawer.drawerEl.classList.contains('is-open');
  }

  static open({ title, subtitle = '', contentHtml = '', footerHtml = '', onClose = null }) {
    Drawer.init();
    Drawer.currentOnClose = onClose;

    if (Drawer.titleEl) Drawer.titleEl.textContent = title;
    if (Drawer.subtitleEl) Drawer.subtitleEl.textContent = subtitle;
    if (Drawer.bodyEl) Drawer.bodyEl.innerHTML = contentHtml;
    if (Drawer.footerEl) Drawer.footerEl.innerHTML = footerHtml;

    if (Drawer.drawerEl) Drawer.drawerEl.classList.add('is-open');
    if (Drawer.backdropEl) Drawer.backdropEl.classList.add('is-active');
    document.body.style.overflow = 'hidden';
  }

  static close() {
    if (!Drawer.isOpen()) return;

    if (Drawer.drawerEl) Drawer.drawerEl.classList.remove('is-open');
    if (Drawer.backdropEl) Drawer.backdropEl.classList.remove('is-active');
    document.body.style.overflow = '';

    if (typeof Drawer.currentOnClose === 'function') {
      try {
        Drawer.currentOnClose();
      } catch (err) {
        console.error('Drawer onClose error:', err);
      }
      Drawer.currentOnClose = null;
    }
  }

  static setContent(contentHtml) {
    Drawer.init();
    if (Drawer.bodyEl) Drawer.bodyEl.innerHTML = contentHtml;
  }

  static setFooter(footerHtml) {
    Drawer.init();
    if (Drawer.footerEl) Drawer.footerEl.innerHTML = footerHtml;
  }
}
