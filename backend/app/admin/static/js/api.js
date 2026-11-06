/**
 * Admin API Client
 * Communicates with FastAPI Admin REST API endpoints at /api/v1/admin
 * Supports live production backend (https://api.unitysi.ir), local development,
 * envelope unwrapping, query string serialization, and toast errors.
 */

import { Toast } from './components/toast.js';

export class ApiClient {
  /**
   * Determine the effective base URL dynamically.
   * Priority:
   * 1. localStorage 'ETTEHAD_ADMIN_BACKEND_URL'
   * 2. window.__ADMIN_BACKEND_URL__
   * 3. Fallback to 'https://api.unitysi.ir/api/v1/admin' if running on file:// or unknown foreign host
   * 4. Relative '/api/v1/admin' when served directly by backend or on unitysi.ir / localhost
   */
  static getBaseUrl() {
    try {
      const stored = localStorage.getItem('ETTEHAD_ADMIN_BACKEND_URL');
      if (stored && stored.trim()) {
        return stored.trim().replace(/\/+$/, '');
      }
    } catch (_) {}

    if (typeof window !== 'undefined' && window.__ADMIN_BACKEND_URL__) {
      return String(window.__ADMIN_BACKEND_URL__).trim().replace(/\/+$/, '');
    }

    if (typeof window !== 'undefined') {
      const proto = window.location.protocol;
      const host = window.location.hostname;
      // When opened locally via file:/// or an external client host, route to official backend
      if (proto === 'file:' || (!host.includes('unitysi.ir') && host !== 'localhost' && host !== '127.0.0.1')) {
        return 'https://api.unitysi.ir/api/v1/admin';
      }
    }

    return '/api/v1/admin';
  }

  static get baseUrl() {
    return ApiClient.getBaseUrl();
  }

  static setBaseUrl(newUrl) {
    try {
      if (newUrl && newUrl.trim()) {
        localStorage.setItem('ETTEHAD_ADMIN_BACKEND_URL', newUrl.trim().replace(/\/+$/, ''));
      } else {
        localStorage.removeItem('ETTEHAD_ADMIN_BACKEND_URL');
      }
    } catch (_) {}
  }

  static resolveUrl(endpoint) {
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      return endpoint;
    }

    const base = ApiClient.baseUrl;

    // Handle endpoints that already contain /api/v1/admin
    if (endpoint.startsWith('/api/v1/admin')) {
      if (base.startsWith('http://') || base.startsWith('https://')) {
        try {
          const rootOrigin = new URL(base).origin;
          return `${rootOrigin}${endpoint}`;
        } catch (_) {}
      }
      return endpoint;
    }

    const cleanEp = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${base}${cleanEp}`;
  }

  static getHeaders(extraHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...extraHeaders
    };

    try {
      const token = localStorage.getItem('admin_token') || localStorage.getItem('access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token.trim()}`;
      }
    } catch (_) {}

    return headers;
  }

  static async request(endpoint, options = {}) {
    const url = ApiClient.resolveUrl(endpoint);
    const headers = ApiClient.getHeaders(options.headers);

    try {
      const response = await fetch(url, { ...options, headers });
      
      let json = null;
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        json = await response.json();
      }

      if (!response.ok) {
        const errorMsg = json?.error?.message || json?.detail || `خطای سرور (${response.status})`;
        throw new Error(errorMsg);
      }

      if (json && json.success === false) {
        throw new Error(json.error?.message || 'خطا در انجام عملیات');
      }

      // Handle raw [items, meta] tuple returned by raw paginate()
      if (Array.isArray(json) && json.length === 2 && json[1] && typeof json[1] === 'object' && ('page' in json[1] || 'totalCount' in json[1])) {
        return {
          data: json[0],
          meta: json[1],
          success: true
        };
      }

      return {
        data: json?.data !== undefined ? json.data : json,
        meta: json?.meta || null,
        success: true
      };
    } catch (err) {
      console.error(`[API Error] ${options.method || 'GET'} ${url}:`, err);
      Toast.error(err.message || 'خطا در برقراری ارتباط با سرور');
      throw err;
    }
  }

  static get(endpoint, params = {}) {
    const cleanParams = Object.entries(params).filter(
      ([_, v]) => v !== undefined && v !== null && v !== ''
    );
    const queryString = new URLSearchParams(cleanParams).toString();
    const finalUrl = queryString ? `${endpoint}?${queryString}` : endpoint;
    return ApiClient.request(finalUrl, { method: 'GET' });
  }

  static post(endpoint, body = {}) {
    return ApiClient.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  static patch(endpoint, body = {}) {
    return ApiClient.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    });
  }

  static put(endpoint, body = {}) {
    return ApiClient.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  }

  static delete(endpoint) {
    return ApiClient.request(endpoint, {
      method: 'DELETE'
    });
  }

  static async upload(endpoint, formData) {
    const url = ApiClient.resolveUrl(endpoint);
    const headers = {
      'Accept': 'application/json'
    };

    try {
      const token = localStorage.getItem('admin_token') || localStorage.getItem('access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token.trim()}`;
      }
    } catch (_) {}

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        headers
      });

      let json = null;
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        json = await response.json();
      }

      if (!response.ok) {
        const errorMsg = json?.error?.message || json?.detail || `خطای سرور (${response.status})`;
        throw new Error(errorMsg);
      }

      if (json && json.success === false) {
        throw new Error(json.error?.message || 'خطا در انجام عملیات');
      }

      // Handle raw [items, meta] tuple returned by raw paginate()
      if (Array.isArray(json) && json.length === 2 && json[1] && typeof json[1] === 'object' && ('page' in json[1] || 'totalCount' in json[1])) {
        return {
          data: json[0],
          meta: json[1],
          success: true
        };
      }

      return {
        data: json?.data !== undefined ? json.data : json,
        meta: json?.meta || null,
        success: true
      };
    } catch (err) {
      console.error(`[API Upload Error] ${url}:`, err);
      Toast.error(err.message || 'خطا در آپلود فایل');
      throw err;
    }
  }
}
