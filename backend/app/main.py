import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base, SessionLocal
from .models import Doctor, Patient, Report, USBKey
from .auth import hash_password
from .routers import auth_router, patients_router, reports_router, usb_router, stats_router

# Create database tables
Base.metadata.create_all(bind=engine)

def seed_initial_data():
    """Seeds default doctor and sample patient data if database is empty."""
    db = SessionLocal()
    try:
        # Check if default doctor exists
        default_email = "doctor@fedmedx.org"
        doctor = db.query(Doctor).filter(Doctor.email == default_email).first()
        if not doctor:
            doctor = Doctor(
                name="Dr. Sarah Jenkins, MD",
                email=default_email,
                password_hash=hash_password("Doctor@12345"),
                specialty="Internal Medicine & Infectious Diseases",
                phone="+1 (555) 432-8765",
                hospital_name="FedMedX Memorial Medical Center"
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
            print(f"[Seed] Created default doctor account: {default_email} / Doctor@12345")

        # Seed sample patients if none exist
        if db.query(Patient).count() == 0:
            sample_patients = [
                Patient(
                    patient_uid="PAT-2026-0010-842",
                    name="Elena Rostova",
                    phone="+1 (555) 019-2834",
                    age=38,
                    gender="Female",
                    diagnosis="Type 2 Diabetes Mellitus with Peripheral Neuropathy",
                    medical_history="Hypertension diagnosed 2021. Allergy to Penicillin.",
                    current_treatment="Glycemic control and dietary lifestyle modification.",
                    current_medicines="Metformin 850mg BD, Lisinopril 10mg OD, Pregabalin 75mg HS",
                    doctor_notes="Patient shows steady improvement in fasting glucose levels. Recommend HbA1c test in 3 months.",
                    visit_date="2026-09-18",
                    doctor_id=doctor.doctor_id
                ),
                Patient(
                    patient_uid="PAT-2026-0011-319",
                    name="David Chen",
                    phone="+1 (555) 018-9921",
                    age=52,
                    gender="Male",
                    diagnosis="Chronic Obstructive Pulmonary Disease (COPD) - Stage II",
                    medical_history="Former smoker (25 pack-years). Mild asthma in childhood.",
                    current_treatment="Bronchodilator maintenance and pulmonary rehabilitation.",
                    current_medicines="Tiotropium 18mcg inhaler, Salbutamol PRN, Formoterol BD",
                    doctor_notes="Chest auscultation reveals bilateral expiratory wheezes. Spirometry ordered.",
                    visit_date="2026-09-19",
                    doctor_id=doctor.doctor_id
                ),
                Patient(
                    patient_uid="PAT-2026-0012-764",
                    name="Marcus Sterling",
                    phone="+1 (555) 017-4452",
                    age=29,
                    gender="Male",
                    diagnosis="HIV-1 Infection (Asymptomatic - Stable on cART)",
                    medical_history="Diagnosed 2023. Baseline CD4 340 cells/uL.",
                    current_treatment="Combined Antiretroviral Therapy (cART). Viral load suppressed (<20 copies/mL).",
                    current_medicines="Biktarvy (Bictegravir/Emtricitabine/Tenofovir AF) 1 tablet daily",
                    doctor_notes="Confidential Health Record. Excellent adherence reported. Lipid profile and kidney functions within normal limits.",
                    visit_date="2026-09-20",
                    doctor_id=doctor.doctor_id
                )
            ]
            db.add_all(sample_patients)
            db.commit()
            print("[Seed] Seeded initial clinical patient records.")
    except Exception as e:
        print(f"[Seed] Error during seeding: {e}")
    finally:
        db.close()

# Seed upon import
seed_initial_data()

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_initial_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-security REST API for managing patient health records, diagnostic reports, and USB hardware authentication.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(patients_router.router, prefix=settings.API_V1_STR)
app.include_router(reports_router.router, prefix=settings.API_V1_STR)
app.include_router(usb_router.router, prefix=settings.API_V1_STR)
app.include_router(stats_router.router, prefix=settings.API_V1_STR)

# Serve Frontend static assets
frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
