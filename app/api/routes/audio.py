from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Depends
import logging

from app.services.audio_service import AudioService
from app.models.responses import UploadResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audio", tags=["Audio"])


def get_audio_service():
    return AudioService()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Upload audio file",
    description="Upload an audio file (wav, mp3, webm) for processing. Returns a file_id for subsequent operations."
)
async def upload_audio(
    file: UploadFile = File(..., description="Audio file (2-5 minutes)"),
    audio_service: AudioService = Depends(get_audio_service)
):
    """
    Upload audio file and receive a file reference ID.
    
    - **file**: Audio file in supported format (wav, mp3, webm, m4a, ogg)
    - Returns: file_id, filename, size, and confirmation message
    """
    logger.info(f"Audio upload request: {file.filename}")
    
    try:
        file_id, file_path, file_size = audio_service.save_audio(file)
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            size_bytes=file_size,
            message="Audio file uploaded successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))