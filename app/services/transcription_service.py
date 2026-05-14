import whisper
import logging
from pathlib import Path
from fastapi import HTTPException
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscriptionService:
    def __init__(self):
        logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
        try:
            self.model = whisper.load_model(settings.WHISPER_MODEL)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise RuntimeError(f"Whisper initialization failed: {str(e)}")
    
    def transcribe(self, file_path: Path) -> dict:
        """
        Transcribe audio file using Whisper.
        
        Returns:
            dict: {
                "text": str,
                "language": str,
                "duration": float
            }
        """
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {file_path}")
        
        try:
            logger.info(f"Starting transcription: {file_path}")
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                str(file_path),
                language="en",  # Force English for grammar checking
                task="transcribe",
                verbose=False
            )
            
            transcript = result["text"].strip()
            language = result.get("language", "en")
            
            # Estimate duration (Whisper provides segments)
            duration = None
            if "segments" in result and result["segments"]:
                duration = result["segments"][-1]["end"]
            
            logger.info(f"Transcription complete. Length: {len(transcript)} chars")
            
            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail="No speech detected in audio file"
                )
            
            return {
                "text": transcript,
                "language": language,
                "duration": duration
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {str(e)}"
            )