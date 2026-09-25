// MedSecure API Client
const API_BASE = '/api';

const API = {
  getToken() {
    return localStorage.getItem('medsecure_token');
  },

  setToken(token) {
    localStorage.setItem('medsecure_token', token);
  },

  removeToken() {
    localStorage.removeItem('medsecure_token');
  },

  getUSBToken() {
    return sessionStorage.getItem('medsecure_usb_token') || '';
  },

  setUSBToken(token) {
    sessionStorage.setItem('medsecure_usb_token', token);
  },

  removeUSBToken() {
    sessionStorage.removeItem('medsecure_usb_token');
  },

  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    const usbToken = this.getUSBToken();

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (usbToken) {
      headers['X-USB-Security-Token'] = usbToken;
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    options.headers = headers;

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, options);

      // Handle 401 Unauthorized (expired token)
      if (response.status === 401 && !endpoint.includes('/auth/login')) {
        this.removeToken();
        window.dispatchEvent(new CustomEvent('auth:expired'));
        throw new Error('Session expired. Please log in again.');
      }

      // Handle 403 Forbidden (e.g. USB Security Verification required)
      if (response.status === 403) {
        const errorData = await response.json().catch(() => ({ detail: 'Access restricted.' }));
        if (errorData.detail && errorData.detail.includes('USB Security')) {
          window.dispatchEvent(new CustomEvent('usb:required', { detail: errorData.detail }));
        }
        throw new Error(errorData.detail || 'Access forbidden.');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        let msg = '';
        if (Array.isArray(errorData.detail)) {
          // Pydantic validation error array: [{loc: [...], msg: "..."}]
          msg = errorData.detail.map(d => {
            const field = d.loc ? d.loc[d.loc.length - 1] : '';
            return field ? `${field}: ${d.msg}` : d.msg;
          }).join(', ');
        } else if (typeof errorData.detail === 'object' && errorData.detail !== null) {
          msg = JSON.stringify(errorData.detail);
        } else {
          msg = errorData.detail || `Request failed with status ${response.status}`;
        }
        throw new Error(msg);
      }

      // If expecting blob/stream
      if (options.responseType === 'blob') {
        return await response.blob();
      }

      return await response.json();
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth endpoints
  login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  register(data) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getProfile() {
    return this.request('/auth/me');
  },

  // Patient endpoints
  getPatients(search = '') {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request(`/patients${q}`);
  },

  getPatient(id) {
    return this.request(`/patients/${id}`);
  },

  createPatient(data) {
    return this.request('/patients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updatePatient(id, data) {
    return this.request(`/patients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  deletePatient(id) {
    return this.request(`/patients/${id}`, {
      method: 'DELETE',
    });
  },

  // Report endpoints
  uploadReport(patientId, formData) {
    return this.request(`/patients/${patientId}/reports`, {
      method: 'POST',
      body: formData,
    });
  },

  getPatientReports(patientId) {
    return this.request(`/patients/${patientId}/reports`);
  },

  deleteReport(reportId) {
    return this.request(`/reports/${reportId}`, {
      method: 'DELETE',
    });
  },

  viewReportBlob(reportId) {
    return this.request(`/reports/${reportId}/view`, {
      responseType: 'blob',
    });
  },

  // USB endpoints
  getHardwareStatus() {
    return this.request('/usb/hardware-status');
  },

  scanUSBDrives() {
    return this.request('/usb/drives');
  },

  generateUSBKey(label, targetDrive = null) {
    return this.request('/usb/generate-key', {
      method: 'POST',
      body: JSON.stringify({ label, target_drive: targetDrive }),
    });
  },

  verifyUSBToken(token) {
    return this.request('/usb/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },

  getUSBKeys() {
    return this.request('/usb/keys');
  },

  revokeUSBKey(keyId) {
    return this.request(`/usb/keys/${keyId}`, {
      method: 'DELETE',
    });
  },

  // Stats & Audit
  getStats() {
    return this.request('/stats');
  },

  getRecentActivity() {
    return this.request('/recent-activity');
  },

  getAuditLogs() {
    return this.request('/audit-logs');
  },
};

// Global Toast helper
window.showToast = function (message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon =
    type === 'success'
      ? 'fa-check-circle'
      : type === 'error'
      ? 'fa-exclamation-circle'
      : 'fa-info-circle';
  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};
