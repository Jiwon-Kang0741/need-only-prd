from fastapi import APIRouter, Depends, HTTPException, Request

from app.llm.pipeline import spec_pipeline
from app.models import ValidationResult
from app.session import get_session_id, session_store

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("")
async def validate_coverage(
    request: Request,
    session_id: str = Depends(get_session_id),
):
    session = session_store.get_or_create(session_id)
    if session.spec_markdown is None:
        raise HTTPException(status_code=400, detail="No spec generated yet. Generate a spec first.")
    if session.raw_input is None:
        raise HTTPException(status_code=400, detail="No input found. Submit input first.")

    requirements = session.extracted_requirements.model_dump() if session.extracted_requirements else {}

    session_store.increment_llm_calls(session_id)
    result = await spec_pipeline.validate_coverage(
        session.raw_input.text,
        session.spec_markdown,
        requirements,
    )

    session.validation_result = ValidationResult(**result)

    return {
        "score": session.validation_result.score,
        "covered": session.validation_result.covered,
        "missing": session.validation_result.missing,
        "suggestions": session.validation_result.suggestions,
    }
