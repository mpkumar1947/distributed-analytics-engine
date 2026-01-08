import logging
from typing import List, Optional, Union

from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Local Imports
from . import models, schemas

logger = logging.getLogger(__name__)

# ==============================================================================
# SEARCH OPERATIONS
# ==============================================================================
async def search_courses(db: AsyncSession, query: str) -> List[models.Course]:
    """Search for courses by code or title (partial match)."""
    search_term = f"%{query}%"
    stmt = select(models.Course).where(
        (models.Course.code.ilike(search_term)) |
        (models.Course.name.ilike(search_term))
    ).order_by(models.Course.code).limit(25)
    
    result = await db.execute(stmt)
    return result.scalars().all()

async def search_instructors(db: AsyncSession, query: str) -> List[models.Instructor]:
    """
    Search for instructors. Splits query into keywords; 
    all keywords must be present in the name (AND logic).
    """
    query_words = [word.strip().lower() for word in query.split() if word.strip()]
    
    if not query_words:
        return []

    conditions = [models.Instructor.name.ilike(f"%{word}%") for word in query_words]
    
    stmt = select(models.Instructor).where(
        and_(*conditions)
    ).order_by(models.Instructor.name).limit(25)
    
    result = await db.execute(stmt)
    return result.scalars().all()

# ==============================================================================
# INSTRUCTOR OPERATIONS
# ==============================================================================
async def get_instructor_by_id(db: AsyncSession, instructor_id: int) -> Optional[models.Instructor]:
    stmt = select(models.Instructor).where(models.Instructor.id == instructor_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_instructors(db: AsyncSession) -> List[models.Instructor]:
    result = await db.execute(select(models.Instructor))
    return result.scalars().all()

async def get_all_offerings_with_grades_for_instructor(db: AsyncSession, instructor_id: int) -> List[models.Offering]:
    """Fetch all offerings for an instructor with grades eagerly loaded."""
    stmt = select(models.Offering).options(
        selectinload(models.Offering.grades),
        selectinload(models.Offering.course)
    ).join(
        models.offering_instructor_association
    ).where(
        models.offering_instructor_association.c.instructor_id == instructor_id
    )
    result = await db.execute(stmt)
    return result.unique().scalars().all()

async def update_instructor_plot_file_id(db: AsyncSession, instructor_id: int, file_id: str):
    stmt = update(models.Instructor).where(
        models.Instructor.id == instructor_id
    ).values(
        career_plot_file_id=file_id
    )
    await db.execute(stmt)
    await db.commit()

# ==============================================================================
# OFFERING & GRADE OPERATIONS
# ==============================================================================
async def get_terms_for_course(db: AsyncSession, course_code: str) -> List[models.Offering]:
    stmt = select(models.Offering).options(
        selectinload(models.Offering.instructors),
        selectinload(models.Offering.course)
    ).where(
        models.Offering.course_code == course_code
    ).order_by(
        models.Offering.academic_year.desc(), models.Offering.semester
    )
    result = await db.execute(stmt)
    return result.unique().scalars().all()

async def get_courses_for_instructor(db: AsyncSession, instructor_id: int) -> List[models.Offering]:
    stmt = select(models.Offering).options(
        selectinload(models.Offering.course),
        selectinload(models.Offering.instructors)
    ).join(
        models.offering_instructor_association
    ).where(
        models.offering_instructor_association.c.instructor_id == instructor_id
    ).order_by(
         models.Offering.course_code, models.Offering.academic_year.desc(), models.Offering.semester
    )
    result = await db.execute(stmt)
    return result.unique().scalars().all()

async def get_offering_by_details(
    db: AsyncSession, course_code: str, academic_year: str, semester: str
) -> Optional[models.Offering]:
     stmt = select(models.Offering).options(
         selectinload(models.Offering.instructors),
         selectinload(models.Offering.course)
     ).where(
         models.Offering.course_code == course_code,
         models.Offering.academic_year == academic_year,
         models.Offering.semester == semester
     )
     result = await db.execute(stmt)
     return result.scalar_one_or_none()

async def get_offering_for_grades(db: AsyncSession, offering_id: int) -> Optional[models.Offering]:
    stmt = select(models.Offering).options(
         selectinload(models.Offering.instructors),
         selectinload(models.Offering.course)
    ).where(models.Offering.id == offering_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_grades_for_offering(db: AsyncSession, offering_id: int) -> List[models.Grade]:
    stmt = select(models.Grade).where(
        models.Grade.offering_id == offering_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()

# ==============================================================================
# USER OPERATIONS
# ==============================================================================
async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.telegram_user_id == user_id))
    return result.scalar_one_or_none()

async def upsert_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """
    Inserts a new user or updates existing fields (last_active_at, subscription) 
    if the user already exists.
    """
    stmt = insert(models.User).values(
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        is_subscribed=True,
        last_active_at=func.now()
    ).on_conflict_do_update(
        index_elements=['telegram_user_id'],
        set_={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'is_subscribed': True,
            'last_active_at': func.now()
        }
    ).returning(models.User)

    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()

async def get_user_by_id_or_username(db: AsyncSession, user_identifier: Union[str, int]) -> Optional[models.User]:
    if isinstance(user_identifier, int) or str(user_identifier).isdigit():
        user_id = int(user_identifier)
        stmt = select(models.User).where(models.User.telegram_user_id == user_id)
    else:
        stmt = select(models.User).where(models.User.username.ilike(user_identifier))
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_user_block_status(
    db: AsyncSession, user_to_update: models.User, is_blocked: bool, reason: Optional[str] = None
) -> models.User:
    user_to_update.is_blocked = is_blocked
    if is_blocked:
        user_to_update.block_reason = reason
        user_to_update.blocked_at = func.now()
    else:
        user_to_update.block_reason = None
        user_to_update.blocked_at = None
        
    await db.commit()
    await db.refresh(user_to_update)
    return user_to_update

# ==============================================================================
# FEEDBACK OPERATIONS
# ==============================================================================
async def create_feedback_entry(db: AsyncSession, feedback: schemas.FeedbackCreate) -> models.Feedback:
    db_feedback = models.Feedback(
        telegram_user_id=feedback.telegram_user_id,
        feedback_type=feedback.feedback_type,
        message_text=feedback.message_text
    )
    db.add(db_feedback)
    await db.commit()
    await db.refresh(db_feedback)
    return db_feedback

async def get_all_feedback(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Feedback]:
    stmt = select(models.Feedback).offset(skip).limit(limit).order_by(models.Feedback.submitted_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

async def update_feedback_status(db: AsyncSession, feedback_id: int, status: str) -> Optional[models.Feedback]:
    db_feedback = await db.get(models.Feedback, feedback_id)
    if db_feedback:
        db_feedback.status = status
        await db.commit()
        await db.refresh(db_feedback)
    return db_feedback  