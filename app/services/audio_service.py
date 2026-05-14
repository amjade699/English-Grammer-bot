import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
    
    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded audio file."""
        if not file.filename or "." not in file.filename:
            raise HTTPException(
                status_code=400,
                detail="A filename with a valid extension is required",
            )
        # Check extension
        file_ext = file.filename.rsplit(".", 1)[-1].lower()
        if file_ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"File type '.{file_ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # File size will be checked during upload
        logger.info(f"File validation passed: {file.filename}")
    
    def save_audio(self, file: UploadFile) -> tuple[str, str, int]:
        """
        Save uploaded audio file to temporary storage.
        
        Returns:
            tuple: (file_id, file_path, file_size)
        """
        self.validate_file(file)
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_ext = file.filename.rsplit(".", 1)[-1].lower()
        file_path = self.upload_dir / f"{file_id}.{file_ext}"
        
        # Save file and track size
        file_size = 0
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_size = os.path.getsize(file_path)
            
            # Check file size after saving
            if file_size > settings.max_file_size_bytes:
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
                )
            
            logger.info(f"Audio saved: {file_id} ({file_size} bytes)")
            return file_id, str(file_path), file_size
            
        except HTTPException:
            raise
        except Exception as e:
            # Cleanup on error
            if file_path.exists():
                os.remove(file_path)
            logger.error(f"Error saving audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save audio: {str(e)}")
    
    def get_file_path(self, file_id: str) -> Path:
        """Get file path from file_id."""
        # Find file with this ID (any extension)
        matches = list(self.upload_dir.glob(f"{file_id}.*"))
        
        if not matches:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        return matches[0]
    
    def cleanup_file(self, file_id: str) -> None:
        """Delete temporary audio file."""
        try:
            file_path = self.get_file_path(file_id)
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_id}")
        except HTTPException:
            # File already deleted or not found
            pass
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_id}: {str(e)}")