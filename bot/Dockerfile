# iitk-grade-bot/bot/Dockerfile
FROM python:3.11-slim

ENV PYTHONPATH=/app
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt "python-telegram-bot[job-queue]"

COPY ./bot/ /app/
# Expose the internal port the bot's Uvicorn server will listen on(security!)
EXPOSE 7000 

CMD ["sh", "-c", "python set_initial_mode.py && python main.py"]