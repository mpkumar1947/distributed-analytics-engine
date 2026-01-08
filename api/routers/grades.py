import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Local Imports
from .. import crud, schemas
from ..database import get_db
from ..utils.grading_analysis import analyze_centric_grading

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/grades",
    tags=["Grades & Offerings"],
)

@router.get("/offering/details", response_model=schemas.OfferingSchema)
async def get_offering_details(
    course_code: str = Query(..., description="Full course code (e.g., MTH101A)"),
    academic_year: str = Query(..., description="Academic year (e.g., 2023-2024)"),
    semester: str = Query(..., description="Semester (e.g., Odd, Even)"),
    db: AsyncSession = Depends(get_db)
):
    offering = await crud.get_offering_by_details(
         db=db, course_code=course_code, academic_year=academic_year, semester=semester
    )
    if not offering:
         raise HTTPException(status_code=404, detail="Offering not found.")
    return offering

@router.get("/offering/{offering_id}", response_model=schemas.GradeDistributionResponse)
async def get_grade_distribution(
    offering_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    offering = await crud.get_offering_for_grades(db=db, offering_id=offering_id)
    if not offering:
        raise HTTPException(status_code=404, detail=f"Offering ID {offering_id} not found.")

    grades_list = await crud.get_grades_for_offering(db=db, offering_id=offering_id)

    # Calculate Totals
    total_graded = sum((g.count or 0) for g in grades_list)
    base_count = offering.current_registered if (offering.current_registered and offering.current_registered > 0) else total_graded

    # Process Grades
    grades_processed = []
    for g in grades_list:
        percentage = 0.0
        if base_count > 0 and g.count:
            percentage = round((g.count / base_count) * 100, 1)
        
        grades_processed.append(schemas.GradeSchema(
            grade_type=g.grade_type,
            count=g.count,
            percentage=percentage
        ))

    # Sort Grades (A* -> F)
    preferred_order = ['A*', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E', 'F', 'S', 'X', 'W']
    sort_map = {grade: i for i, grade in enumerate(preferred_order)}
    grades_processed.sort(key=lambda x: sort_map.get(x.grade_type, 999))
    
    centric_label = analyze_centric_grading(grades=grades_processed, total_students=total_graded)

    return schemas.GradeDistributionResponse(
        offering=offering,
        grades=grades_processed,
        total_graded_students=total_graded,
        centric_grading=centric_label
    )

@router.get("/offering/by_course/{course_code}", response_model=List[schemas.OfferingTermWithInstructorsInfo])
async def list_offerings_for_course(
    course_code: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    offerings = await crud.get_terms_for_course(db=db, course_code=course_code)
    if not offerings:
        raise HTTPException(status_code=404, detail=f"No offerings found for course {course_code}")
    
    # Transform to Schema
    response = []
    for off in offerings:
        response.append(schemas.OfferingTermWithInstructorsInfo(
            academic_year=off.academic_year,
            semester=off.semester,
            instructors=[schemas.InstructorInOfferingSchema.from_orm(i) for i in off.instructors],
            course=off.course
         ))
    return response

@router.get("/offering/by_prof/{instructor_id}", response_model=List[schemas.ProfCourseOfferingInfo])
async def list_offerings_for_prof(
    instructor_id: int = Path(..., gt=0), 
    db: AsyncSession = Depends(get_db)
):
    offerings = await crud.get_courses_for_instructor(db=db, instructor_id=instructor_id)
    if not offerings:
         raise HTTPException(status_code=404, detail=f"No offerings found for instructor ID {instructor_id}")
    return [schemas.ProfCourseOfferingInfo.from_orm(o) for o in offerings]