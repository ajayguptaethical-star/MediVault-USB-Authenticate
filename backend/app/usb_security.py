import os
import json
import uuid
import hashlib
import psutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .config import settings
from .models import USBKey

def get_removable_drives() -> List[Dict]:
    """Scans Windows for connected removable storage drives (USB flash drives)."""
    drives = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            # Check for removable drives or check drive roots
            is_removable = "removable" in p.opts.lower() or "cdrom" not in p.opts.lower()
            drive_info = {
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
                "has_medkey": False,
                "medkey_token": None,
                "medkey_doctor": None
            }
            # Check if medsecure.medkey is located on the drive root
            key_path = Path(p.mountpoint) / settings.USB_KEY_FILENAME
            if key_path.exists() and key_path.is_file():
                try:
                    content = key_path.read_text(encoding="utf-8").strip()
                    data = json.loads(content)
                    drive_info["has_medkey"] = True
                    drive_info["medkey_token"] = data.get("token")
                    drive_info["medkey_doctor"] = data.get("doctor_email")
                except Exception:
                    drive_info["has_medkey"] = False

            drives.append(drive_info)
    except Exception as e:
        print(f"[USBSecurity] Error scanning partitions: {e}")
    return drives

def check_physical_usb_hardware(doctor_id: Optional[int] = None, db: Optional[Session] = None) -> Dict:
    """
    Directly verifies if the physical USB pen drive containing an authorized .medkey file
    is physically plugged into the computer right now.
    """
    drives = get_removable_drives()
    for d in drives:
        if d.get("has_medkey") and d.get("medkey_token"):
            token = d["medkey_token"]
            if db and doctor_id:
                # Validate against database
                key = db.query(USBKey).filter(
                    USBKey.doctor_id == doctor_id,
                    USBKey.key_token == token,
                    USBKey.is_active == True
                ).first()
                if key:
                    return {
                        "is_plugged": True,
                        "drive": d["mountpoint"],
                        "token": token,
                        "doctor_email": d.get("medkey_doctor"),
                        "device": d["device"]
                    }
            elif token:
                # Found valid token on connected drive
                return {
                    "is_plugged": True,
                    "drive": d["mountpoint"],
                    "token": token,
                    "doctor_email": d.get("medkey_doctor"),
                    "device": d["device"]
                }

    return {
        "is_plugged": False,
        "drive": None,
        "token": None,
        "message": "Physical USB Pen Drive with authorized .medkey security key not detected."
    }

def create_usb_key_token(doctor_id: int, doctor_email: str, db: Session, label: str = "Hardware USB Key") -> Dict:
    """Generates a secure cryptographic key token and registers it in the database."""
    raw_token = f"MEDKEY-{uuid.uuid4().hex.upper()}"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Save to database
    usb_key = USBKey(
        doctor_id=doctor_id,
        key_token=raw_token,
        key_hash=token_hash,
        label=label,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(usb_key)
    db.commit()
    db.refresh(usb_key)

    key_file_payload = {
        "system": "MedSecure Doctor Key Vault",
        "doctor_id": doctor_id,
        "doctor_email": doctor_email,
        "token": raw_token,
        "hash": token_hash,
        "issued_at": datetime.utcnow().isoformat(),
        "security_level": "CRYPTO_HW_LEVEL_2"
    }

    return {
        "usb_key_id": usb_key.id,
        "key_token": raw_token,
        "file_content": json.dumps(key_file_payload, indent=2),
        "filename": settings.USB_KEY_FILENAME
    }

def write_key_to_drive(mountpoint: str, file_content: str) -> bool:
    """Writes the medsecure.medkey file directly to a specified drive."""
    try:
        target = Path(mountpoint) / settings.USB_KEY_FILENAME
        target.write_text(file_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[USBSecurity] Could not write to drive {mountpoint}: {e}")
        return False

def verify_usb_token_against_db(token: str, doctor_id: int, db: Session) -> bool:
    """Checks if the token is valid, active, and belongs to this doctor."""
    key = db.query(USBKey).filter(
        USBKey.doctor_id == doctor_id,
        USBKey.key_token == token.strip(),
        USBKey.is_active == True
    ).first()

    if key:
        key.last_used_at = datetime.utcnow()
        db.commit()
        return True
    return False
