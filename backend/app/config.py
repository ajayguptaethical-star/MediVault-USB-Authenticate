import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "secure_vault"
CREDENTIALS_DIR = BASE_DIR / "credentials"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "MedSecure - Doctor Medical Record Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "medsecure-super-secret-production-key-2026-medical-grade")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'medical_records.db'}")
    
    # Storage & Upload limits
    STORAGE_PATH: Path = STORAGE_DIR
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf"}
    ALLOWED_MIME_TYPES: set = {
        "image/jpeg",
        "image/png",
        "application/pdf",
    }
    
    # Google Drive API Target Folders
    GOOGLE_DRIVE_CREDENTIALS_FILE: Path = CREDENTIALS_DIR / "service_account.json"
    GOOGLE_DRIVE_OAUTH_TOKEN_FILE: Path = CREDENTIALS_DIR / "token.json"
    GOOGLE_DRIVE_PATIENT_FOLDER_ID: str = "1DYdRmBvRsPSzTZ7_XXxEMF725mv9yHis"
    GOOGLE_DRIVE_PATIENT_FOLDER_URL: str = "https://drive.google.com/drive/folders/1DYdRmBvRsPSzTZ7_XXxEMF725mv9yHis"
    GOOGLE_DRIVE_REPORTS_FOLDER_ID: str = "1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU"
    GOOGLE_DRIVE_REPORTS_FOLDER_URL: str = "https://drive.google.com/drive/folders/1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU?usp=drive_link"
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "1DYdRmBvRsPSzTZ7_XXxEMF725mv9yHis")
    GOOGLE_DRIVE_ALL_FOLDER_IDS: list = ["1DYdRmBvRsPSzTZ7_XXxEMF725mv9yHis", "1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU"]
    
    # USB Security Key settings (Strict Hardware Enforcement)
    USB_KEY_FILENAME: str = "medsecure.medkey"
    REQUIRE_USB_FOR_SENSITIVE: bool = True
    REQUIRE_HARDWARE_USB_FOR_PATIENT_ACCESS: bool = True

    class Config:
        case_sensitive = True

settings = Settings()
