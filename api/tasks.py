import asyncio
import os
import logging
from typing import Dict, Any

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from telegram import Bot as TelegramBot
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest

from .models import User

logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def _execute_broadcast(task_id: str, message_text: str) -> Dict[str, Any]:
    """
    Async implementation of the broadcast logic.
    Creates its own DB engine/session to ensure thread safety within the Celery worker.
    """
    logger.info(f"Broadcast Task {task_id}: Started.")

    if not TELEGRAM_BOT_TOKEN or not DATABASE_URL:
        logger.error(f"Broadcast Task {task_id}: Missing Config (Token or DB URL).")
        return {"status": "error", "message": "Server configuration error."}

    bot = TelegramBot(token=TELEGRAM_BOT_TOKEN)
    
    # Metrics
    metrics = {
        "sent": 0,
        "blocked": 0,
        "not_found": 0,
        "errors": 0,
        "total_targets": 0
    }

    # Ephemeral DB Engine for this task
    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=1, max_overflow=2)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # Fetch Users
        async with AsyncSessionLocal() as session:
            stmt = select(User.telegram_user_id).where(
                User.is_subscribed == True, 
                User.is_blocked == False
            )
            result = await session.execute(stmt)
            user_ids = result.scalars().all()

        metrics["total_targets"] = len(user_ids)
        logger.info(f"Broadcast Task {task_id}: Targeting {metrics['total_targets']} users.")

        # Send Messages
        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=user_id, text=message_text, parse_mode=ParseMode.HTML)
                metrics["sent"] += 1
            except Forbidden:
                metrics["blocked"] += 1
            except BadRequest:
                metrics["not_found"] += 1
            except Exception as e:
                logger.error(f"Broadcast Task {task_id}: Failed for user {user_id}: {e}")
                metrics["errors"] += 1
            
            # Rate limiting safety
            await asyncio.sleep(0.05)

        logger.info(f"Broadcast Task {task_id}: Completed. Metrics: {metrics}")
        return {"status": "completed", "metrics": metrics}

    except Exception as e:
        logger.error(f"Broadcast Task {task_id}: Critical failure: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        await engine.dispose()

@shared_task(bind=True, name="api.tasks.send_broadcast_to_all_task", max_retries=2)
def send_broadcast_to_all_task(self, message_text: str):
    """
    Celery wrapper to run the async broadcast logic.
    """
    task_id = str(self.request.id)
    return asyncio.run(_execute_broadcast(task_id, message_text))