from datetime import datetime
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from .models import AuditLog

def log_audit(
    db: Session,
    action: str,
    doctor_id: Optional[int] = None,
    doctor_email: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[str] = None,
    request: Optional[Request] = None
):
    """Utility to record HIPAA/medical audit log events."""
    ip_address = None
    if request and request.client:
        ip_address = request.client.host

    audit_entry = AuditLog(
        doctor_id=doctor_id,
        doctor_email=doctor_email,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details=details,
        ip_address=ip_address,
        timestamp=datetime.utcnow()
    )
    try:
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AuditLog] Failed to record log: {e}")
