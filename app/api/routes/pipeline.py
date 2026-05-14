from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import logging
import time

from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.services.grammar_service import GrammarService
from app.models.responses import ProcessResponse, TranscriptionResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["End-to-End Processing"])


def get_audio_service():
    return AudioService()


def get_transcription_service():
    return TranscriptionService()


def get_grammar_service():
    return GrammarService()


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Complete audio processing pipeline",
    description="End-to-end processing: upload → transcribe → analyze grammar. Single endpoint for complete workflow."
)
async def process_audio_complete(
    file: UploadFile = File(..., description="Audio file (2-5 minutes)"),
    audio_service: AudioService = Depends(get_audio_service),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    grammar_service: GrammarService = Depends(get_grammar_service)
):
    """
    Complete processing pipeline in one request.
    
    Steps:
    1. Upload and validate audio file
    2. Transcribe audio to text using Whisper
    3. Analyze grammar using Groq LLM
    4. Return complete results
    
    - **file**: Audio file in supported format
    - Returns: Complete analysis including transcript and grammar corrections
    """
    start_time = time.time()
    logger.info(f"Starting complete pipeline for: {file.filename}")
    
    file_id = None
    
    try:
        # Step 1: Upload audio
        logger.info("Step 1/3: Uploading audio...")
        file_id, file_path, file_size = audio_service.save_audio(file)
        
        # Step 2: Transcribe
        logger.info("Step 2/3: Transcribing audio...")
        file_path_obj = audio_service.get_file_path(file_id)
        transcription_result = transcription_service.transcribe(file_path_obj)
        
        transcript_response = TranscriptionResponse(
            file_id=file_id,
            transcript=transcription_result["text"],
            duration_seconds=transcription_result.get("duration"),
            language=transcription_result.get("language")
        )
        
        # Step 3: Analyze grammar
        logger.info("Step 3/3: Analyzing grammar...")
        grammar_analysis = grammar_service.analyze_grammar(transcription_result["text"])
        
        # Calculate total processing time
        processing_time = time.time() - start_time
        
        logger.info(f"Pipeline complete in {processing_time:.2f}s")
        
        return ProcessResponse(
            file_id=file_id,
            transcript=transcript_response,
            grammar_analysis=grammar_analysis,
            processing_time_seconds=round(processing_time, 2)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
    
    finally:
        # Cleanup temporary file
        if file_id:
            try:
                audio_service.cleanup_file(file_id)
            except Exception as e:
                logger.warning(f"Cleanup failed for {file_id}: {str(e)}")