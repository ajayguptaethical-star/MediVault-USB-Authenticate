from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Doctor, USBKey
from ..schemas import USBKeyOut, USBVerificationRequest
from ..auth import get_current_doctor
from ..audit import log_audit
from ..usb_security import (
    get_removable_drives,
    create_usb_key_token,
    write_key_to_drive,
    verify_usb_token_against_db
)

router = APIRouter(prefix="/usb", tags=["USB Security Hardware"])

class GenerateKeyRequest(BaseModel):
    label: Optional[str] = "Doctor Hardware Token"
    target_drive: Optional[str] = None  # e.g., "E:\\"

@router.get("/hardware-status")
def get_hardware_status(
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """
    Real-time check whether the doctor's physical USB Pen Drive is currently
    plugged into the computer.
    """
    from ..usb_security import check_physical_usb_hardware
    hw = check_physical_usb_hardware(doctor_id=current_doctor.doctor_id, db=db)
    return {
        "is_plugged": hw["is_plugged"],
        "drive": hw.get("drive"),
        "token": hw.get("token"),
        "doctor_name": current_doctor.name,
        "doctor_email": current_doctor.email,
        "message": "Physical USB Pen Drive is plugged in and verified." if hw["is_plugged"] else "Physical USB Pen Drive not detected. Insert USB Drive to view patient records."
    }

@router.get("/drives")
def scan_usb_drives(current_doctor: Doctor = Depends(get_current_doctor)):
    """Scans for connected USB drives and checks for valid medkey tokens."""
    drives = get_removable_drives()
    return {"drives": drives, "count": len(drives)}

@router.get("/keys", response_model=List[USBKeyOut])
def get_registered_keys(
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """Retrieves all registered USB security keys for the current doctor."""
    return db.query(USBKey).filter(USBKey.doctor_id == current_doctor.doctor_id).all()

@router.post("/generate-key")
def generate_key(
    req: GenerateKeyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """Issues a new cryptographic USB key and optionally writes to physical drive."""
    key_data = create_usb_key_token(
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        db=db,
        label=req.label or "Doctor Hardware Token"
    )

    written = False
    if req.target_drive:
        written = write_key_to_drive(req.target_drive, key_data["file_content"])

    log_audit(
        db,
        action="USB_KEY_GENERATED",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="USB",
        target_id=str(key_data["usb_key_id"]),
        details=f"Generated new USB token. Written to drive {req.target_drive}: {written}",
        request=request
    )

    return {
        "success": True,
        "token": key_data["key_token"],
        "filename": key_data["filename"],
        "written_to_drive": written,
        "file_content": key_data["file_content"],
        "message": f"USB Security Key successfully created for {current_doctor.name}."
    }

@router.post("/verify")
def verify_usb_token(
    req: USBVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """Verifies a physical or simulated USB key token."""
    is_valid = verify_usb_token_against_db(req.token, current_doctor.doctor_id, db)
    if not is_valid:
        log_audit(
            db,
            action="USB_VERIFY_FAILED",
            doctor_id=current_doctor.doctor_id,
            doctor_email=current_doctor.email,
            target_type="USB",
            details="Invalid or revoked USB security token presented",
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="USB Security Verification Failed: Key token is invalid or unauthorized."
        )

    log_audit(
        db,
        action="USB_VERIFY_SUCCESS",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="USB",
        details="Hardware USB security device verified successfully",
        request=request
    )

    return {
        "verified": True,
        "doctor_name": current_doctor.name,
        "token": req.token,
        "message": "USB Security Device Verified. Full clearance granted."
    }

@router.delete("/keys/{key_id}")
def revoke_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """Revokes a registered USB security key."""
    key = db.query(USBKey).filter(
        USBKey.id == key_id,
        USBKey.doctor_id == current_doctor.doctor_id
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    key.is_active = False
    db.commit()

    log_audit(
        db,
        action="USB_KEY_REVOKED",
        doctor_id=current_doctor.doctor_id,
        doctor_email=current_doctor.email,
        target_type="USB",
        target_id=str(key_id),
        details="Revoked USB hardware security token",
        request=request
    )

    return {"message": "USB Security Key revoked successfully"}
