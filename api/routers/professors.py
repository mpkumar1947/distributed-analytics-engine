import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db
from ..utils.prof_analyzer import calculate_career_stats

router = APIRouter(prefix="/professors", tags=["Professors"])
logger = logging.getLogger(__name__)

@router.get("/{instructor_id}/dossier", response_model=schemas.ProfessorDossierSchema)
async def get_professor_dossier(
    instructor_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Analyzes a professor's entire teaching history to generate a career dossier.
    Includes career SPI, consistency metrics, and grading tendencies.
    """
    instructor = await crud.get_instructor_by_id(db, instructor_id=instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    offerings = await crud.get_all_offerings_with_grades_for_instructor(db, instructor_id=instructor_id)
    
    if not offerings:
        return schemas.ProfessorDossierSchema(
            instructor_name=instructor.name,
            career_plot_file_id=instructor.career_plot_file_id,
            message="No grade data available for analysis."
        )

    try:
        career_stats = calculate_career_stats(offerings)
    except Exception as e:
        logger.error(f"Failed to calculate stats for instructor {instructor_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal analysis error.")

    return schemas.ProfessorDossierSchema(
        instructor_name=instructor.name,
        career_plot_file_id=instructor.career_plot_file_id,
        stats=career_stats
    )