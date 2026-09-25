// MedSecure Medical Reports Module

const Reports = {
  currentUploadPatientId: null,
  selectedFile: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const uploadForm = document.getElementById('uploadReportForm');
    if (uploadForm) {
      uploadForm.addEventListener('submit', (e) => this.handleUploadSubmit(e));
    }

    const dropzone = document.getElementById('reportDropzone');
    const fileInput = document.getElementById('reportFileInput');

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());

      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          this.handleFileSelected(e.target.files[0]);
        }
      });

      ['dragenter', 'dragover'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.remove('dragover');
        });
      });

      dropzone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length > 0) {
          this.handleFileSelected(e.dataTransfer.files[0]);
        }
      });
    }

    // Auto-tick sensitive checkbox when HIV Report is selected
    const reportTypeSelect = document.getElementById('uploadReportType');
    const sensitiveCheckbox = document.getElementById('uploadIsSensitive');
    if (reportTypeSelect && sensitiveCheckbox) {
      reportTypeSelect.addEventListener('change', (e) => {
        if (e.target.value === 'HIV Report') {
          sensitiveCheckbox.checked = true;
        }
      });
    }

    window.addEventListener('auth:ready', () => {
      this.loadAllRecentReports();
    });
  },

  handleFileSelected(file) {
    const allowed = ['image/jpeg', 'image/png', 'application/pdf'];
    const ext = file.name.split('.').pop().toLowerCase();
    const validExts = ['jpg', 'jpeg', 'png', 'pdf'];

    if (!validExts.includes(ext)) {
      window.showToast('Invalid file format. Only JPG, PNG, and PDF files are supported.', 'error');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      window.showToast('File exceeds 25MB limit.', 'error');
      return;
    }

    this.selectedFile = file;
    const fileInfo = document.getElementById('selectedFileInfo');
    if (fileInfo) {
      fileInfo.style.display = 'block';
      fileInfo.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #e0f2fe; border: 1px solid #bae6fd; border-radius: var(--radius-md);">
          <div style="display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-file" style="color: var(--primary);"></i>
            <strong>${file.name}</strong>
            <span style="font-size: 12px; color: var(--text-muted);">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
          </div>
          <button type="button" class="icon-btn delete" onclick="Reports.clearSelectedFile()" style="width: 24px; height: 24px; font-size: 12px;">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      `;
    }
  },

  clearSelectedFile() {
    this.selectedFile = null;
    const fileInput = document.getElementById('reportFileInput');
    if (fileInput) fileInput.value = '';
    const fileInfo = document.getElementById('selectedFileInfo');
    if (fileInfo) fileInfo.style.display = 'none';
  },

  openUploadModal(patientId, patientName, patientUID) {
    this.currentUploadPatientId = patientId;
    this.clearSelectedFile();

    const titleEl = document.getElementById('uploadReportModalTitle');
    if (titleEl) {
      titleEl.textContent = `Upload Medical Report: ${patientName} (${patientUID})`;
    }

    const modal = document.getElementById('uploadReportModal');
    if (modal) modal.classList.add('open');
  },

  closeUploadModal() {
    const modal = document.getElementById('uploadReportModal');
    if (modal) modal.classList.remove('open');
  },

  async handleUploadSubmit(e) {
    e.preventDefault();
    if (!this.selectedFile) {
      window.showToast('Please select a report file to upload.', 'warning');
      return;
    }

    const reportType = document.getElementById('uploadReportType').value;
    const isSensitive = document.getElementById('uploadIsSensitive').checked;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    const formData = new FormData();
    formData.append('file', this.selectedFile);
    formData.append('report_type', reportType);
    formData.append('is_sensitive', isSensitive);

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Securely Uploading to Cloud...';

      const res = await API.uploadReport(this.currentUploadPatientId, formData);
      window.showToast(`Medical Report uploaded! Stored in ${res.storage_provider === 'google_drive' ? 'Google Drive Cloud' : 'Secure Vault'}.`, 'success');

      this.closeUploadModal();
      this.clearSelectedFile();

      // Refresh patient detail if open
      if (Patients.selectedPatient && Patients.selectedPatient.patient_id === this.currentUploadPatientId) {
        Patients.viewPatientDetail(this.currentUploadPatientId);
      }

      this.loadAllRecentReports();
      window.Dashboard.loadStats();
    } catch (err) {
      window.showToast(err.message || 'Report upload failed.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload Medical Document';
    }
  },

  renderPatientDetailReports(reports, patientId, patientName, patientUID) {
    const container = document.getElementById('detailReportsContainer');
    if (!container) return;

    if (!reports || reports.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--text-muted); background: #f8fafc; border-radius: var(--radius-md);">
          <i class="fa-regular fa-folder-open" style="font-size: 28px; margin-bottom: 8px; color: var(--text-light);"></i>
          <p>No medical reports uploaded yet for this patient.</p>
          <button class="btn-primary" style="margin-top: 10px; font-size: 13px;" onclick="Reports.openUploadModal(${patientId}, '${patientName.replace(/'/g, "\\'")}', '${patientUID}')">
            <i class="fa-solid fa-cloud-arrow-up"></i> Upload First Report
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h4 style="font-size: 14px; font-weight: 700;">Uploaded Reports & Diagnostic Documents (${reports.length})</h4>
        <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="Reports.openUploadModal(${patientId}, '${patientName.replace(/'/g, "\\'")}', '${patientUID}')">
          <i class="fa-solid fa-plus"></i> Upload Report
        </button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${reports
          .map(
            (r) => `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: #fff;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div class="stat-icon blue" style="width: 38px; height: 38px; font-size: 16px;">
                <i class="${r.file_type.includes('pdf') ? 'fa-solid fa-file-pdf' : 'fa-solid fa-file-image'}"></i>
              </div>
              <div>
                <div style="font-weight: 600; font-size: 13px; color: var(--secondary);">${r.file_name}</div>
                <div style="display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                  <span class="badge badge-blue">${r.report_type}</span>
                  <span>${(r.file_size / 1024).toFixed(0)} KB</span>
                  <span><i class="fa-regular fa-clock"></i> ${new Date(r.uploaded_at).toLocaleDateString()}</span>
                  ${r.is_sensitive ? '<span class="badge badge-sensitive"><i class="fa-solid fa-shield-halved"></i> Sensitive (HIV/Confidential)</span>' : ''}
                  <span class="badge ${r.storage_provider === 'google_drive' ? 'badge-green' : 'badge-amber'}">
                    <i class="fa-brands fa-google-drive"></i> ${r.storage_provider === 'google_drive' ? 'Google Drive Cloud' : 'Encrypted Vault'}
                  </span>
                </div>
              </div>
            </div>
            <div class="action-btns">
              <button class="icon-btn" title="Secure Preview Document" onclick="Reports.previewReport(${r.report_id}, '${r.file_name.replace(/'/g, "\\'")}', ${r.is_sensitive})">
                <i class="fa-solid fa-eye"></i>
              </button>
              <button class="icon-btn" title="Download Document" onclick="Reports.downloadReport(${r.report_id}, '${r.file_name.replace(/'/g, "\\'")}', ${r.is_sensitive})">
                <i class="fa-solid fa-download"></i>
              </button>
              <button class="icon-btn delete" title="Delete Report" onclick="Reports.deleteReport(${r.report_id}, ${patientId})">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        `
          )
          .join('')}
      </div>
    `;
  },

  async previewReport(reportId, fileName, isSensitive) {
    // If sensitive and no USB token present, prompt USB verification
    if (isSensitive && !API.getUSBToken()) {
      window.USBSecurity.openUSBModal('USB Security Verification Required: This document is classified as Highly Sensitive (e.g. HIV / Confidential Medical Record). Please authenticate with your USB device to view.');
      return;
    }

    try {
      window.showToast('Fetching secure document...', 'info');
      const blob = await API.viewReportBlob(reportId);
      const url = URL.createObjectURL(blob);

      const previewModal = document.getElementById('reportPreviewModal');
      const previewTitle = document.getElementById('reportPreviewTitle');
      const previewBody = document.getElementById('reportPreviewContent');

      previewTitle.textContent = fileName;
      previewBody.innerHTML = '';

      if (blob.type === 'application/pdf' || fileName.toLowerCase().endsWith('.pdf')) {
        previewBody.innerHTML = `<iframe src="${url}" style="width: 100%; height: 550px; border: none; border-radius: var(--radius-sm);"></iframe>`;
      } else {
        previewBody.innerHTML = `
          <div style="text-align: center; max-height: 550px; overflow: auto;">
            <img src="${url}" alt="${fileName}" style="max-width: 100%; border-radius: var(--radius-sm); box-shadow: 0 4px 12px rgba(0,0,0,0.1);" />
          </div>
        `;
      }

      previewModal.classList.add('open');
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  closePreviewModal() {
    const previewModal = document.getElementById('reportPreviewModal');
    if (previewModal) previewModal.classList.remove('open');
  },

  async downloadReport(reportId, fileName, isSensitive) {
    if (isSensitive && !API.getUSBToken()) {
      window.USBSecurity.openUSBModal('USB Security Verification Required for downloading sensitive medical record.');
      return;
    }

    try {
      window.showToast('Preparing secure download...', 'info');
      const blob = await API.viewReportBlob(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  async deleteReport(reportId, patientId) {
    if (!confirm('Are you sure you want to delete this medical report?')) return;
    try {
      await API.deleteReport(reportId);
      window.showToast('Report deleted successfully.', 'info');
      if (Patients.selectedPatient && Patients.selectedPatient.patient_id === patientId) {
        Patients.viewPatientDetail(patientId);
      }
      this.loadAllRecentReports();
      window.Dashboard.loadStats();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  async loadAllRecentReports() {
    const tbody = document.getElementById('recentReportsTableBody');
    if (!tbody) return;

    try {
      const activity = await API.getRecentActivity();
      const reports = activity.recent_reports || [];

      if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">No diagnostic reports uploaded yet.</td></tr>';
        return;
      }

      tbody.innerHTML = reports
        .map(
          (r) => `
        <tr>
          <td><strong style="font-size: 13px;">${r.file_name}</strong></td>
          <td>${r.patient_name} <br><small style="color: var(--text-muted); font-family: monospace;">${r.patient_uid}</small></td>
          <td><span class="badge badge-blue">${r.report_type}</span></td>
          <td>${r.is_sensitive ? '<span class="badge badge-sensitive"><i class="fa-solid fa-lock"></i> Sensitive</span>' : '<span class="badge badge-green">Standard</span>'}</td>
          <td>
            <button class="icon-btn" title="View Document" onclick="Reports.previewReport(${r.report_id}, '${r.file_name.replace(/'/g, "\\'")}', ${r.is_sensitive})">
              <i class="fa-solid fa-eye"></i>
            </button>
          </td>
        </tr>
      `
        )
        .join('');
    } catch (err) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger);">Failed to load recent reports.</td></tr>';
    }
  },
};

window.Reports = Reports;
