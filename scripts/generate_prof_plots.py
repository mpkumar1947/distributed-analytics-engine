# scripts/generate_prof_plots.py
import argparse
import asyncio
import os
import logging
from dotenv import load_dotenv
from telegram import Bot as TelegramBot
import datetime

import sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from api.database import AsyncSessionFactory
from api import crud
from api.utils.prof_analyzer import calculate_career_stats, generate_career_plot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PLOT_STORAGE_CHANNEL_ID = os.getenv("TELEGRAM_PLOT_STORAGE_CHANNEL_ID")

if not BOT_TOKEN or not PLOT_STORAGE_CHANNEL_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_PLOT_STORAGE_CHANNEL_ID must be set in .env")

async def process_one_instructor(db, bot, instructor):
    prof_id = instructor.id
    prof_name = instructor.name
    logger.info(f"Processing instructor {prof_id}: {prof_name}")

    try:
        offerings = await crud.get_all_offerings_with_grades_for_instructor(db, instructor_id=prof_id)
        if not offerings:
            logger.warning(f"No offerings with grade data for {prof_name}. Skipping.")
            return

        career_stats = calculate_career_stats(offerings)
        if not career_stats:
            logger.warning(f"Stats could not be calculated for {prof_name}. Skipping.")
            return

        plot_bytes = generate_career_plot(prof_name, career_stats)
        if not plot_bytes:
            logger.warning(f"Plot generation failed for {prof_name}. Skipping.")
            return

        logger.info(f"Uploading plot for {prof_name}...")
        sent_message = await bot.send_photo(
            chat_id=PLOT_STORAGE_CHANNEL_ID,
            photo=plot_bytes,
            caption=f"Career plot for: {prof_name} (ID: {prof_id})"
        )
        
        if not sent_message.photo:
            raise ValueError("Message sent to Telegram did not contain a photo.")
        
        new_file_id = sent_message.photo[-1].file_id
        await crud.update_instructor_plot_file_id(db, instructor_id=prof_id, file_id=new_file_id)
        logger.info(f"Success! DB updated for {prof_name} with file_id: {new_file_id}")

    except Exception as e:
        logger.error(f"FAILED to process instructor {prof_id} ({prof_name}): {e}", exc_info=True)

async def main():
    parser = argparse.ArgumentParser(description="Generate and upload career plots for instructors.")
    parser.add_argument("--prof-id", type=int, help="Optional: Process only a single instructor by their ID.")
    args = parser.parse_args()

    bot = TelegramBot(token=BOT_TOKEN)
    async with AsyncSessionFactory() as session:
        instructors_to_process = []
        
        # This block now correctly fetches the instructors without a transaction
        if args.prof_id:
            logger.info(f"Fetching single instructor with ID: {args.prof_id}")
            instructor = await crud.get_instructor_by_id(session, instructor_id=args.prof_id)
            if instructor:
                instructors_to_process.append(instructor)
            else:
                logger.error(f"Instructor with ID {args.prof_id} not found.")
        else:
            logger.info("Fetching all instructors from the database...")
            instructors_to_process = await crud.get_all_instructors(session)
        
        logger.info(f"Found {len(instructors_to_process)} instructor(s) to process.")
        
        # The transaction now correctly starts INSIDE the loop for each professor
        for instructor in instructors_to_process:
           
           async with AsyncSessionFactory() as session:
              
              await process_one_instructor(session, bot, instructor)
           await asyncio.sleep(2)
    
    logger.info("Finished processing.")

if __name__ == "__main__":
    asyncio.run(main())