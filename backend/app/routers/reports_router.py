from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..config import settings
from ..database import get_db
from ..models import Patient, Report, Doctor
from ..schemas import ReportOut
from ..auth import get_current_doctor, verify_usb_session
from ..drive_service import drive_service
from ..audit import log_audit

router = APIRouter(tags=["Medical Reports"])

@router.post("/patients/{patient_id}/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def upload_patient_report(
    patient_id: int,
    request: Request,
    file: UploadFile = File(...),
    report_type: str = Form(..., description="X-Ray, Blood Report, HIV Report, Prescription, Scan Reports, Other"),
    is_sensitive: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Read and validate size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    # Automatically enforce high sensitivity for sensitive medical categories
    if "hiv" in report_type.lower() or "psychiatry" in report_type.lower() or "confidential" in report_type.lower():
        is_sensitive = True

    # Upload via Drive Service (or local vault fallback)
    file_id, provider, local_path = drive_service.upload_file(file, patient.patient_uid)

    new_report = Report(
        patient_id=patient_id,
        report_type=report_type,
        file_name=file.filename,
        file_type=file.content_type or ext,
        file_size=file_size,
        google_drive_file_id=file_id,
        local_storage_path=local_path,
        storage_provider=provider,
        is_sensitive=is_sensitive or False,
        uploaded_by=current_doctor.doctor_id
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    log_audit(
        db,
        action="UPLOAD_REPORT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="REPORT",
        target_id=str(new_report.report_id),
        details=f"Uploaded {report_type} for patient {patient.name} ({patient.patient_uid}). Sensitive={new_report.is_sensitive}",
        request=request
    )

    return new_report

@router.get("/patients/{patient_id}/reports", response_model=List[ReportOut])
def get_patient_reports(
    patient_id: int,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    reports = db.query(Report).filter(Report.patient_id == patient_id).order_by(desc(Report.uploaded_at)).all()
    return reports

@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report_metadata(
    report_id: int,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")
    return report

@router.get("/reports/{report_id}/view")
def view_report_content(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
    usb_verified: bool = Depends(verify_usb_session)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")

    # If this is marked sensitive (like HIV reports), require USB hardware security key verification!
    if report.is_sensitive and not usb_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="USB Security Verification Required: This document is classified as Highly Sensitive (e.g., HIV / Confidential record). Please insert your authorized USB security device to view."
        )

    stream, mime = drive_service.get_file_stream(
        report.google_drive_file_id,
        local_path=report.local_storage_path
    )

    log_audit(
        db,
        action="VIEW_REPORT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="REPORT",
        target_id=str(report.report_id),
        details=f"Viewed report: {report.file_name} ({report.report_type})",
        request=request
    )

    return StreamingResponse(
        stream,
        media_type=mime,
        headers={"Content-Disposition": f"inline; filename=\"{report.file_name}\""}
    )

@router.get("/reports/{report_id}/download")
def download_report_content(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
    usb_verified: bool = Depends(verify_usb_session)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")

    if report.is_sensitive and not usb_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="USB Security Verification Required for sensitive report download."
        )

    stream, mime = drive_service.get_file_stream(
        report.google_drive_file_id,
        local_path=report.local_storage_path
    )

    log_audit(
        db,
        action="DOWNLOAD_REPORT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="REPORT",
        target_id=str(report.report_id),
        details=f"Downloaded report: {report.file_name}",
        request=request
    )

    return StreamingResponse(
        stream,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=\"{report.file_name}\""}
    )

@router.delete("/reports/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")

    f_name = report.file_name
    drive_service.delete_file(report.google_drive_file_id, local_path=report.local_storage_path)
    db.delete(report)
    db.commit()

    log_audit(
        db,
        action="DELETE_REPORT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="REPORT",
        target_id=str(report_id),
        details=f"Deleted report: {f_name}",
        request=request
    )

    return {"message": f"Report '{f_name}' deleted successfully"}
