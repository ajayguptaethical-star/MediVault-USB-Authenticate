// MedSecure Dashboard Controller

const Dashboard = {
  currentView: 'overview',

  init() {
    this.bindNavigation();
    window.addEventListener('auth:ready', () => {
      this.loadStats();
      this.loadRecentActivity();
    });
  },

  bindNavigation() {
    const navItems = document.querySelectorAll('.sidebar-menu .menu-item[data-view]');
    navItems.forEach((item) => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.getAttribute('data-view');
        this.switchView(view);
      });
    });
  },

  switchView(viewName) {
    this.currentView = viewName;

    // Update active state in sidebar
    document.querySelectorAll('.sidebar-menu .menu-item').forEach((el) => {
      if (el.getAttribute('data-view') === viewName) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // Toggle view containers
    document.querySelectorAll('.page-view').forEach((viewEl) => {
      if (viewEl.id === `view-${viewName}`) {
        viewEl.classList.add('active');
      } else {
        viewEl.classList.remove('active');
      }
    });

    // View-specific reloads
    if (viewName === 'overview') {
      this.loadStats();
      this.loadRecentActivity();
    } else if (viewName === 'patients') {
      window.Patients.loadPatients();
    } else if (viewName === 'reports') {
      window.Reports.loadAllRecentReports();
    } else if (viewName === 'audit') {
      this.loadAuditLogs();
    } else if (viewName === 'usb') {
      window.USBSecurity.scanDrives(false);
      window.USBSecurity.loadRegisteredKeys();
    }
  },

  async loadStats() {
    try {
      const stats = await API.getStats();

      const totalPatientsEl = document.getElementById('statTotalPatients');
      if (totalPatientsEl) totalPatientsEl.textContent = stats.total_patients;

      const totalReportsEl = document.getElementById('statTotalReports');
      if (totalReportsEl) totalReportsEl.textContent = stats.total_reports;

      const sensitiveReportsEl = document.getElementById('statSensitiveReports');
      if (sensitiveReportsEl) sensitiveReportsEl.textContent = stats.sensitive_reports_count;

      const visitsCountEl = document.getElementById('statVisitsCount');
      if (visitsCountEl) visitsCountEl.textContent = stats.recent_visits_count;

      const storageProviderEl = document.getElementById('statStorageProvider');
      if (storageProviderEl) {
        storageProviderEl.textContent = stats.storage_provider;
      }

      const driveBadgeEl = document.getElementById('googleDriveHeaderBadge');
      if (driveBadgeEl) {
        if (stats.google_drive_connected) {
          driveBadgeEl.className = 'badge badge-green';
          driveBadgeEl.innerHTML = '<i class="fa-brands fa-google-drive"></i> Google Drive Cloud Sync Active';
        } else {
          driveBadgeEl.className = 'badge badge-amber';
          driveBadgeEl.innerHTML = '<i class="fa-solid fa-hard-drive"></i> Encrypted Vault (Local Fallback)';
        }
      }
    } catch (err) {
      console.warn('Failed to load dashboard stats:', err);
    }
  },

  async loadRecentActivity() {
    try {
      const activity = await API.getRecentActivity();
      const recentPatients = activity.recent_patients || [];

      const listEl = document.getElementById('recentPatientsList');
      if (!listEl) return;

      if (recentPatients.length === 0) {
        listEl.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted);">No recent visits recorded.</div>';
        return;
      }

      listEl.innerHTML = recentPatients
        .map(
          (p) => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border: 1px solid var(--border-color); border-radius: var(--radius-md); margin-bottom: 8px; background: #fff;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="doctor-avatar" style="width: 36px; height: 36px; font-size: 12px; background: #e0f2fe; color: var(--primary); border: none;">
              <i class="fa-solid fa-user-injured"></i>
            </div>
            <div>
              <div style="font-weight: 600; font-size: 13px; color: var(--secondary);">${p.name}</div>
              <div style="font-size: 11px; color: var(--text-muted);">${p.diagnosis}</div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="badge badge-blue" style="font-size: 11px;"><i class="fa-regular fa-calendar"></i> ${p.visit_date}</span>
            <button class="icon-btn" title="View Patient" onclick="Patients.viewPatientDetail(${p.patient_id})">
              <i class="fa-solid fa-arrow-right"></i>
            </button>
          </div>
        </div>
      `
        )
        .join('');
    } catch (err) {
      console.warn('Failed to load recent activity:', err);
    }
  },

  async loadAuditLogs() {
    const tbody = document.getElementById('auditLogsTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading security audit trail...</td></tr>';

    try {
      const logs = await API.getAuditLogs();

      if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">No audit events recorded yet.</td></tr>';
        return;
      }

      tbody.innerHTML = logs
        .map((l) => {
          let badgeClass = 'badge-blue';
          if (l.action.includes('FAIL') || l.action.includes('DELETE')) badgeClass = 'badge-red';
          else if (l.action.includes('SUCCESS') || l.action.includes('REGISTER')) badgeClass = 'badge-green';
          else if (l.action.includes('USB')) badgeClass = 'badge-sensitive';

          return `
          <tr>
            <td><span style="font-size: 12px; color: var(--text-muted);">${new Date(l.timestamp).toLocaleString()}</span></td>
            <td><span class="badge ${badgeClass}">${l.action}</span></td>
            <td><strong>${l.doctor_email || 'System'}</strong></td>
            <td><span style="font-family: monospace; font-size: 12px;">${l.ip_address || '127.0.0.1'}</span></td>
            <td><div style="max-width: 320px; font-size: 13px; color: var(--text-main);">${l.details || 'N/A'}</div></td>
          </tr>
        `;
        })
        .join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger);">Failed to load audit logs: ${err.message}</td></tr>`;
    }
  },
};

window.Dashboard = Dashboard;

// Master Bootstrapping on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  window.Auth.init();
  window.Dashboard.init();
  window.Patients.init();
  window.Reports.init();
  window.USBSecurity.init();
});
