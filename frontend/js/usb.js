// MedSecure USB Security Key Module

const USBSecurity = {
  activeToken: null,
  registeredKeys: [],

  isPhysicalPlugged: false,
  physicalDrive: null,
  pollTimer: null,

  init() {
    this.activeToken = API.getUSBToken();
    this.bindEvents();
    this.loadRegisteredKeys();
    this.startHardwarePolling();
  },

  startHardwarePolling() {
    // Immediate check
    this.checkHardwareLive();
    // Poll hardware state every 3.5 seconds
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = setInterval(() => {
      this.checkHardwareLive();
    }, 3500);
  },

  async checkHardwareLive() {
    try {
      const res = await API.getHardwareStatus();
      this.isPhysicalPlugged = res.is_plugged;
      this.physicalDrive = res.drive;

      if (res.is_plugged && res.token) {
        this.activeToken = res.token;
        API.setUSBToken(res.token);
      } else if (!sessionStorage.getItem('medsecure_demo_token')) {
        // If not plugged and not explicit demo simulation
        this.activeToken = null;
        API.removeUSBToken();
      }
      this.updateStatusBadge();
    } catch (e) {
      // Ignore background network errors
    }
  },

  bindEvents() {
    const badge = document.getElementById('usbStatusBadge');
    if (badge) {
      badge.addEventListener('click', () => this.openUSBModal());
    }

    const scanBtn = document.getElementById('scanUSBDrivesBtn');
    if (scanBtn) {
      scanBtn.addEventListener('click', () => this.scanDrives());
    }

    const genKeyBtn = document.getElementById('generateUSBKeyBtn');
    if (genKeyBtn) {
      genKeyBtn.addEventListener('click', () => this.generateKey());
    }

    const verifyTokenForm = document.getElementById('verifyTokenForm');
    if (verifyTokenForm) {
      verifyTokenForm.addEventListener('submit', (e) => this.handleManualVerify(e));
    }

    const simulateBtn = document.getElementById('simulateUSBKeyBtn');
    if (simulateBtn) {
      simulateBtn.addEventListener('click', () => this.simulateDemoKey());
    }

    window.addEventListener('usb:required', (e) => {
      this.openUSBModal(e.detail);
    });

    window.addEventListener('auth:ready', () => {
      this.loadRegisteredKeys();
      this.checkHardwareLive();
    });
  },

  updateStatusBadge() {
    const badge = document.getElementById('usbStatusBadge');
    if (!badge) return;

    if (this.isPhysicalPlugged) {
      badge.className = 'usb-status-badge connected';
      badge.innerHTML = `<i class="fa-solid fa-usb" style="color: #059669;"></i> <span>Physical Pen Drive (${this.physicalDrive || 'USB'}) Active & Unlocked</span>`;
    } else if (this.activeToken) {
      badge.className = 'usb-status-badge connected';
      badge.innerHTML = '<i class="fa-solid fa-shield-halved"></i> <span>USB Security: Token Active</span>';
    } else {
      badge.className = 'usb-status-badge disconnected';
      badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: #dc2626;"></i> <span>USB Pen Drive: Not Inserted (Locked)</span>';
    }
  },

  openUSBModal(warningMessage = null) {
    const modal = document.getElementById('usbModal');
    if (modal) {
      modal.classList.add('open');
      const warningEl = document.getElementById('usbSecurityWarning');
      if (warningEl) {
        if (warningMessage) {
          warningEl.textContent = warningMessage;
          warningEl.style.display = 'block';
        } else {
          warningEl.style.display = 'none';
        }
      }
      this.scanDrives(true);
    }
  },

  closeUSBModal() {
    const modal = document.getElementById('usbModal');
    if (modal) modal.classList.remove('open');
  },

  async scanDrives(showAlert = true) {
    const container = document.getElementById('usbDrivesList');
    if (container) {
      container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Scanning for connected drives...</div>';
    }

    try {
      const res = await API.scanUSBDrives();
      const drives = res.drives || [];

      if (!container) return;
      container.innerHTML = '';

      if (drives.length === 0) {
        container.innerHTML = `
          <div class="empty-state" style="padding: 16px; text-align: center; color: var(--text-muted);">
            <i class="fa-solid fa-usb" style="font-size: 24px; margin-bottom: 8px; color: var(--text-light);"></i>
            <p>No removable USB flash drives detected.</p>
            <small>You can use the <b>Virtual Security Key Demo</b> below to simulate physical hardware key insertion.</small>
          </div>
        `;
        return;
      }

      drives.forEach((d) => {
        const driveCard = document.createElement('div');
        driveCard.style.cssText = 'padding: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-md); margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; background: #fff;';

        const hasKey = d.has_medkey;
        driveCard.innerHTML = `
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <i class="fa-solid fa-hard-drive" style="color: var(--primary);"></i>
              <strong>Drive ${d.device} (${d.mountpoint})</strong>
              ${hasKey ? '<span class="badge badge-green"><i class="fa-solid fa-check"></i> .medkey Found</span>' : '<span class="badge badge-amber">Empty Root</span>'}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
              Format: ${d.fstype || 'Removable'} | Opts: ${d.opts || 'rw'}
            </div>
          </div>
          <div>
            ${hasKey ? `<button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="USBSecurity.verifyDriveKey('${d.medkey_token}')"><i class="fa-solid fa-key"></i> Authenticate Drive</button>` : `<button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="USBSecurity.writeKeyToDrive('${d.mountpoint.replace(/\\/g, '\\\\')}')"><i class="fa-solid fa-download"></i> Install Key Here</button>`}
          </div>
        `;
        container.appendChild(driveCard);
      });

      if (showAlert) {
        window.showToast(`Drive scan completed. Found ${drives.length} drives.`, 'info');
      }
    } catch (err) {
      if (container) {
        container.innerHTML = '<p style="color: var(--danger); font-size: 13px;">Error scanning hardware drives.</p>';
      }
    }
  },

  async verifyDriveKey(token) {
    if (!token) return;
    try {
      const res = await API.verifyUSBToken(token);
      this.activeToken = token;
      API.setUSBToken(token);
      this.updateStatusBadge();
      window.showToast(res.message, 'success');
      this.closeUSBModal();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  async handleManualVerify(e) {
    e.preventDefault();
    const tokenInput = document.getElementById('manualUSBTokenInput');
    const token = tokenInput ? tokenInput.value.trim() : '';
    if (!token) return;

    try {
      const res = await API.verifyUSBToken(token);
      this.activeToken = token;
      API.setUSBToken(token);
      this.updateStatusBadge();
      window.showToast(res.message, 'success');
      this.closeUSBModal();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  async generateKey(targetDrive = null) {
    try {
      const res = await API.generateUSBKey("Doctor Security USB Key", targetDrive);
      window.showToast('Cryptographic Security Key generated successfully!', 'success');

      // Trigger download of the .medkey file so user can copy to any flash drive
      const blob = new Blob([res.file_content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = res.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      // Auto-populate token in verification input
      const tokenInput = document.getElementById('manualUSBTokenInput');
      if (tokenInput) tokenInput.value = res.token;

      this.loadRegisteredKeys();
      this.scanDrives(false);
    } catch (err) {
      window.showToast(err.message || 'Failed to generate USB key.', 'error');
    }
  },

  async writeKeyToDrive(mountpoint) {
    await this.generateKey(mountpoint);
  },

  async simulateDemoKey() {
    // Generates key and automatically verifies it in current session for live demonstration
    try {
      const res = await API.generateUSBKey("Virtual Demo Key Simulator");
      const token = res.token;
      await API.verifyUSBToken(token);
      this.activeToken = token;
      API.setUSBToken(token);
      this.updateStatusBadge();
      window.showToast("Virtual USB Key Verified! Full clearance granted.", "success");
      this.closeUSBModal();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  async loadRegisteredKeys() {
    try {
      const keys = await API.getUSBKeys();
      this.registeredKeys = keys;
      this.renderRegisteredKeys(keys);
    } catch (err) {
      console.warn('Could not load USB keys:', err);
    }
  },

  renderRegisteredKeys(keys) {
    const listEl = document.getElementById('registeredUSBKeysList');
    if (!listEl) return;

    if (!keys || keys.length === 0) {
      listEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No hardware keys issued yet.</p>';
      return;
    }

    listEl.innerHTML = keys
      .map(
        (k) => `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 6px; font-size: 13px;">
        <div>
          <strong>${k.label}</strong> (ID: #${k.id})
          <div style="font-size: 11px; color: var(--text-light);">Issued: ${new Date(k.created_at).toLocaleDateString()} | ${k.is_active ? '<span style="color: var(--accent); font-weight: 600;">Active</span>' : '<span style="color: var(--danger);">Revoked</span>'}</div>
        </div>
        ${k.is_active ? `<button class="btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="USBSecurity.revokeKey(${k.id})">Revoke</button>` : ''}
      </div>
    `
      )
      .join('');
  },

  async revokeKey(keyId) {
    if (!confirm('Are you sure you want to revoke this security key?')) return;
    try {
      await API.revokeUSBKey(keyId);
      window.showToast('Security Key revoked.', 'info');
      if (this.activeToken) {
        this.activeToken = null;
        API.removeUSBToken();
        this.updateStatusBadge();
      }
      this.loadRegisteredKeys();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  }
};

window.USBSecurity = USBSecurity;
