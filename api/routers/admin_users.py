import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

router = APIRouter(
    prefix="/admin/users",
    tags=["Admin - User Management"]
)
logger = logging.getLogger(__name__)

@router.get("/{user_identifier}", response_model=schemas.UserRead)
async def read_user_status(user_identifier: str, db: AsyncSession = Depends(get_db)):
    """Get user status by Telegram ID or username."""
    db_user = await crud.get_user_by_id_or_username(db, user_identifier=user_identifier)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_identifier}/block_status", response_model=schemas.UserRead)
async def set_user_block_status(
    user_identifier: str,
    status_update: schemas.UserBlockStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Admin action: set_user_block_status for '{user_identifier}'")
    
    db_user = await crud.get_user_by_id_or_username(db, user_identifier=user_identifier)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found to update block status.")
    
    try:
        updated_user = await crud.update_user_block_status(
            db=db, 
            user_to_update=db_user, 
            is_blocked=status_update.is_blocked, 
            reason=status_update.block_reason
        )
        return updated_user
    except Exception as e:
        logger.error(f"Error in set_user_block_status for {user_identifier}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")