import os
import logging
import redis

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MAINTENANCE_MODE = os.getenv("BOT_STARTUP_MAINTENANCE_MODE", "false").lower() == 'true'

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("set_initial_mode")

def main():
    logger.info(f"Connecting to Redis...")
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        
        if MAINTENANCE_MODE:
            client.set('maintenance_mode', 'stealth')
            logger.info("✅ MAINTENANCE MODE ENABLED (Stealth).")
        else:
            client.delete('maintenance_mode')
            logger.info("✅ MAINTENANCE MODE DISABLED (Live).")
            
    except redis.exceptions.ConnectionError:
        logger.fatal("Could not connect to Redis. Ensure the service is running.")
        exit(1)
    except Exception as e:
        logger.fatal(f"Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()