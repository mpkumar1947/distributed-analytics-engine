import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

logger = logging.getLogger(__name__) 

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/", response_model=schemas.FeedbackRead, status_code=201)
async def create_feedback_submission(
    feedback_in: schemas.FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives feedback from a user (via the bot) and stores it.
    """
    try:
        db_feedback = await crud.create_feedback_entry(db=db, feedback=feedback_in)
        return db_feedback
    except Exception as e:
        logger.error(f"Failed to create feedback entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not store feedback.")