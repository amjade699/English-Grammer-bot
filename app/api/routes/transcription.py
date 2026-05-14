from fastapi import APIRouter, HTTPException, Depends
import logging

from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.models.requests import TranscribeRequest
from app.models.responses import TranscriptionResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcription", tags=["Transcription"])


def get_audio_service():
    return AudioService()


def get_transcription_service():
    return TranscriptionService()


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Transcribe audio to text",
    description="Convert uploaded audio file to text using Whisper model."
)
async def transcribe_audio(
    request: TranscribeRequest,
    audio_service: AudioService = Depends(get_audio_service),
    transcription_service: TranscriptionService = Depends(get_transcription_service)
):
    """
    Transcribe audio file to text.
    
    - **file_id**: Reference ID from /upload-audio endpoint
    - Returns: Full transcript with metadata
    """
    logger.info(f"Transcription request for file: {request.file_id}")
    
    try:
        # Get file path
        file_path = audio_service.get_file_path(request.file_id)
        
        # Transcribe
        result = transcription_service.transcribe(file_path)
        
        return TranscriptionResponse(
            file_id=request.file_id,
            transcript=result["text"],
            duration_seconds=result.get("duration"),
            language=result.get("language")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))