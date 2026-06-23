import logging
import os
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.database import get_db
from api import models, schemas
from api.crud import update_user_block_status
from bot.main import get_bot_instance

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin Dashboard"]
)

# ==============================================================================
# SECURE MIDDLEWARE DEPENDENCY
# ==============================================================================
async def verify_dashboard_secret(x_dashboard_secret: str = Header(None)):
    """Ensures the request comes from the trusted Cloudflare Worker proxy."""
    expected_secret = os.getenv("DASHBOARD_SECRET")
    
    # If no secret is set in env, the dashboard is disabled for security
    if not expected_secret:
        logger.error("DASHBOARD_SECRET env var is not set on the server!")
        raise HTTPException(status_code=500, detail="Dashboard API disabled (no secret configured).")
        
    if not x_dashboard_secret or x_dashboard_secret != expected_secret:
        logger.warning("Unauthorized access attempt to admin dashboard.")
        raise HTTPException(status_code=401, detail="Invalid or missing X-Dashboard-Secret header.")
        
    return True

# ==============================================================================
# SCHEMAS
# ==============================================================================
class BroadcastPayload(BaseModel):
    message_text: str

class PollPayload(BaseModel):
    question: str
    options: List[str]
    is_anonymous: bool = True
    type: str = "regular" # 'regular' or 'quiz'
    correct_option_id: Optional[int] = None
    
class ReplyPayload(BaseModel):
    telegram_user_id: int
    message_text: str

class FeedbackStatusUpdate(BaseModel):
    status: str # 'new', 'read', 'replied'

# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/stats", dependencies=[Depends(verify_dashboard_secret)])
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get high-level statistics for the dashboard top bar."""
    # Total Users
    total_users = (await db.execute(select(func.count(models.User.telegram_user_id)))).scalar_one()
    # Active Subscribers
    total_subs = (await db.execute(select(func.count(models.User.telegram_user_id)).where(models.User.is_subscribed == True))).scalar_one()
    # Feedback counts
    new_feedback = (await db.execute(select(func.count(models.Feedback.id)).where(models.Feedback.status == 'new'))).scalar_one()
    total_feedback = (await db.execute(select(func.count(models.Feedback.id)))).scalar_one()
    
    return {
        "total_users": total_users,
        "total_subscribers": total_subs,
        "new_feedback": new_feedback,
        "total_feedback": total_feedback
    }

@router.get("/feedback", dependencies=[Depends(verify_dashboard_secret)])
async def list_feedback(db: AsyncSession = Depends(get_db), limit: int = 50, offset: int = 0):
    """List all feedback with user context."""
    # Join with User to get username/names
    stmt = select(models.Feedback, models.User).join(
        models.User, models.Feedback.telegram_user_id == models.User.telegram_user_id
    ).order_by(models.Feedback.submitted_at.desc()).limit(limit).offset(offset)
    
    results = await db.execute(stmt)
    
    data = []
    for fb, user in results.all():
        data.append({
            "id": fb.id,
            "telegram_user_id": fb.telegram_user_id,
            "username": user.username,
            "first_name": user.first_name,
            "feedback_type": fb.feedback_type,
            "message_text": fb.message_text,
            "status": fb.status,
            "submitted_at": fb.submitted_at.isoformat() if fb.submitted_at else None
        })
    return data

@router.patch("/feedback/{feedback_id}/status", dependencies=[Depends(verify_dashboard_secret)])
async def update_feedback_status(feedback_id: int, payload: FeedbackStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Update feedback status (new -> read -> replied)."""
    db_feedback = await db.get(models.Feedback, feedback_id)
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found.")
        
    db_feedback.status = payload.status
    await db.commit()
    return {"success": True, "new_status": db_feedback.status}

@router.get("/users", dependencies=[Depends(verify_dashboard_secret)])
async def list_users(db: AsyncSession = Depends(get_db), limit: int = 50, offset: int = 0):
    """List registered users."""
    stmt = select(models.User).order_by(models.User.last_active_at.desc().nullslast()).limit(limit).offset(offset)
    results = await db.execute(stmt)
    return results.scalars().all()

@router.post("/users/{telegram_user_id}/block", dependencies=[Depends(verify_dashboard_secret)])
async def toggle_block_user(telegram_user_id: int, payload: schemas.UserBlockStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Block or unblock a user."""
    db_user = await db.get(models.User, telegram_user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    updated_user = await update_user_block_status(db, db_user, payload.is_blocked, payload.block_reason)
    return updated_user

# ==============================================================================
# TELEGRAM BOT INTEGRATION ENDPOINTS
# ==============================================================================

@router.post("/reply", dependencies=[Depends(verify_dashboard_secret)])
async def send_direct_reply(payload: ReplyPayload):
    """Send a direct message from the bot to a specific user (e.g., replying to feedback)."""
    bot = get_bot_instance()
    try:
        await bot.send_message(
            chat_id=payload.telegram_user_id,
            text=payload.message_text,
            parse_mode="MarkdownV2"
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to send reply to {payload.telegram_user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/broadcast", dependencies=[Depends(verify_dashboard_secret)])
async def send_broadcast(payload: BroadcastPayload, db: AsyncSession = Depends(get_db)):
    """Send a broadcast message to all subscribed users."""
    bot = get_bot_instance()
    
    # Get all active subscribers
    stmt = select(models.User.telegram_user_id).where(models.User.is_subscribed == True)
    results = await db.execute(stmt)
    subscribers = results.scalars().all()
    
    if not subscribers:
        return {"success": True, "sent_count": 0, "message": "No subscribers found."}
        
    sent_count = 0
    errors = []
    
    for user_id in subscribers:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=payload.message_text,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            sent_count += 1
        except Exception as e:
            errors.append({"user_id": user_id, "error": str(e)})
            
    return {
        "success": True,
        "sent_count": sent_count,
        "total_attempted": len(subscribers),
        "errors": errors
    }

@router.post("/poll", dependencies=[Depends(verify_dashboard_secret)])
async def send_poll(payload: PollPayload, db: AsyncSession = Depends(get_db)):
    """Send a native Telegram Poll or Quiz to all subscribed users."""
    bot = get_bot_instance()
    
    stmt = select(models.User.telegram_user_id).where(models.User.is_subscribed == True)
    results = await db.execute(stmt)
    subscribers = results.scalars().all()
    
    sent_count = 0
    errors = []
    
    for user_id in subscribers:
        try:
            await bot.send_poll(
                chat_id=user_id,
                question=payload.question,
                options=payload.options,
                is_anonymous=payload.is_anonymous,
                type=payload.type,
                correct_option_id=payload.correct_option_id
            )
            sent_count += 1
        except Exception as e:
            errors.append({"user_id": user_id, "error": str(e)})
            
    return {
        "success": True,
        "sent_count": sent_count,
        "total_attempted": len(subscribers),
        "errors": errors
    }
