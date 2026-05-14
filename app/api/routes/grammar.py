from fastapi import APIRouter, HTTPException, Depends
import logging

from app.services.grammar_service import GrammarService
from app.models.requests import AnalyzeGrammarRequest
from app.models.responses import GrammarAnalysisResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/grammar", tags=["Grammar Analysis"])


def get_grammar_service():
    return GrammarService()


@router.post(
    "/analyze",
    response_model=GrammarAnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Analyze grammar",
    description="Analyze transcript for grammatical errors using Groq LLM."
)
async def analyze_grammar(
    request: AnalyzeGrammarRequest,
    grammar_service: GrammarService = Depends(get_grammar_service)
):
    """
    Analyze text for grammatical errors.
    
    - **transcript**: Full transcript text to analyze
    - Returns: Grammar errors, corrections, explanations, and corrected transcript
    """
    logger.info(f"Grammar analysis request (text length: {len(request.transcript)})")
    
    try:
        analysis = grammar_service.analyze_grammar(request.transcript)
        return analysis
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grammar analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))