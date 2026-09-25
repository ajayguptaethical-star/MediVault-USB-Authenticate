from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Doctor, USBKey
from .schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_doctor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Doctor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        doctor_id: int = payload.get("sub")
        email: str = payload.get("email")
        if doctor_id is None:
            raise credentials_exception
        token_data = TokenData(doctor_id=int(doctor_id), email=email)
    except JWTError:
        raise credentials_exception

    doctor = db.query(Doctor).filter(Doctor.doctor_id == token_data.doctor_id).first()
    if doctor is None:
        raise credentials_exception
    return doctor

def verify_usb_session(
    x_usb_token: Optional[str] = Header(None, alias="X-USB-Security-Token"),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
) -> bool:
    """Checks whether the physical USB drive is plugged in or a valid USB token is presented."""
    from .usb_security import check_physical_usb_hardware
    
    # 1. Direct real-time hardware scan of connected USB drives
    hw = check_physical_usb_hardware(doctor_id=current_doctor.doctor_id, db=db)
    if hw["is_plugged"]:
        return True

    # 2. Virtual / session token fallback
    if x_usb_token:
        key = db.query(USBKey).filter(
            USBKey.doctor_id == current_doctor.doctor_id,
            USBKey.key_token == x_usb_token,
            USBKey.is_active == True
        ).first()
        if key:
            return True

    return False

def require_usb_security(
    usb_verified: bool = Depends(verify_usb_session)
):
    """Enforces that the doctor has their authorized USB pen drive plugged in."""
    if not usb_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hardware USB Security Required: Doctor's authorized USB Pen Drive is not plugged into this computer. Please insert your USB Pen Drive to view patient records and medical files."
        )
    return True

