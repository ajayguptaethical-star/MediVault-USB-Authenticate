from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db
from ..models import Doctor
from ..schemas import DoctorCreate, DoctorLogin, DoctorOut, Token
from ..auth import hash_password, verify_password, create_access_token, get_current_doctor
from ..audit import log_audit

router = APIRouter(prefix="/auth", tags=["Doctor Authentication"])

@router.post("/register", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def register_doctor(doctor_in: DoctorCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(Doctor).filter(Doctor.email == doctor_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A doctor with this email address is already registered."
        )

    hashed_pw = hash_password(doctor_in.password)
    new_doctor = Doctor(
        name=doctor_in.name,
        email=doctor_in.email,
        password_hash=hashed_pw,
        specialty=doctor_in.specialty or "General Medicine",
        phone=doctor_in.phone,
        hospital_name=doctor_in.hospital_name or "FedMedX Healthcare System"
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    log_audit(
        db,
        action="DOCTOR_REGISTER",
        doctor_id=new_doctor.doctor_id,
        doctor_email=new_doctor.email,
        target_type="DOCTOR",
        target_id=str(new_doctor.doctor_id),
        details=f"Doctor registered: {new_doctor.name} ({new_doctor.specialty})",
        request=request
    )

    return new_doctor

@router.post("/login", response_model=Token)
def login_doctor(login_data: DoctorLogin, request: Request, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.email == login_data.email).first()
    if not doctor or not verify_password(login_data.password, doctor.password_hash):
        log_audit(
            db,
            action="LOGIN_FAILED",
            doctor_email=login_data.email,
            target_type="AUTH",
            details="Invalid login credentials attempt",
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(doctor.doctor_id), "email": doctor.email})

    log_audit(
        db,
        action="LOGIN_SUCCESS",
        doctor_id=doctor.doctor_id,
        doctor_email=doctor.email,
        target_type="AUTH",
        target_id=str(doctor.doctor_id),
        details=f"Doctor logged in successfully: {doctor.email}",
        request=request
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "doctor": doctor
    }

@router.get("/me", response_model=DoctorOut)
def get_current_doctor_profile(current_doctor: Doctor = Depends(get_current_doctor)):
    return current_doctor
