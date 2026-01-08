import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)

@router.post("/subscribe", response_model=schemas.UserRead)
async def subscribe_or_update_user(
    user_in: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user or updates details and activity using upsert logic.
    """
    try:
        upserted_user = await crud.upsert_user(db, user=user_in)
        return upserted_user
    except Exception as e:
        logger.error(f"Error during user upsert for {user_in.telegram_user_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during user update.")

@router.post("/{telegram_user_id}/unsubscribe", response_model=schemas.UserRead)
async def unsubscribe_user_endpoint(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Marks a user as unsubscribed."""
    db_user = await crud.get_user(db, user_id=telegram_user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Direct update for now; consider moving to CRUD if logic grows
    db_user.is_subscribed = False
    await db.commit()
    await db.refresh(db_user)
    return db_user