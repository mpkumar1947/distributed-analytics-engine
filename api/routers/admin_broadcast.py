import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..tasks import send_broadcast_to_all_task

router = APIRouter(
    prefix="/admin/broadcast",
    tags=["Admin - Broadcast"]
)
logger = logging.getLogger(__name__)

class BroadcastMessageRequest(BaseModel):
    message_text: str = Field(..., min_length=5, max_length=4000,
                              description="Message to broadcast (HTML supported).")

@router.post("/", status_code=202, summary="Enqueue a broadcast message")
async def enqueue_broadcast_message_route(broadcast_request: BroadcastMessageRequest):
    """
    Accepts a message and enqueues it for broadcasting via Celery.
    """
    logger.info(f"Admin request to enqueue broadcast: '{broadcast_request.message_text[:50]}...'")
    try:
        task = send_broadcast_to_all_task.delay(broadcast_request.message_text)
        logger.info(f"Broadcast message enqueued. Task ID: {task.id}")
        return {"message": "Broadcast task successfully queued.", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to enqueue broadcast task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to queue broadcast message.")