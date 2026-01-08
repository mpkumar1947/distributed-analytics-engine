import logging
import os
import asyncio
from typing import List

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
    ConversationHandler, TypeHandler, JobQueue
)
from fastapi import FastAPI, Request, Response
import uvicorn

# Local Imports
from handlers import (
    start_command, help_command, cancel_conversation,
    subscribe_command, unsubscribe_command,
    maintenance_command, broadcast_admin_command,
    block_user_command, unblock_user_command, user_status_command,
    admin_help_command, feedback_start_command,
    select_search_mode_callback, handle_course_search_input, handle_prof_search_input,
    select_item_callback, select_year_semester_callback,
    page_course_search_results_callback, page_prof_search_results_callback,
    page_prof_course_list_callback, page_year_semester_list_callback,
    back_to_typing_course_callback, back_to_typing_prof_callback,
    back_to_prof_search_list_callback, back_to_course_search_list_callback,
    back_to_prof_courses_callback, back_to_year_sem_select_callback,
    back_to_main_callback, simple_close_callback, back_to_course_list_from_plot_callback,
    view_prof_courses_callback,
    feedback_type_callback, feedback_message_handler,
    feedback_confirm_send_callback, feedback_cancel_or_edit_callback,
    global_pre_processor
)

from constants import (
    SELECTING_ACTION, TYPING_COURSE, TYPING_PROF,
    SELECTING_COURSE_RESULTS, SELECTING_PROF_RESULTS,
    SELECTING_COURSE_FOR_PROF, SELECTING_YEAR_SEMESTER, SHOWING_FINAL_GRADES,
    COURSE_SEARCH_MODE, PROF_SEARCH_MODE, CANCEL, BACK_TO_MAIN,
    COURSE_SELECT_PREFIX, PROF_SELECT_PREFIX, YEAR_SEM_SELECT_PREFIX,
    BACK_TO_TYPING_COURSE, BACK_TO_TYPING_PROF,
    BACK_TO_PROF_COURSE_LIST_PREFIX, BACK_TO_COURSE_SEARCH_LIST,
    BACK_TO_PROF_SEARCH_LIST, BACK_TO_YEAR_SEM_SELECT_PREFIX,
    BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX,
    PAGE_COURSE_SEARCH_RESULTS_PREFIX, PAGE_PROF_SEARCH_RESULTS_PREFIX,
    PAGE_PROF_COURSE_LIST_PREFIX, PAGE_YEAR_SEMESTER_PREFIX,
    ASK_FEEDBACK_TYPE, TYPING_FEEDBACK_MESSAGE, CONFIRM_FEEDBACK_SUBMISSION,
    FEEDBACK_TYPE_BUG, FEEDBACK_TYPE_SUGGESTION, FEEDBACK_TYPE_GENERAL,
    VIEW_PROF_COURSES_PREFIX, CONFIRM_SEND_FEEDBACK, CANCEL_FEEDBACK
)

# Load environment variables
load_dotenv()

# Logger Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN")
WEBHOOK_URL_PATH_PREFIX = os.getenv("WEBHOOK_URL_PATH_PREFIX", "/webhook")
BOT_WEBHOOK_PORT = int(os.getenv("BOT_WEBHOOK_PORT", "7000"))
TELEGRAM_ADMIN_IDS_STR = os.getenv("TELEGRAM_ADMIN_IDS", "")

if not BOT_TOKEN or not PUBLIC_DOMAIN:
    logger.fatal("Critical Env Vars Missing: TELEGRAM_BOT_TOKEN or PUBLIC_DOMAIN.")
    exit(1)

# Webhook URLs
FULL_WEBHOOK_URL = f"https://{PUBLIC_DOMAIN.rstrip('/')}{WEBHOOK_URL_PATH_PREFIX.rstrip('/')}/{BOT_TOKEN}"
WEBHOOK_PATH = f"{WEBHOOK_URL_PATH_PREFIX.rstrip('/')}/{BOT_TOKEN}"

# Parse Admin IDs
ADMIN_USER_IDS: List[int] = []
if TELEGRAM_ADMIN_IDS_STR:
    try:
        ADMIN_USER_IDS = [int(uid.strip()) for uid in TELEGRAM_ADMIN_IDS_STR.split(',') if uid.strip()]
    except ValueError:
        logger.error("Failed to parse TELEGRAM_ADMIN_IDS.")

# Global Application Instances
ptb_application: Application = None
webhook_fastapi_app = FastAPI(docs_url=None, redoc_url=None)


@webhook_fastapi_app.post(WEBHOOK_PATH)
async def telegram_webhook_endpoint(request: Request):
    """Handle incoming Telegram updates via Webhook."""
    try:
        request_body = await request.json()
        update = Update.de_json(request_body, ptb_application.bot)
        await ptb_application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return Response(status_code=200)


async def setup_ptb_application():
    """Initialize and configure the Telegram Bot Application."""
    global ptb_application

    # Build Application
    builder = Application.builder().token(BOT_TOKEN).job_queue(JobQueue())
    ptb_application = builder.build()

    # Store Config in Bot Data
    ptb_application.bot_data['ADMIN_USER_IDS'] = ADMIN_USER_IDS

    # Register Handlers
    # 1. Global Pre-processor
    ptb_application.add_handler(TypeHandler(Update, global_pre_processor), group=-1)

    # 2. Main Search Conversation
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(select_search_mode_callback, pattern=f"^({COURSE_SEARCH_MODE}|{PROF_SEARCH_MODE})$")],
            TYPING_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_course_search_input)],
            TYPING_PROF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prof_search_input)],
            SELECTING_COURSE_RESULTS: [
                CallbackQueryHandler(select_item_callback, pattern=f"^{COURSE_SELECT_PREFIX}"),
                CallbackQueryHandler(back_to_typing_course_callback, pattern=f"^{BACK_TO_TYPING_COURSE}$"),
                CallbackQueryHandler(page_course_search_results_callback, pattern=f"^{PAGE_COURSE_SEARCH_RESULTS_PREFIX}"),
            ],
            SELECTING_PROF_RESULTS: [
                CallbackQueryHandler(select_item_callback, pattern=f"^{PROF_SELECT_PREFIX}"),
                CallbackQueryHandler(back_to_typing_prof_callback, pattern=f"^{BACK_TO_TYPING_PROF}$"),
                CallbackQueryHandler(page_prof_search_results_callback, pattern=f"^{PAGE_PROF_SEARCH_RESULTS_PREFIX}"),
            ],
            SELECTING_COURSE_FOR_PROF: [
                CallbackQueryHandler(select_item_callback, pattern=f"^{COURSE_SELECT_PREFIX}"),
                CallbackQueryHandler(page_prof_course_list_callback, pattern=f"^{PAGE_PROF_COURSE_LIST_PREFIX}"),
                CallbackQueryHandler(view_prof_courses_callback, pattern=f"^{VIEW_PROF_COURSES_PREFIX}"),
            ],
            SELECTING_YEAR_SEMESTER: [
                CallbackQueryHandler(select_year_semester_callback, pattern=f"^{YEAR_SEM_SELECT_PREFIX}"),
                CallbackQueryHandler(page_year_semester_list_callback, pattern=f"^{PAGE_YEAR_SEMESTER_PREFIX}"),
                CallbackQueryHandler(back_to_course_search_list_callback, pattern=f"^{BACK_TO_COURSE_SEARCH_LIST}$"),
                CallbackQueryHandler(back_to_prof_courses_callback, pattern=f"^{BACK_TO_PROF_COURSE_LIST_PREFIX}"),
            ],
            SHOWING_FINAL_GRADES: [
                CallbackQueryHandler(back_to_year_sem_select_callback, pattern=f"^{BACK_TO_YEAR_SEM_SELECT_PREFIX}"),
                CallbackQueryHandler(back_to_course_list_from_plot_callback, pattern=f"^{BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX}"),
                CallbackQueryHandler(back_to_main_callback, pattern=f"^{BACK_TO_MAIN}$"),
                CallbackQueryHandler(cancel_conversation, pattern=f"^{CANCEL}$"),
            ],
        },
        fallbacks=[
            CommandHandler('start', start_command),
            CommandHandler('cancel', cancel_conversation),
            CommandHandler('help', help_command),
            CallbackQueryHandler(back_to_main_callback, pattern=f"^{BACK_TO_MAIN}$"),
            CallbackQueryHandler(back_to_prof_search_list_callback, pattern=f"^{BACK_TO_PROF_SEARCH_LIST}$"),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CANCEL}$"),
            CallbackQueryHandler(simple_close_callback, pattern="^close_interaction$"),
        ],
        conversation_timeout=600,
        allow_reentry=True,
    )
    ptb_application.add_handler(search_conv_handler)

    # 3. Feedback Conversation
    feedback_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback_start_command)],
        states={
            ASK_FEEDBACK_TYPE: [CallbackQueryHandler(feedback_type_callback, pattern=f"^({FEEDBACK_TYPE_BUG}|{FEEDBACK_TYPE_SUGGESTION}|{FEEDBACK_TYPE_GENERAL})$")],
            TYPING_FEEDBACK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_message_handler)],
            CONFIRM_FEEDBACK_SUBMISSION: [
                CallbackQueryHandler(feedback_confirm_send_callback, pattern=f"^{CONFIRM_SEND_FEEDBACK}$"),
                CallbackQueryHandler(feedback_cancel_or_edit_callback, pattern=f"^{CANCEL_FEEDBACK}$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(feedback_cancel_or_edit_callback, pattern=f"^{CANCEL_FEEDBACK}$"),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CANCEL}$"),
            CommandHandler('cancel', cancel_conversation),
            CommandHandler('start', start_command),
        ],
        conversation_timeout=300,
        allow_reentry=True,
    )
    ptb_application.add_handler(feedback_conv_handler)

    # 4. General & Admin Commands
    ptb_application.add_handler(CommandHandler("help", help_command))
    ptb_application.add_handler(CommandHandler("subscribe", subscribe_command))
    ptb_application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    ptb_application.add_handler(CommandHandler("maintenance", maintenance_command))
    ptb_application.add_handler(CommandHandler("broadcast_admin", broadcast_admin_command))
    ptb_application.add_handler(CommandHandler("block", block_user_command))
    ptb_application.add_handler(CommandHandler("unblock", unblock_user_command))
    ptb_application.add_handler(CommandHandler("userstatus", user_status_command))
    ptb_application.add_handler(CommandHandler("admin_commands", admin_help_command))

    # Initialize
    await ptb_application.initialize()
    
    # Set Webhook
    await ptb_application.bot.set_webhook(url=FULL_WEBHOOK_URL, allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    logger.info(f"Webhook set to: {FULL_WEBHOOK_URL}")


async def main():
    """Entry point."""
    await setup_ptb_application()

    config = uvicorn.Config(
        app=webhook_fastapi_app,
        host="0.0.0.0",
        port=BOT_WEBHOOK_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    logger.info(f"Starting Webhook Server on port {BOT_WEBHOOK_PORT}...")
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.fatal(f"Fatal error: {e}", exc_info=True)