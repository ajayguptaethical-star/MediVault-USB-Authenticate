from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models import Patient, Report, Doctor, AuditLog, USBKey
from ..schemas import DashboardStats, AuditLogOut
from ..auth import get_current_doctor
from ..drive_service import drive_service

router = APIRouter(tags=["Dashboard & Audit Analytics"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    total_patients = db.query(Patient).count()
    total_reports = db.query(Report).count()
    sensitive_reports = db.query(Report).filter(Report.is_sensitive == True).count()

    # Recent visits in last 7 days
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_visits = db.query(Patient).filter(Patient.created_at >= recent_cutoff).count()

    active_usb_keys = db.query(USBKey).filter(
        USBKey.doctor_id == current_doctor.doctor_id,
        USBKey.is_active == True
    ).count()

    return {
        "total_patients": total_patients,
        "total_reports": total_reports,
        "recent_visits_count": recent_visits,
        "sensitive_reports_count": sensitive_reports,
        "storage_provider": "Google Drive Cloud" if drive_service.is_connected else "Encrypted Vault (Local)",
        "google_drive_connected": drive_service.is_connected,
        "usb_security_enabled": active_usb_keys > 0
    }

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs

@router.get("/recent-activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    recent_patients = db.query(Patient).order_by(desc(Patient.created_at)).limit(5).all()
    recent_reports = db.query(Report).order_by(desc(Report.uploaded_at)).limit(5).all()

    return {
        "recent_patients": [
            {
                "patient_id": p.patient_id,
                "patient_uid": p.patient_uid,
                "name": p.name,
                "diagnosis": p.diagnosis,
                "visit_date": p.visit_date,
                "gender": p.gender,
                "age": p.age
            } for p in recent_patients
        ],
        "recent_reports": [
            {
                "report_id": r.report_id,
                "patient_id": r.patient_id,
                "patient_name": r.patient.name if r.patient else "Unknown",
                "patient_uid": r.patient.patient_uid if r.patient else "N/A",
                "report_type": r.report_type,
                "file_name": r.file_name,
                "is_sensitive": r.is_sensitive,
                "uploaded_at": r.uploaded_at.isoformat()
            } for r in recent_reports
        ]
    }
