import os
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  MedSecure • Secure Doctor Medical Record Management System  ")
    print("  FastAPI Backend + Google Drive API + USB Hardware Security ")
    print("=" * 60)
    print("  Server URL: http://localhost:8000")
    print("  API Docs:   http://localhost:8000/docs")
    print("  Default Login: doctor@fedmedx.org / Doctor@12345")
    print("=" * 60)
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
