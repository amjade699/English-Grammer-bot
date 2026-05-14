import json
import logging
from groq import Groq
from groq import AuthenticationError, BadRequestError, RateLimitError, APIStatusError
from fastapi import HTTPException
from typing import Dict, Any

from app.core.config import get_settings
from app.models.responses import GrammarAnalysisResponse, GrammarSummary, GrammarError, LanguageLevel

logger = logging.getLogger(__name__)
settings = get_settings()


class GrammarService:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        logger.info(f"Groq client initialized with model: {self.model}")
    
    def _build_grammar_prompt(self, transcript: str) -> str:
        """
        Build the grammar analysis prompt for Groq LLM.
        
        This prompt is engineered to:
        - Handle spoken English nuances
        - Account for ASR transcription errors
        - Provide professional corrections
        - Output strict JSON format
        """
        prompt = f"""You are an expert English grammar teacher analyzing spoken English transcribed from audio.

IMPORTANT CONTEXT:
- This text was spoken naturally, then transcribed by speech recognition (ASR)
- ASR may introduce errors like missing punctuation, run-on sentences, or misheard words
- Focus on genuine grammatical mistakes, not ASR artifacts
- Preserve the speaker's original meaning and intent

YOUR TASK:
Analyze the following transcript for grammatical errors and provide:
1. A summary of total sentences, total errors, and overall language proficiency level
2. A list of all grammatical errors with corrections and explanations
3. A fully corrected version of the entire transcript

TRANSCRIPT:
{transcript}

OUTPUT REQUIREMENTS:
You MUST respond with ONLY valid JSON in this EXACT format (no markdown, no extra text):

{{
  "summary": {{
    "total_sentences": <number>,
    "total_errors": <number>,
    "overall_level": "<Beginner|Intermediate|Advanced>"
  }},
  "errors": [
    {{
      "original": "<exact incorrect phrase or sentence>",
      "issue_type": "<type of error: e.g., Subject-Verb Agreement, Tense Error, Article Usage, Word Choice, etc.>",
      "explanation": "<clear explanation of why this is wrong and the rule being violated>",
      "correction": "<the corrected version>"
    }}
  ],
  "corrected_transcript": "<full transcript with all corrections applied, maintaining natural flow>"
}}

ANALYSIS GUIDELINES:
- Consider common spoken English patterns (contractions, informal language)
- Distinguish between grammar errors and stylistic choices
- For "overall_level": 
  - Beginner: Multiple basic errors (subject-verb, articles, tenses)
  - Intermediate: Occasional errors, mostly correct structures
  - Advanced: Rare errors, complex structures mostly correct
- If no errors found, return empty "errors" array and original transcript as "corrected_transcript"
- Be specific in explanations - teach, don't just correct

OUTPUT ONLY THE JSON. DO NOT include any preamble, explanations, or markdown formatting."""

        return prompt
    
    def analyze_grammar(self, transcript: str) -> GrammarAnalysisResponse:
        """
        Analyze transcript for grammar mistakes using Groq LLM.
        
        Args:
            transcript: Full transcribed text
            
        Returns:
            GrammarAnalysisResponse with structured error analysis
        """
        if not transcript or len(transcript.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Transcript too short for meaningful analysis"
            )
        
        try:
            logger.info(f"Starting grammar analysis (transcript length: {len(transcript)})")
            
            # Build prompt
            prompt = self._build_grammar_prompt(transcript)
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional English grammar analysis system. You respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,  # Low temperature for consistent, accurate analysis
                max_tokens=4000,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Extract response
            response_text = chat_completion.choices[0].message.content
            logger.info(f"Received LLM response ({len(response_text)} chars)")
            
            # Parse JSON response
            try:
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.debug(f"Raw response: {response_text[:500]}")
                raise HTTPException(
                    status_code=500,
                    detail="LLM returned invalid JSON format"
                )
            
            # Validate and build response
            return self._parse_analysis_response(analysis_data)
            
        except HTTPException:
            raise
        except AuthenticationError as e:
            logger.error("Groq authentication failed: invalid or revoked GROQ_API_KEY")
            raise HTTPException(
                status_code=502,
                detail=(
                    "Groq rejected the API key (401). Create a new key at "
                    "https://console.groq.com/keys , put it in .env as GROQ_API_KEY, "
                    "restart the server, and ensure there are no extra spaces or quotes."
                ),
            ) from e
        except RateLimitError as e:
            logger.error(f"Groq rate limit: {e}")
            raise HTTPException(
                status_code=429,
                detail="Groq rate limit reached. Try again in a moment.",
            ) from e
        except BadRequestError as e:
            logger.error(f"Groq bad request (often wrong model name): {e}")
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Groq returned 400: {e.message}. "
                    "Check GROQ_MODEL in .env matches a model your account can use."
                ),
            ) from e
        except APIStatusError as e:
            logger.error(f"Groq API error {e.status_code}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Groq API error ({e.status_code}): {e.message}",
            ) from e
        except Exception as e:
            logger.error(f"Grammar analysis error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Grammar analysis failed: {str(e)}"
            )
    
    def _parse_analysis_response(self, data: Dict[str, Any]) -> GrammarAnalysisResponse:
        """Parse and validate LLM response into Pydantic model."""
        try:
            # Parse summary
            summary_data = data.get("summary", {})
            raw_level = summary_data.get("overall_level") or "Intermediate"
            level_key = str(raw_level).strip().lower()
            level_map = {
                "beginner": LanguageLevel.BEGINNER,
                "intermediate": LanguageLevel.INTERMEDIATE,
                "advanced": LanguageLevel.ADVANCED,
            }
            overall_level = level_map.get(level_key, LanguageLevel.INTERMEDIATE)

            summary = GrammarSummary(
                total_sentences=summary_data.get("total_sentences", 0),
                total_errors=summary_data.get("total_errors", 0),
                overall_level=overall_level,
            )
            
            # Parse errors
            errors = [
                GrammarError(
                    original=err.get("original", ""),
                    issue_type=err.get("issue_type", "Unknown"),
                    explanation=err.get("explanation", ""),
                    correction=err.get("correction", "")
                )
                for err in data.get("errors", [])
            ]
            
            # Get corrected transcript
            corrected_transcript = data.get("corrected_transcript", "")
            
            return GrammarAnalysisResponse(
                summary=summary,
                errors=errors,
                corrected_transcript=corrected_transcript
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response structure: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse grammar analysis: {str(e)}"
            )