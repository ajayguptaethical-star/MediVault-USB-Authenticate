import random
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from ..database import get_db
from ..models import Patient, Doctor, Report
from ..schemas import PatientCreate, PatientUpdate, PatientOut, PatientDetailOut
from ..auth import get_current_doctor, verify_usb_session
from ..audit import log_audit

router = APIRouter(prefix="/patients", tags=["Patient Management"])

def generate_patient_uid(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(Patient).count() + 1
    rand = random.randint(100, 999)
    return f"PAT-{year}-{count:04d}-{rand}"

@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    patient_uid = patient_in.patient_uid or generate_patient_uid(db)
    
    # Check for UID clash
    existing = db.query(Patient).filter(Patient.patient_uid == patient_uid).first()
    if existing:
        patient_uid = generate_patient_uid(db)

    new_patient = Patient(
        patient_uid=patient_uid,
        name=patient_in.name,
        phone=patient_in.phone,
        age=patient_in.age,
        gender=patient_in.gender,
        diagnosis=patient_in.diagnosis,
        medical_history=patient_in.medical_history,
        current_treatment=patient_in.current_treatment,
        current_medicines=patient_in.current_medicines,
        doctor_notes=patient_in.doctor_notes,
        visit_date=patient_in.visit_date,
        doctor_id=current_doctor.doctor_id
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # Automatically upload patient data record to Google Drive folder: 1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU
    from ..drive_service import drive_service
    patient_dict = {
        "patient_uid": new_patient.patient_uid,
        "name": new_patient.name,
        "phone": new_patient.phone,
        "age": new_patient.age,
        "gender": new_patient.gender,
        "diagnosis": new_patient.diagnosis,
        "medical_history": new_patient.medical_history,
        "current_treatment": new_patient.current_treatment,
        "current_medicines": new_patient.current_medicines,
        "doctor_notes": new_patient.doctor_notes,
        "visit_date": new_patient.visit_date,
        "attending_physician": current_doctor.name,
        "hospital": current_doctor.hospital_name,
        "target_google_drive_folder": "https://drive.google.com/drive/folders/1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU?usp=drive_link",
        "created_at": new_patient.created_at.isoformat()
    }
    gdrive_file_id, provider, file_path = drive_service.upload_patient_profile(
        patient_dict,
        new_patient.patient_uid,
        new_patient.name
    )

    # Attach this patient data record as a Medical Document report
    report_entry = Report(
        patient_id=new_patient.patient_id,
        report_type="Patient Health Record (EMR)",
        file_name=f"Patient_{new_patient.patient_uid}_Medical_Record.json",
        file_type="application/json",
        file_size=len(str(patient_dict).encode()),
        google_drive_file_id=gdrive_file_id,
        local_storage_path=file_path,
        storage_provider=provider,
        is_sensitive=new_patient.diagnosis.lower().find("hiv") != -1,
        uploaded_by=current_doctor.doctor_id
    )
    db.add(report_entry)
    db.commit()

    log_audit(
        db,
        action="CREATE_PATIENT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="PATIENT",
        target_id=str(new_patient.patient_id),
        details=f"Created record for {new_patient.name} ({new_patient.patient_uid}). Stored to Google Drive: {gdrive_file_id}",
        request=request
    )

    return new_patient

@router.get("", response_model=List[PatientOut])
def get_patients(
    search: Optional[str] = Query(None, description="Search by name, ID, phone, or diagnosis"),
    skip: int = 0,
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    query = db.query(Patient)
    
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.name.ilike(search_pattern),
                Patient.patient_uid.ilike(search_pattern),
                Patient.phone.ilike(search_pattern),
                Patient.diagnosis.ilike(search_pattern)
            )
        )

    patients = query.order_by(desc(Patient.created_at)).offset(skip).limit(limit).all()
    return patients

@router.get("/{patient_id}", response_model=PatientDetailOut)
def get_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
    usb_clearance: bool = Depends(verify_usb_session)
):
    # Strict Hardware USB Lock Enforcement: Doctor MUST have USB Pen Drive plugged in!
    if not usb_clearance:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="USB Pen Drive Not Detected: Doctor's authorized USB Security Key is not plugged into this computer. Please insert your USB Pen Drive to view patient records."
        )

    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    log_audit(
        db,
        action="VIEW_PATIENT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="PATIENT",
        target_id=str(patient.patient_id),
        details=f"Viewed record for {patient.name} ({patient.patient_uid}) with verified USB key.",
        request=request
    )

    return patient

@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    update_data = patient_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)

    log_audit(
        db,
        action="UPDATE_PATIENT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="PATIENT",
        target_id=str(patient.patient_id),
        details=f"Updated details for patient {patient.name} ({patient.patient_uid})",
        request=request
    )

    return patient

@router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    p_name = patient.name
    p_uid = patient.patient_uid
    db.delete(patient)
    db.commit()

    log_audit(
        db,
        action="DELETE_PATIENT",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="PATIENT",
        target_id=str(patient_id),
        details=f"Deleted patient record: {p_name} ({p_uid})",
        request=request
    )

    return {"message": f"Patient record {p_uid} deleted successfully"}
