import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    'grade_bot_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['api.tasks']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    task_routes={
        'api.tasks.send_broadcast_to_all_task': {'queue': 'broadcasts'},
    },
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

if __name__ == '__main__':
    app.start()