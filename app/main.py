from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import shutil

REPO_ROOT = Path(__file__).resolve().parent.parent

# Add ffmpeg to PATH for Whisper
try:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
    else:
        logging.warning("FFmpeg not found in system PATH. Audio transcription may not work.")
except Exception as e:
    logging.error(f"Failed to setup FFmpeg: {e}")

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import audio, transcription, grammar, pipeline

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

if os.environ.get("GROQ_API_KEY"):
    logger.warning(
        "GROQ_API_KEY is set in the process environment; it overrides your project .env file. "
        "If grammar analysis fails with 401, remove or update the key in Windows Environment "
        "Variables, or run `Remove-Item Env:GROQ_API_KEY` in this PowerShell session."
    )

# Initialize FastAPI app
app = FastAPI(
    title="HMS Grammar Learning Bot API",
    description="Backend system for voice-based grammar learning with Whisper STT and Groq LLM analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio.router)
app.include_router(transcription.router)
app.include_router(grammar.router)
app.include_router(pipeline.router)

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - Serves the frontend UI."""
    return FileResponse(REPO_ROOT / "index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Suppress favicon 404 error from browsers."""
    return Response(status_code=204)

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "whisper_model": settings.WHISPER_MODEL,
        "groq_model": settings.GROQ_MODEL,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
