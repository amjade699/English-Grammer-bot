from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class LanguageLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    message: str


class TranscriptionResponse(BaseModel):
    file_id: str
    transcript: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class GrammarError(BaseModel):
    original: str = Field(..., description="Original incorrect text")
    issue_type: str = Field(..., description="Type of grammatical error")
    explanation: str = Field(..., description="Explanation of the mistake")
    correction: str = Field(..., description="Corrected version")


class GrammarSummary(BaseModel):
    total_sentences: int
    total_errors: int
    overall_level: LanguageLevel


class GrammarAnalysisResponse(BaseModel):
    summary: GrammarSummary
    errors: List[GrammarError]
    corrected_transcript: str


class ProcessResponse(BaseModel):
    file_id: str
    transcript: TranscriptionResponse
    grammar_analysis: GrammarAnalysisResponse
    processing_time_seconds: float


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None