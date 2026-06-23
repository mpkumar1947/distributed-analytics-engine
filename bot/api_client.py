"""
bot/api_client.py — Direct Database Access Layer

Previously this module made HTTP requests to the FastAPI backend.
Now it talks directly to the database using SQLAlchemy + asyncpg,
eliminating the separate API service entirely.

The return format of every function is kept IDENTICAL to the old HTTP
responses so that handlers.py requires zero changes.
"""
import os
import sys
import logging
import asyncio
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot as TelegramBot
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest

# Ensure api package is importable
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from api.database import AsyncSessionFactory
from api import crud, models, schemas
from api.utils.grading_analysis import analyze_centric_grading
from api.utils.prof_analyzer import calculate_career_stats

logger = logging.getLogger(__name__)


# ==============================================================================
# DATABASE SESSION HELPER
# ==============================================================================

@asynccontextmanager
async def get_db_session():
    """Provides an async database session with automatic cleanup."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ==============================================================================
# SEARCH & DATA FETCHING
# ==============================================================================

async def search_items_api(query: str, search_type: str, user_id: int) -> Optional[List[Dict]]:
    """Search courses or professors. Returns list of dicts matching old API format."""
    try:
        async with get_db_session() as db:
            if search_type == "course":
                results = await crud.search_courses(db, query=query)
                return [{"code": c.code, "name": c.name} for c in results] if results else None
            else:
                results = await crud.search_instructors(db, query=query)
                return [{"id": i.id, "name": i.name} for i in results] if results else None
    except Exception as e:
        logger.error(f"search_items_api error ({search_type}): {e}", exc_info=True)
        return None


async def get_offerings_for_course_api(course_code: str, user_id: int) -> Optional[List[Dict]]:
    """Get all term offerings for a course. Returns list matching OfferingTermWithInstructorsInfo."""
    try:
        async with get_db_session() as db:
            offerings = await crud.get_terms_for_course(db, course_code=course_code)
            if not offerings:
                return None
            return [
                {
                    "academic_year": off.academic_year,
                    "semester": off.semester,
                    "instructors": [{"id": i.id, "name": i.name} for i in off.instructors],
                    "course": {"code": off.course.code, "name": off.course.name}
                }
                for off in offerings
            ]
    except Exception as e:
        logger.error(f"get_offerings_for_course_api error: {e}", exc_info=True)
        return None


async def get_offerings_for_prof_api(instructor_id: int, user_id: int) -> Optional[List[Dict]]:
    """Get all offerings for a professor. Returns list matching ProfCourseOfferingInfo."""
    try:
        async with get_db_session() as db:
            offerings = await crud.get_courses_for_instructor(db, instructor_id=instructor_id)
            if not offerings:
                return None
            return [
                {
                    "id": off.id,
                    "course": {"code": off.course.code, "name": off.course.name},
                    "academic_year": off.academic_year,
                    "semester": off.semester,
                    "plot_file_id": off.plot_file_id,
                }
                for off in offerings
            ]
    except Exception as e:
        logger.error(f"get_offerings_for_prof_api error: {e}", exc_info=True)
        return None


async def get_offering_details_api(
    course_code: str,
    academic_year: str,
    semester: str,
    user_id: int
) -> Optional[Dict]:
    """Get specific offering details. Returns dict matching OfferingSchema."""
    try:
        async with get_db_session() as db:
            offering = await crud.get_offering_by_details(
                db, course_code=course_code,
                academic_year=academic_year, semester=semester
            )
            if not offering:
                return None
            return {
                "id": offering.id,
                "academic_year": offering.academic_year,
                "semester": offering.semester,
                "total_registered": offering.total_registered,
                "current_registered": offering.current_registered,
                "plot_file_id": offering.plot_file_id,
                "course": {"code": offering.course.code, "name": offering.course.name},
                "instructors": [{"id": i.id, "name": i.name} for i in offering.instructors],
            }
    except Exception as e:
        logger.error(f"get_offering_details_api error: {e}", exc_info=True)
        return None


async def get_grades_distribution_api(offering_id: int, user_id: int) -> Optional[Dict]:
    """
    Get grade distribution for an offering.
    Returns dict matching GradeDistributionResponse, including grading analysis.
    """
    try:
        async with get_db_session() as db:
            offering = await crud.get_offering_for_grades(db, offering_id=offering_id)
            if not offering:
                return None

            grades_list = await crud.get_grades_for_offering(db, offering_id=offering_id)

            # Calculate totals
            total_graded = sum((g.count or 0) for g in grades_list)
            base_count = (
                offering.current_registered
                if (offering.current_registered and offering.current_registered > 0)
                else total_graded
            )

            # Process & sort grades
            preferred_order = ['A*', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E', 'F', 'S', 'X', 'W']
            sort_map = {grade: i for i, grade in enumerate(preferred_order)}

            grades_processed = []
            for g in grades_list:
                percentage = round((g.count / base_count) * 100, 1) if (base_count > 0 and g.count) else 0.0
                grades_processed.append({
                    "grade_type": g.grade_type,
                    "count": int(g.count),
                    "percentage": percentage,
                })
            grades_processed.sort(key=lambda x: sort_map.get(x["grade_type"], 999))

            # Run grading analysis
            centric_label = analyze_centric_grading(grades=grades_list, total_students=total_graded)

            return {
                "offering": {
                    "id": offering.id,
                    "academic_year": offering.academic_year,
                    "semester": offering.semester,
                    "total_registered": offering.total_registered,
                    "current_registered": offering.current_registered,
                    "plot_file_id": offering.plot_file_id,
                    "course": {"code": offering.course.code, "name": offering.course.name},
                    "instructors": [{"id": i.id, "name": i.name} for i in offering.instructors],
                },
                "grades": grades_processed,
                "total_graded_students": int(total_graded),
                "centric_grading": centric_label,
            }
    except Exception as e:
        logger.error(f"get_grades_distribution_api error: {e}", exc_info=True)
        return None


async def get_professor_dossier_api(prof_id: int, user_id: int) -> Optional[Dict]:
    """
    Get professor career dossier with stats.
    Returns dict matching ProfessorDossierSchema.
    """
    try:
        async with get_db_session() as db:
            instructor = await crud.get_instructor_by_id(db, instructor_id=prof_id)
            if not instructor:
                return None

            offerings = await crud.get_all_offerings_with_grades_for_instructor(db, instructor_id=prof_id)

            if not offerings:
                return {
                    "instructor_name": instructor.name,
                    "career_plot_file_id": instructor.career_plot_file_id,
                    "message": "No grade data available for analysis.",
                    "stats": None,
                }

            try:
                career_stats = calculate_career_stats(offerings)
            except Exception as e:
                logger.error(f"Failed to calculate stats for instructor {prof_id}: {e}", exc_info=True)
                return {
                    "instructor_name": instructor.name,
                    "career_plot_file_id": instructor.career_plot_file_id,
                    "message": "Analysis failed due to data issues.",
                    "stats": None,
                }

            return {
                "instructor_name": instructor.name,
                "career_plot_file_id": instructor.career_plot_file_id,
                "stats": career_stats,
            }
    except Exception as e:
        logger.error(f"get_professor_dossier_api error: {e}", exc_info=True)
        return None


# ==============================================================================
# USER ACTIONS
# ==============================================================================

async def subscribe_user_api(
    tg_user_id: int,
    first_name: Optional[str],
    last_name: Optional[str],
    username: Optional[str]
) -> Optional[Dict]:
    """Register or update a user via upsert."""
    try:
        async with get_db_session() as db:
            user_data = schemas.UserCreate(
                telegram_user_id=tg_user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
            )
            upserted = await crud.upsert_user(db, user=user_data)
            return {
                "telegram_user_id": upserted.telegram_user_id,
                "first_name": upserted.first_name,
                "last_name": upserted.last_name,
                "username": upserted.username,
                "is_subscribed": upserted.is_subscribed,
            }
    except Exception as e:
        logger.error(f"subscribe_user_api error for {tg_user_id}: {e}", exc_info=True)
        return None


async def unsubscribe_user_api(tg_user_id: int) -> Optional[Dict]:
    """Mark a user as unsubscribed."""
    try:
        async with get_db_session() as db:
            db_user = await crud.get_user(db, user_id=tg_user_id)
            if not db_user:
                return None
            db_user.is_subscribed = False
            await db.commit()
            await db.refresh(db_user)
            return {"telegram_user_id": db_user.telegram_user_id, "is_subscribed": False}
    except Exception as e:
        logger.error(f"unsubscribe_user_api error for {tg_user_id}: {e}", exc_info=True)
        return None


async def submit_feedback_api(
    tg_user_id: int,
    feedback_type: str,
    message_text: str,
    username: Optional[str] = None
) -> Optional[Dict]:
    """Store user feedback in the database."""
    try:
        async with get_db_session() as db:
            feedback_data = schemas.FeedbackCreate(
                telegram_user_id=tg_user_id,
                feedback_type=feedback_type,
                message_text=message_text,
            )
            db_feedback = await crud.create_feedback_entry(db, feedback=feedback_data)
            return {
                "id": db_feedback.id,
                "feedback_type": db_feedback.feedback_type,
                "message_text": db_feedback.message_text,
                "status": db_feedback.status,
            }
    except Exception as e:
        logger.error(f"submit_feedback_api error for {tg_user_id}: {e}", exc_info=True)
        return None


# ==============================================================================
# ADMIN ACTIONS
# ==============================================================================

async def get_user_status_api(
    target_user_id: Union[str, int],
    admin_user_id: int
) -> Optional[Dict]:
    """Get user status by ID or username."""
    try:
        async with get_db_session() as db:
            db_user = await crud.get_user_by_id_or_username(db, user_identifier=target_user_id)
            if not db_user:
                return None
            return {
                "telegram_user_id": db_user.telegram_user_id,
                "first_name": db_user.first_name,
                "last_name": db_user.last_name,
                "username": db_user.username,
                "is_subscribed": db_user.is_subscribed,
                "is_blocked": db_user.is_blocked,
                "block_reason": db_user.block_reason,
            }
    except Exception as e:
        logger.error(f"get_user_status_api error: {e}", exc_info=True)
        return None


async def set_user_block_status_api(
    target_user_id: Union[str, int],
    block: bool,
    reason: Optional[str],
    admin_user_id: int
) -> Optional[Dict]:
    """Block or unblock a user."""
    try:
        async with get_db_session() as db:
            db_user = await crud.get_user_by_id_or_username(db, user_identifier=target_user_id)
            if not db_user:
                return None
            updated = await crud.update_user_block_status(
                db, user_to_update=db_user, is_blocked=block, reason=reason
            )
            return {
                "telegram_user_id": updated.telegram_user_id,
                "is_blocked": updated.is_blocked,
                "block_reason": updated.block_reason,
            }
    except Exception as e:
        logger.error(f"set_user_block_status_api error: {e}", exc_info=True)
        return None


async def initiate_broadcast_api(message_text: str, admin_user_id: int) -> Optional[Dict]:
    """
    Execute broadcast directly using asyncio — no Celery/Redis queue needed.
    This is called as a background task from the broadcast admin command.
    """
    logger.info(f"Broadcast initiated by admin {admin_user_id}")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    db_url = os.getenv("DATABASE_URL")

    if not bot_token or not db_url:
        logger.error("Broadcast: Missing BOT_TOKEN or DATABASE_URL")
        return {"status": "error", "message": "Server configuration error."}

    bot = TelegramBot(token=bot_token)
    metrics = {"sent": 0, "blocked": 0, "not_found": 0, "errors": 0, "total_targets": 0}

    try:
        async with get_db_session() as session:
            stmt = select(models.User.telegram_user_id).where(
                models.User.is_subscribed == True,
                models.User.is_blocked == False
            )
            result = await session.execute(stmt)
            user_ids = result.scalars().all()

        metrics["total_targets"] = len(user_ids)
        logger.info(f"Broadcast: Targeting {metrics['total_targets']} users.")

        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=user_id, text=message_text, parse_mode=ParseMode.HTML)
                metrics["sent"] += 1
            except Forbidden:
                metrics["blocked"] += 1
            except BadRequest:
                metrics["not_found"] += 1
            except Exception as e:
                logger.error(f"Broadcast failed for user {user_id}: {e}")
                metrics["errors"] += 1
            await asyncio.sleep(0.05)

        logger.info(f"Broadcast completed. Metrics: {metrics}")
        return {"status": "completed", "metrics": metrics}

    except Exception as e:
        logger.error(f"Broadcast critical failure: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
