from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    specialty = Column(String(120), default="General Medicine")
    phone = Column(String(30), nullable=True)
    hospital_name = Column(String(150), default="FedMedX Healthcare System")
    created_at = Column(DateTime, default=datetime.utcnow)

    patients = relationship("Patient", back_populates="doctor", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="doctor")
    usb_keys = relationship("USBKey", back_populates="doctor", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(50), unique=True, index=True, nullable=False)  # e.g., PAT-2026-001
    name = Column(String(120), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    
    # Clinical details
    diagnosis = Column(String(255), nullable=False)
    medical_history = Column(Text, nullable=True)
    current_treatment = Column(Text, nullable=True)
    current_medicines = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    visit_date = Column(String(50), nullable=False)
    
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="patients")
    reports = relationship("Report", back_populates="patient", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False, index=True)
    report_type = Column(String(80), nullable=False)  # X-Ray, Blood Report, HIV Report, Prescription, Scan Reports, Other
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(80), nullable=False)  # mime or extension
    file_size = Column(Integer, nullable=False)     # in bytes
    
    # Storage details
    google_drive_file_id = Column(String(150), nullable=True)
    local_storage_path = Column(String(255), nullable=True)
    storage_provider = Column(String(50), default="local")  # "google_drive" or "local"
    
    # High-privacy classification (e.g. HIV reports, psychiatric, etc.)
    is_sensitive = Column(Boolean, default=False)
    
    uploaded_by = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="reports")
    doctor = relationship("Doctor", back_populates="reports")


class USBKey(Base):
    __tablename__ = "usb_keys"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    key_token = Column(String(255), unique=True, nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    label = Column(String(120), default="Doctor Hardware Token")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    doctor = relationship("Doctor", back_populates="usb_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=True)
    doctor_email = Column(String(150), nullable=True)
    action = Column(String(80), nullable=False)  # LOGIN, PATIENT_ADD, REPORT_VIEW, etc.
    target_type = Column(String(50), nullable=True)  # PATIENT, REPORT, AUTH, USB
    target_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(60), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="audit_logs")
