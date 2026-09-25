import os
import io
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_workflow():
    print("\n--- Starting MedSecure Automated Verification Suite ---")

    # 1. Test Doctor Login
    print("1. Testing Doctor Authentication (Default Seed Doctor)...")
    login_res = client.post("/api/auth/login", json={
        "email": "doctor@fedmedx.org",
        "password": "Doctor@12345"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   [PASS] Authenticated as {token_data['doctor']['name']}")

    # 2. Test Fetching Stats
    print("2. Testing Dashboard Stats Endpoint...")
    stats_res = client.get("/api/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    print(f"   [PASS] Total Patients: {stats['total_patients']}, Total Reports: {stats['total_reports']}")

    # 3. Test Creating Patient
    print("3. Testing Patient Creation...")
    patient_payload = {
        "name": "Alexander Vance",
        "phone": "+1 555 987 6543",
        "age": 45,
        "gender": "Male",
        "diagnosis": "Cardiovascular Hypertension & Angina",
        "medical_history": "Hyperlipidemia since 2019",
        "current_treatment": "Beta-blocker therapy & low sodium diet",
        "current_medicines": "Amlodipine 5mg, Metoprolol 25mg",
        "doctor_notes": "ECG stable. Follow up in 6 weeks.",
        "visit_date": "2026-09-21"
    }
    p_create_res = client.post("/api/patients", json=patient_payload, headers=headers)
    assert p_create_res.status_code == 201, f"Patient creation failed: {p_create_res.text}"
    patient = p_create_res.json()
    patient_id = patient["patient_id"]
    print(f"   [PASS] Created Patient: {patient['name']} ({patient['patient_uid']})")

    # 4. Test Searching Patients
    print("4. Testing Patient Search...")
    search_res = client.get("/api/patients?search=Alexander", headers=headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) > 0 and results[0]["name"] == "Alexander Vance"
    print(f"   [PASS] Search returned {len(results)} match(es)")

    # 5. Test Uploading Standard Report (X-Ray)
    print("5. Testing Diagnostic Report Upload (X-Ray image)...")
    dummy_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100)
    files = {"file": ("chest_xray.jpg", dummy_image, "image/jpeg")}
    data = {"report_type": "X-Ray", "is_sensitive": "false"}
    upload_res = client.post(f"/api/patients/{patient_id}/reports", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    report = upload_res.json()
    report_id = report["report_id"]
    print(f"   [PASS] Uploaded Report ID #{report_id} ({report['file_name']}) - Provider: {report['storage_provider']}")

    # 6. Test Uploading Sensitive Report (HIV Report)
    print("6. Testing Sensitive Report Upload (HIV Report - automatically gated)...")
    dummy_hiv_doc = io.BytesIO(b"%PDF-1.4\n%HIV Test Confidential\n%%EOF")
    files_hiv = {"file": ("hiv_screening.pdf", dummy_hiv_doc, "application/pdf")}
    data_hiv = {"report_type": "HIV Report", "is_sensitive": "true"}
    upload_hiv_res = client.post(f"/api/patients/{patient_id}/reports", data=data_hiv, files=files_hiv, headers=headers)
    assert upload_hiv_res.status_code == 201
    hiv_report = upload_hiv_res.json()
    assert hiv_report["is_sensitive"] is True
    hiv_report_id = hiv_report["report_id"]
    print(f"   [PASS] Uploaded HIV Report ID #{hiv_report_id} (Sensitive flag: True)")

    # 7. Verifying USB Security Gate with Unauthorized Doctor (Should be 403 Forbidden)
    print("7. Verifying USB Security Gate (Unauthorized doctor without physical USB key)...")
    # Register another doctor who does NOT have their key on F:\
    reg_other = client.post("/api/auth/register", json={
        "name": "Dr. Unauthorized Keyholder",
        "email": "unauthorized@hospital.org",
        "password": "Password@123",
        "specialty": "Visiting"
    })
    login_other = client.post("/api/auth/login", json={
        "email": "unauthorized@hospital.org",
        "password": "Password@123"
    })
    other_token = login_other.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    view_no_usb = client.get(f"/api/reports/{hiv_report_id}/view", headers=other_headers)
    assert view_no_usb.status_code == 403, f"Expected 403 Forbidden for unauthorized doctor, got {view_no_usb.status_code}"
    print(f"   [PASS] Security Gate Enforced: Doctor without valid USB hardware key was blocked (403 Forbidden)")

    # 8. Test Physical USB Pen Drive Detection for Dr. Sarah Jenkins
    print("8. Verifying Real Physical USB Pen Drive Detection...")
    hw_status = client.get("/api/usb/hardware-status", headers=headers).json()
    print(f"   [PASS] Physical Drive Status: {hw_status}")
    assert hw_status["is_plugged"] is True, "Physical USB Drive on F: should be detected as plugged in!"

    # 9. Test Accessing Sensitive Report with Authorized Doctor whose USB Pen Drive is inserted
    print("9. Verifying Sensitive Report Access WITH Doctor's Physical USB Pen Drive...")
    view_with_usb = client.get(f"/api/reports/{hiv_report_id}/view", headers=headers)
    assert view_with_usb.status_code == 200, f"Expected 200 OK with physical USB pen drive, got {view_with_usb.status_code}"
    print(f"   [PASS] Clearance Granted: Doctor with physical USB pen drive successfully accessed confidential files!")

    # 10. Test Audit Logs
    print("10. Testing HIPAA Audit Log Recording...")
    audit_res = client.get("/api/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs[:10]]
    print(f"   [PASS] Verified {len(logs)} audit entries. Recent actions: {actions[:4]}")

    print("\n========================================================")
    print("  ALL VERIFICATION TESTS PASSED SUCCESSFULLY! (10/10)   ")
    print("========================================================\n")

if __name__ == "__main__":
    test_full_workflow()
