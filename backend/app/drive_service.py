import os
import io
import uuid
import shutil
from pathlib import Path
from typing import Tuple, Optional, BinaryIO
from fastapi import UploadFile, HTTPException

from .config import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.is_connected = False
        self._init_client()

    def _init_client(self):
        """Initializes the Google Drive API client if service account json is present."""
        if not GOOGLE_LIBS_AVAILABLE:
            self.is_connected = False
            return

        creds_path = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        if creds_path.exists() and creds_path.is_file():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(creds_path), scopes=SCOPES
                )
                self.service = build('drive', 'v3', credentials=creds)
                self.is_connected = True
                print("[GoogleDriveService] Successfully authenticated with Google Drive API.")
            except Exception as e:
                print(f"[GoogleDriveService] Failed to initialize Google Drive client: {e}")
                self.is_connected = False
        else:
            self.is_connected = False

    def upload_patient_profile(self, patient_data: dict, patient_uid: str, patient_name: str) -> Tuple[str, str, str]:
        """
        Automatically exports and uploads patient data to the designated Google Drive folder.
        Target Folder: 1yf-glDrsL1pUPC_mdxKS7tqBH46RjZjU
        """
        import json
        clean_name = patient_name.replace(" ", "_")
        filename = f"Patient_{patient_uid}_{clean_name}_Medical_Record.json"
        content_bytes = json.dumps(patient_data, indent=2, default=str).encode('utf-8')

        if self.is_connected and self.service:
            try:
                file_metadata = {
                    'name': filename,
                    'description': f"Clinical Medical Record for {patient_name} ({patient_uid})",
                    'mimeType': 'application/json',
                    'parents': settings.GOOGLE_DRIVE_ALL_FOLDER_IDS
                }

                media = MediaIoBaseUpload(
                    io.BytesIO(content_bytes),
                    mimetype='application/json',
                    resumable=True
                )
                drive_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, mimeType, webViewLink'
                ).execute()

                file_id = drive_file.get('id')
                web_link = drive_file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
                print(f"[GoogleDriveService] Successfully uploaded patient record to Google Drive folders: {web_link}")
                return file_id, "google_drive", web_link
            except Exception as e:
                print(f"[GoogleDriveService] Failed to upload patient record to Drive: {e}")

        # Local secure vault fallback
        dest_path = settings.STORAGE_PATH / filename
        dest_path.write_bytes(content_bytes)
        local_id = f"gdrive_vault_{uuid.uuid4().hex[:12]}"
        return local_id, "local", str(dest_path)

    def upload_file(self, file: UploadFile, patient_uid: str) -> Tuple[str, str, str]:
        """
        Uploads file to Google Drive or falls back to local secure vault.
        Returns: (file_id, storage_provider, local_or_drive_path)
        """
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{patient_uid}_{uuid.uuid4().hex[:8]}_{file.filename}"

        # If Google Drive is connected, upload to Drive
        if self.is_connected and self.service:
            try:
                file_metadata = {
                    'name': unique_filename,
                    'description': f"Medical Record for Patient {patient_uid}",
                    'parents': settings.GOOGLE_DRIVE_ALL_FOLDER_IDS
                }

                # Reset file position
                file.file.seek(0)
                media = MediaIoBaseUpload(
                    file.file,
                    mimetype=file.content_type or 'application/octet-stream',
                    resumable=True
                )
                drive_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, mimeType, webViewLink'
                ).execute()

                drive_file_id = drive_file.get('id')
                return drive_file_id, "google_drive", drive_file_id
            except Exception as e:
                print(f"[GoogleDriveService] Drive upload failed, using secure vault: {e}")

        # Fallback: Secure Local Storage Vault
        dest_path = settings.STORAGE_PATH / unique_filename
        file.file.seek(0)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        mock_drive_id = f"gdrive_vault_{uuid.uuid4().hex}"
        return mock_drive_id, "local", str(dest_path)

    def get_file_stream(self, file_id: str, local_path: Optional[str] = None) -> Tuple[BinaryIO, str]:
        """
        Retrieves file stream for downloading or previewing.
        Returns: (io.BytesIO / file_handle, mime_type)
        """
        if self.is_connected and self.service and not file_id.startswith("gdrive_vault_"):
            try:
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                fh.seek(0)
                
                # Fetch metadata for mimeType
                meta = self.service.files().get(fileId=file_id, fields='mimeType').execute()
                mime = meta.get('mimeType', 'application/octet-stream')
                return fh, mime
            except Exception as e:
                print(f"[GoogleDriveService] Drive fetch failed: {e}")

        # Fallback to local storage path
        if local_path and os.path.exists(local_path):
            f = open(local_path, "rb")
            ext = Path(local_path).suffix.lower()
            mime = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
            return f, mime

        raise HTTPException(status_code=404, detail="Requested medical report file could not be found.")

    def delete_file(self, file_id: str, local_path: Optional[str] = None):
        """Deletes file from Google Drive and/or local vault."""
        if self.is_connected and self.service and not file_id.startswith("gdrive_vault_"):
            try:
                self.service.files().delete(fileId=file_id).execute()
            except Exception as e:
                print(f"[GoogleDriveService] Drive deletion error: {e}")

        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass

drive_service = GoogleDriveService()
