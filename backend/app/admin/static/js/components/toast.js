/**
 * Toast Notification System
 * Bottom-left floating notifications with auto-dismiss and dismissal animation
 */

export class Toast {
  static container = null;

  static init() {
    if (!Toast.container) {
      let el = document.getElementById('toast-container');
      if (!el) {
        el = document.createElement('div');
        el.id = 'toast-container';
        el.className = 'toast-container';
        document.body.appendChild(el);
      }
      Toast.container = el;
    }
  }

  static show(message, type = 'info', duration = 3500) {
    Toast.init();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    else if (type === 'error') icon = '⚠️';
    else if (type === 'warning') icon = '⚡';

    toast.innerHTML = `
      <span style="font-weight: bold; font-size: 1.1rem;">${icon}</span>
      <span style="flex: 1; word-break: break-word;">${message}</span>
    `;

    toast.addEventListener('click', () => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 250);
    });

    Toast.container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 250);
      }
    }, duration);
  }

  static success(msg) {
    Toast.show(msg, 'success');
  }

  static error(msg) {
    Toast.show(msg, 'error', 4500);
  }

  static warning(msg) {
    Toast.show(msg, 'warning');
  }

  static info(msg) {
    Toast.show(msg, 'info');
  }
}
