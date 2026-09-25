// MedSecure Patient Management Module

const Patients = {
  currentPatients: [],
  selectedPatient: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const addPatientBtn = document.getElementById('openAddPatientModalBtn');
    if (addPatientBtn) {
      addPatientBtn.addEventListener('click', () => this.openAddModal());
    }

    const reportFileInput = document.getElementById('patientNewReportFile');
    if (reportFileInput) {
      reportFileInput.addEventListener('change', (e) => {
        const preview = document.getElementById('patientNewReportPreview');
        if (e.target.files.length > 0 && preview) {
          const file = e.target.files[0];
          preview.style.display = 'block';
          preview.innerHTML = `<i class="fa-solid fa-file-circle-check"></i> Selected: <b>${file.name}</b> (${(file.size/1024).toFixed(0)} KB) — Ready for Google Drive upload`;
        } else if (preview) {
          preview.style.display = 'none';
        }
      });
    }

    const addPatientForm = document.getElementById('addPatientForm');
    if (addPatientForm) {
      addPatientForm.addEventListener('submit', (e) => this.handleSavePatient(e));
    }

    const searchInput = document.getElementById('patientSearchInput');
    if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.loadPatients(e.target.value.trim());
        }, 300);
      });
    }

    const headerSearch = document.getElementById('headerGlobalSearch');
    if (headerSearch) {
      headerSearch.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          window.Dashboard.switchView('patients');
          const pInput = document.getElementById('patientSearchInput');
          if (pInput) {
            pInput.value = headerSearch.value;
            this.loadPatients(headerSearch.value);
          }
        }
      });
    }

    window.addEventListener('auth:ready', () => {
      this.loadPatients();
    });
  },

  async loadPatients(search = '') {
    const tbody = document.getElementById('patientsTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading patient records...</td></tr>';

    try {
      const patients = await API.getPatients(search);
      this.currentPatients = patients;
      this.renderPatientsTable(patients);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 24px;">Failed to load patients: ${err.message}</td></tr>`;
    }
  },

  renderPatientsTable(patients) {
    const tbody = document.getElementById('patientsTableBody');
    if (!tbody) return;

    if (!patients || patients.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">No patient records found. Click <b>"Add New Patient"</b> to register one.</td></tr>';
      return;
    }

    tbody.innerHTML = patients
      .map(
        (p) => `
      <tr>
        <td>
          <strong style="color: var(--primary); font-family: monospace; font-size: 13px;">${p.patient_uid}</strong>
        </td>
        <td>
          <div style="font-weight: 600; color: var(--secondary);">${p.name}</div>
          <div style="font-size: 12px; color: var(--text-muted);">${p.phone || 'No phone'}</div>
        </td>
        <td>${p.age} yrs / ${p.gender}</td>
        <td>
          <div style="font-weight: 500; max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.diagnosis}">
            ${p.diagnosis}
          </div>
        </td>
        <td>
          <span class="badge badge-blue"><i class="fa-regular fa-calendar"></i> ${p.visit_date}</span>
        </td>
        <td>
          ${p.diagnosis.toLowerCase().includes('hiv') ? '<span class="badge badge-sensitive"><i class="fa-solid fa-lock"></i> Sensitive</span>' : '<span class="badge badge-green">Standard</span>'}
        </td>
        <td>
          <div class="action-btns">
            <button class="icon-btn" title="View Full Medical History & Reports" onclick="Patients.viewPatientDetail(${p.patient_id})">
              <i class="fa-solid fa-file-medical"></i>
            </button>
            <button class="icon-btn" title="Upload Medical Report" onclick="Reports.openUploadModal(${p.patient_id}, '${p.name.replace(/'/g, "\\'")}', '${p.patient_uid}')">
              <i class="fa-solid fa-cloud-arrow-up"></i>
            </button>
            <button class="icon-btn" title="Edit Patient Details" onclick="Patients.openEditModal(${p.patient_id})">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button class="icon-btn delete" title="Delete Patient Record" onclick="Patients.deletePatient(${p.patient_id}, '${p.name.replace(/'/g, "\\'")}')">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        </td>
      </tr>
    `
      )
      .join('');
  },

  openAddModal() {
    this.selectedPatient = null;
    const modal = document.getElementById('patientModal');
    const form = document.getElementById('addPatientForm');
    const title = document.getElementById('patientModalTitle');

    if (form) form.reset();
    if (title) title.textContent = 'Add New Patient Record';

    // Set today's date as default visit date
    const visitDateInput = document.getElementById('patientVisitDate');
    if (visitDateInput) {
      visitDateInput.value = new Date().toISOString().split('T')[0];
    }

    const reportFileInput = document.getElementById('patientNewReportFile');
    if (reportFileInput) reportFileInput.value = '';
    const reportPreview = document.getElementById('patientNewReportPreview');
    if (reportPreview) reportPreview.style.display = 'none';

    document.getElementById('patientEditId').value = '';
    if (modal) modal.classList.add('open');
  },

  async openEditModal(patientId) {
    try {
      const patient = await API.getPatient(patientId);
      this.selectedPatient = patient;

      document.getElementById('patientModalTitle').textContent = `Edit Patient: ${patient.name}`;
      document.getElementById('patientEditId').value = patient.patient_id;
      document.getElementById('patientName').value = patient.name;
      document.getElementById('patientPhone').value = patient.phone || '';
      document.getElementById('patientAge').value = patient.age;
      document.getElementById('patientGender').value = patient.gender;
      document.getElementById('patientDiagnosis').value = patient.diagnosis;
      document.getElementById('patientVisitDate').value = patient.visit_date;
      document.getElementById('patientHistory').value = patient.medical_history || '';
      document.getElementById('patientTreatment').value = patient.current_treatment || '';
      document.getElementById('patientMedicines').value = patient.current_medicines || '';
      document.getElementById('patientNotes').value = patient.doctor_notes || '';

      document.getElementById('patientModal').classList.add('open');
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },

  closePatientModal() {
    const modal = document.getElementById('patientModal');
    if (modal) modal.classList.remove('open');
  },

  async handleSavePatient(e) {
    e.preventDefault();
    const editId = document.getElementById('patientEditId').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    const patientData = {
      name: document.getElementById('patientName').value.trim(),
      phone: document.getElementById('patientPhone').value.trim(),
      age: parseInt(document.getElementById('patientAge').value, 10),
      gender: document.getElementById('patientGender').value,
      diagnosis: document.getElementById('patientDiagnosis').value.trim(),
      visit_date: document.getElementById('patientVisitDate').value,
      medical_history: document.getElementById('patientHistory').value.trim(),
      current_treatment: document.getElementById('patientTreatment').value.trim(),
      current_medicines: document.getElementById('patientMedicines').value.trim(),
      doctor_notes: document.getElementById('patientNotes').value.trim(),
    };

    // Check if an image/report file is attached
    const reportFileInput = document.getElementById('patientNewReportFile');
    const attachedFile = reportFileInput && reportFileInput.files.length > 0 ? reportFileInput.files[0] : null;
    const reportType = document.getElementById('patientNewReportType') ? document.getElementById('patientNewReportType').value : 'Patient Photo';

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving & Syncing to Google Drive...';

      if (editId) {
        await API.updatePatient(editId, patientData);
        if (attachedFile) {
          const formData = new FormData();
          formData.append('file', attachedFile);
          formData.append('report_type', reportType);
          formData.append('is_sensitive', reportType.toLowerCase().includes('hiv'));
          await API.uploadReport(editId, formData);
        }
        window.showToast('Patient record updated successfully!', 'success');
      } else {
        const newPatient = await API.createPatient(patientData);
        if (attachedFile) {
          const formData = new FormData();
          formData.append('file', attachedFile);
          formData.append('report_type', reportType);
          formData.append('is_sensitive', reportType.toLowerCase().includes('hiv'));
          await API.uploadReport(newPatient.patient_id, formData);
        }
        window.showToast('Patient record and document successfully saved & synced to Google Drive!', 'success');
      }

      this.closePatientModal();
      this.loadPatients();
      window.Dashboard.loadStats();
    } catch (err) {
      window.showToast(err.message || 'Error saving patient record.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Patient Record';
    }
  },

  async viewPatientDetail(patientId) {
    try {
      const patient = await API.getPatient(patientId);
      this.selectedPatient = patient;

      document.getElementById('detailPatientName').textContent = patient.name;
      document.getElementById('detailPatientUID').textContent = patient.patient_uid;
      document.getElementById('detailPatientDemographics').textContent = `${patient.age} yrs • ${patient.gender} • ${patient.phone || 'No phone recorded'}`;
      document.getElementById('detailPatientDiagnosis').textContent = patient.diagnosis;
      document.getElementById('detailPatientVisitDate').textContent = patient.visit_date;

      document.getElementById('detailPatientHistory').textContent = patient.medical_history || 'No previous history recorded.';
      document.getElementById('detailPatientTreatment').textContent = patient.current_treatment || 'No active treatment documented.';
      document.getElementById('detailPatientMedicines').textContent = patient.current_medicines || 'No prescribed medicines.';
      document.getElementById('detailPatientNotes').textContent = patient.doctor_notes || 'No confidential clinical notes.';

      // Render reports for this patient
      Reports.renderPatientDetailReports(patient.reports || [], patient.patient_id, patient.name, patient.patient_uid);

      document.getElementById('patientDetailModal').classList.add('open');
    } catch (err) {
      if (err.message && err.message.toLowerCase().includes('usb')) {
        window.USBSecurity.openUSBModal("⚠️ Access Blocked: You must insert your authorized physical USB Pen Drive into this computer to view patient clinical data.");
      } else {
        window.showToast(err.message, 'error');
      }
    }
  },

  closeDetailModal() {
    const modal = document.getElementById('patientDetailModal');
    if (modal) modal.classList.remove('open');
  },

  async deletePatient(patientId, patientName) {
    if (!confirm(`Are you sure you want to permanently delete patient record "${patientName}" and all associated medical reports?`)) {
      return;
    }

    try {
      await API.deletePatient(patientId);
      window.showToast(`Patient record deleted.`, 'info');
      this.loadPatients();
      window.Dashboard.loadStats();
    } catch (err) {
      window.showToast(err.message, 'error');
    }
  },
};

window.Patients = Patients;
