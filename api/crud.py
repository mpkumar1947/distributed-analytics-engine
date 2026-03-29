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

