# MedSecure • Secure Doctor Medical Record Management Dashboard

A modern, highly secure, and professional **Doctor Medical Record Management System** built with **FastAPI**, **SQLite**, **Google Drive API v3**, and a **USB Hardware Security Key** layer.

---

## 🌟 Key Features

1. **Doctor Authentication & RBAC**:
   - Secure login using Doctor Email and Password.
   - Passwords hashed with high-entropy `bcrypt`.
   - Signed JSON Web Tokens (JWT) for session and API authorization.
   - Pre-seeded default doctor account (`doctor@fedmedx.org` / `Doctor@12345`).

2. **Patient Medical Record Management**:
   - Complete clinical profile: Name, Unique Patient UID (e.g., `PAT-2026-XXXX`), Phone, Age, Gender, Disease / Diagnosis, Medical History, Treatment Protocol, Medicines, Confidential Notes, Visit Date.
   - Real-time search by Patient Name, UID, Phone, or Diagnosis.
   - Interactive Patient Detail Modal with full clinical history and timeline.

3. **Medical Report Upload & Cloud Storage**:
   - Diagnostic categories: **X-Ray**, **Blood Report**, **HIV Report**, **Prescription**, **Scan Reports**, and Other Documents.
   - Supported formats: **JPG**, **JPEG**, **PNG**, **PDF** (up to 25MB).
   - In-browser document preview lightbox (view PDFs & images directly without leaving the app).
   - Direct integration with the **Google Drive API v3** to store files in the doctor's configured institutional Google Drive folder.
   - Automatic encrypted local vault fallback if Google Drive credentials are not yet configured.

4. **USB Hardware Security Key Layer (High-Privacy Protection)**:
   - Extra security layer designed for doctor workstations.
   - Physical USB scanning: detects connected removable flash drives on Windows and authenticates against cryptographic `.medkey` tokens on the drive.
   - Built-in **Token Generator** to format any USB flash drive.
   - One-Click **Demo USB Simulation** mode for presentations/testing.
   - Highly sensitive records (such as **HIV Reports** and confidential notes) are strictly gated behind USB verification.

5. **HIPAA-Grade Security & Audit Logging**:
   - Comprehensive audit logging recording every login, patient record access, report upload, report preview/download, and USB verification event with timestamps and IP addresses.

---

## 🚀 Quick Start

### 1. Run the Application
Open PowerShell in this directory and run:
```powershell
python run.py
```

### 2. Access the Application
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive REST API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Redoc API**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Default Doctor Credentials
- **Email**: `doctor@fedmedx.org`
- **Password**: `Doctor@12345`

*(You can also click "Register New Doctor" to create custom physician credentials).*

---

## ☁️ Configuring Google Drive API (Optional)

1. Create a Google Cloud Project and enable the **Google Drive API**.
2. Create a **Service Account** with Drive access.
3. Download the JSON key file and rename it to:
   ```text
   credentials/service_account.json
   ```
4. Share your target Google Drive folder with the service account email (with Editor permission).
5. Set the folder ID in your environment or `backend/app/config.py`:
   ```bash
   export GOOGLE_DRIVE_FOLDER_ID="your_folder_id_here"
   ```
*If no credentials file is present, MedSecure automatically stores files in the secure local vault (`storage/secure_vault/`), ensuring 100% offline usability out-of-the-box.*

---

## 🔑 How the USB Hardware Security Key Works

```text
Doctor Login (Email + Password)
          ↓
     Dashboard
          ↓
Attempting to View Sensitive Record (e.g. HIV Report)
          ↓
Is USB Security Key Active in Session?
     ├── NO ──> Prompts Doctor to insert authorized USB Drive or Enter Token
     └── YES ─> Full Clearance: Secure Document Streamed & Rendered
```

1. Go to the **USB Security Key** tab in the sidebar.
2. Click **"Generate & Download .medkey Token"**.
3. Save or copy `medsecure.medkey` to the root directory of your USB flash drive (e.g. `E:\medsecure.medkey`).
4. Click **"Scan USB Ports"** -> **"Authenticate Drive"**.
5. Alternatively, for testing without a USB drive, click **"Simulate Hardware USB Key Insertion"**.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new physician account |
| `POST` | `/api/auth/login` | Authenticate doctor and receive JWT access token |
| `GET` | `/api/auth/me` | Retrieve current authenticated doctor profile |
| `GET` | `/api/patients` | List/search all patient clinical records |
| `POST` | `/api/patients` | Create new patient record |
| `GET` | `/api/patients/{id}` | Retrieve patient details and complete history |
| `PUT` | `/api/patients/{id}` | Update patient medical record |
| `DELETE` | `/api/patients/{id}` | Permanently delete patient record |
| `POST` | `/api/patients/{id}/reports` | Upload diagnostic report (X-Ray, Blood, HIV, etc.) |
| `GET` | `/api/patients/{id}/reports` | List diagnostic reports for a patient |
| `GET` | `/api/reports/{id}/view` | Stream document for in-browser preview (USB-gated) |
| `GET` | `/api/reports/{id}/download` | Download diagnostic document (USB-gated) |
| `DELETE` | `/api/reports/{id}` | Delete medical report from DB & Cloud Storage |
| `GET` | `/api/usb/drives` | Scan connected removable storage devices |
| `POST` | `/api/usb/generate-key` | Issue cryptographic hardware key token |
| `POST` | `/api/usb/verify` | Verify USB hardware security token |
| `GET` | `/api/stats` | Retrieve system analytics and storage status |
| `GET` | `/api/audit-logs` | Retrieve HIPAA security audit trail |
