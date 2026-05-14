from pydantic import BaseModel, Field


class TranscribeRequest(BaseModel):
    file_id: str = Field(..., description="Reference ID of uploaded audio file")


class AnalyzeGrammarRequest(BaseModel):
    transcript: str = Field(..., min_length=10, description="Full transcript text to analyze")